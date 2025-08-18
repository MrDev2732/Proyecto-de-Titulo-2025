"""
Repository para manejo de datos de autenticación.

Contiene todas las consultas y operaciones de base de datos relacionadas con usuarios,
roles y autenticación OAuth.
"""

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.database import User, Role, UserOauthIdentity, UserSession
from src.database.enums import UserStatus
from src.database.timezone_utils import now_chile
from src.core.logging import get_logger


logger = get_logger(__name__)


class AuthRepository:
    """Repository para operaciones de autenticación."""

    @staticmethod
    async def find_user_by_email(session: AsyncSession, email: str) -> Optional[User]:
        """
        Buscar usuario por email.

        Args:
            session: Sesión de base de datos
            email: Email a buscar

        Returns:
            User: Usuario encontrado o None
        """
        result = await session.execute(
            select(User)
            .options(selectinload(User.roles))
            .where(User.email == email.lower())
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def find_user_by_id(session: AsyncSession, user_id: UUID) -> Optional[User]:
        """
        Buscar usuario por ID.

        Args:
            session: Sesión de base de datos
            user_id: ID del usuario

        Returns:
            User: Usuario encontrado o None
        """
        result = await session.execute(
            select(User)
            .options(selectinload(User.roles))
            .where(User.id == user_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def create_user(
        session: AsyncSession,
        email: str,
        password_hash: Optional[str] = None,
        status: UserStatus = UserStatus.ACTIVE,
        email_verified_at: Optional[datetime] = None
    ) -> User:
        """
        Crear nuevo usuario.

        Args:
            session: Sesión de base de datos
            email: Email del usuario
            password_hash: Hash de contraseña (opcional para OAuth)
            status: Estado del usuario
            email_verified_at: Fecha de verificación del email

        Returns:
            User: Usuario creado
        """
        user = User(
            email=email.lower(),
            password_hash=password_hash,
            status=status,
            email_verified_at=email_verified_at
        )

        session.add(user)
        await session.flush()  # Para obtener el ID
        return user

    @staticmethod
    async def assign_roles_to_user(
        session: AsyncSession,
        user: User,
        role_names: List[str]
    ) -> None:
        """
        Asignar roles a un usuario.

        Args:
            session: Sesión de base de datos
            user: Usuario al que asignar roles
            role_names: Lista de nombres de roles
        """
        if not role_names:
            return

        # Buscar roles existentes
        role_objects = []
        for role_name in role_names:
            role = await RoleRepository.find_role_by_name(session, role_name)
            if role:
                role_objects.append(role)
            else:
                logger.warning(f"Rol '{role_name}' no encontrado")

        # Asignar roles al usuario
        # Refresh para cargar la relación roles antes de acceder
        await session.refresh(user, ["roles"])
        user.roles.extend(role_objects)

    @staticmethod
    async def update_user_password(
        session: AsyncSession,
        user: User,
        new_password_hash: str
    ) -> None:
        """
        Actualizar contraseña del usuario.

        Args:
            session: Sesión de base de datos
            user: Usuario a actualizar
            new_password_hash: Nuevo hash de contraseña
        """
        user.password_hash = new_password_hash

    @staticmethod
    async def update_user_status(
        session: AsyncSession,
        user: User,
        status: UserStatus
    ) -> None:
        """
        Actualizar estado del usuario.

        Args:
            session: Sesión de base de datos
            user: Usuario a actualizar
            status: Nuevo estado
        """
        user.status = status


class RoleRepository:
    """Repository para operaciones con roles."""

    @staticmethod
    async def find_role_by_name(session: AsyncSession, name: str) -> Optional[Role]:
        """
        Buscar rol por nombre.

        Args:
            session: Sesión de base de datos
            name: Nombre del rol

        Returns:
            Role: Rol encontrado o None
        """
        result = await session.execute(
            select(Role).where(Role.name == name)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def create_role(session: AsyncSession, name: str) -> Role:
        """
        Crear nuevo rol.

        Args:
            session: Sesión de base de datos
            name: Nombre del rol

        Returns:
            Role: Rol creado
        """
        role = Role(name=name)
        session.add(role)
        await session.flush()
        return role

    @staticmethod
    async def get_all_roles(session: AsyncSession) -> List[Role]:
        """
        Obtener todos los roles.

        Args:
            session: Sesión de base de datos

        Returns:
            List[Role]: Lista de todos los roles
        """
        result = await session.execute(select(Role))
        return result.scalars().all()


class OAuthRepository:
    """Repository para operaciones OAuth."""

    @staticmethod
    async def find_oauth_identity(
        session: AsyncSession,
        provider: str,
        provider_user_id: str
    ) -> Optional[UserOauthIdentity]:
        """
        Buscar identidad OAuth.

        Args:
            session: Sesión de base de datos
            provider: Proveedor OAuth
            provider_user_id: ID del usuario en el proveedor

        Returns:
            UserOauthIdentity: Identidad encontrada o None
        """
        result = await session.execute(
            select(UserOauthIdentity)
            .options(selectinload(UserOauthIdentity.user).selectinload(User.roles))
            .where(
                UserOauthIdentity.provider == provider,
                UserOauthIdentity.provider_user_id == provider_user_id
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def create_oauth_identity(
        session: AsyncSession,
        user_id: UUID,
        provider: str,
        provider_user_id: str,
        provider_email: str,
        access_token: Optional[str] = None,
        refresh_token: Optional[str] = None,
        token_expires_at: Optional[datetime] = None
    ) -> UserOauthIdentity:
        """
        Crear nueva identidad OAuth.

        Args:
            session: Sesión de base de datos
            user_id: ID del usuario local
            provider: Proveedor OAuth
            provider_user_id: ID del usuario en el proveedor
            provider_email: Email del proveedor
            access_token: Token de acceso OAuth
            refresh_token: Token de refresh OAuth
            token_expires_at: Fecha de expiración del token

        Returns:
            UserOauthIdentity: Identidad OAuth creada
        """
        oauth_identity = UserOauthIdentity(
            user_id=user_id,
            provider=provider,
            provider_user_id=provider_user_id,
            provider_email=provider_email,
            access_token=access_token,
            refresh_token=refresh_token,
            token_expires_at=token_expires_at
        )

        session.add(oauth_identity)
        await session.flush()
        return oauth_identity

    @staticmethod
    async def update_oauth_tokens(
        session: AsyncSession,
        oauth_identity: UserOauthIdentity,
        access_token: Optional[str] = None,
        refresh_token: Optional[str] = None,
        token_expires_at: Optional[datetime] = None,
        provider_email: Optional[str] = None
    ) -> None:
        """
        Actualizar tokens OAuth.

        Args:
            session: Sesión de base de datos
            oauth_identity: Identidad OAuth a actualizar
            access_token: Nuevo token de acceso
            refresh_token: Nuevo token de refresh
            token_expires_at: Nueva fecha de expiración
            provider_email: Nuevo email del proveedor
        """
        if access_token is not None:
            oauth_identity.access_token = access_token
        if refresh_token is not None:
            oauth_identity.refresh_token = refresh_token
        if token_expires_at is not None:
            oauth_identity.token_expires_at = token_expires_at
        if provider_email is not None:
            oauth_identity.provider_email = provider_email


class SessionRepository:
    """Repository para operaciones con sesiones de usuario."""

    @staticmethod
    async def create_session(
        session: AsyncSession,
        user_id: UUID,
        access_token_hash: str,
        refresh_token_hash: Optional[str],
        expires_at: datetime,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> UserSession:
        """
        Crear nueva sesión de usuario.

        Args:
            session: Sesión de base de datos
            user_id: ID del usuario
            access_token_hash: Hash del access token
            refresh_token_hash: Hash del refresh token (opcional)
            expires_at: Fecha de expiración
            ip_address: Dirección IP del cliente
            user_agent: User agent del cliente

        Returns:
            UserSession: Sesión creada
        """
        user_session = UserSession(
            user_id=user_id,
            access_token_hash=access_token_hash,
            refresh_token_hash=refresh_token_hash,
            expires_at=expires_at,
            ip_address=ip_address,
            user_agent=user_agent
        )
        session.add(user_session)
        await session.flush()
        return user_session

    @staticmethod
    async def find_session_by_access_token(
        session: AsyncSession,
        access_token_hash: str
    ) -> Optional[UserSession]:
        """
        Buscar sesión por hash de access token.

        Args:
            session: Sesión de base de datos
            access_token_hash: Hash del access token

        Returns:
            UserSession: Sesión encontrada o None
        """
        result = await session.execute(
            select(UserSession)
            .options(selectinload(UserSession.user).selectinload(User.roles))
            .where(
                UserSession.access_token_hash == access_token_hash,
                UserSession.is_active == True
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def find_session_by_refresh_token(
        session: AsyncSession,
        refresh_token_hash: str
    ) -> Optional[UserSession]:
        """
        Buscar sesión por hash de refresh token.

        Args:
            session: Sesión de base de datos
            refresh_token_hash: Hash del refresh token

        Returns:
            UserSession: Sesión encontrada o None
        """
        result = await session.execute(
            select(UserSession)
            .options(selectinload(UserSession.user).selectinload(User.roles))
            .where(
                UserSession.refresh_token_hash == refresh_token_hash,
                UserSession.is_active == True
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def revoke_session(
        session: AsyncSession,
        user_session: UserSession
    ) -> None:
        """
        Revocar sesión.

        Args:
            session: Sesión de base de datos
            user_session: Sesión a revocar
        """
        user_session.revoke()

    @staticmethod
    async def revoke_all_user_sessions(
        session: AsyncSession,
        user_id: UUID
    ) -> None:
        """
        Revocar todas las sesiones de un usuario.

        Args:
            session: Sesión de base de datos
            user_id: ID del usuario
        """
        await session.execute(
            update(UserSession)
            .where(
                UserSession.user_id == user_id,
                UserSession.is_active == True
            )
            .values(
                is_active=False,
                revoked_at=now_chile()
            )
        )

    @staticmethod
    async def cleanup_expired_sessions(session: AsyncSession) -> int:
        """
        Limpiar sesiones expiradas.

        Args:
            session: Sesión de base de datos

        Returns:
            int: Número de sesiones limpiadas
        """
        result = await session.execute(
            update(UserSession)
            .where(
                UserSession.expires_at < now_chile(),
                UserSession.is_active == True
            )
            .values(
                is_active=False,
                revoked_at=now_chile()
            )
        )
        return result.rowcount

    @staticmethod
    async def get_user_active_sessions(
        session: AsyncSession,
        user_id: UUID
    ) -> List[UserSession]:
        """
        Obtener sesiones activas de un usuario.

        Args:
            session: Sesión de base de datos
            user_id: ID del usuario

        Returns:
            List[UserSession]: Lista de sesiones activas
        """
        result = await session.execute(
            select(UserSession)
            .where(
                UserSession.user_id == user_id,
                UserSession.is_active == True,
                UserSession.expires_at > now_chile()
            )
            .order_by(UserSession.created_at.desc())
        )
        return list(result.scalars().all())

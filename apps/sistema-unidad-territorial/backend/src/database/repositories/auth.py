"""
Repository para manejo de datos de autenticación.

Contiene todas las consultas y operaciones de base de datos relacionadas con usuarios,
roles y autenticación OAuth.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.database import (
    User, 
    UserEmail,
    UserOauthIdentity, 
    RoleAssignment,
    UserStatus,
)
from src.database.utils import now_chile
from src.core.logging import get_logger
from src.core.encryption import get_encryption_service


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
        # Buscar por email en la tabla user_emails y hacer join con users
        result = await session.execute(
            select(User)
            .join(UserEmail, User.id == UserEmail.user_id)
            .options(
                selectinload(User.primary_email),
                selectinload(User.emails),
                selectinload(User.role_assignments).options(
                    selectinload(RoleAssignment.role),
                    selectinload(RoleAssignment.tenant),
                    selectinload(RoleAssignment.community)
                )
            )
            .where(UserEmail.email == email.lower())
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
            .options(
                selectinload(User.primary_email),
                selectinload(User.emails),
                selectinload(User.role_assignments).options(
                    selectinload(RoleAssignment.role),
                    selectinload(RoleAssignment.tenant),
                    selectinload(RoleAssignment.community)
                )
            )
            .where(User.id == user_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def create_user(
        session: AsyncSession,
        email: str,
        password_hash: Optional[str] = None,
        status: UserStatus = UserStatus.ACTIVE,
        email_verified_at: Optional[datetime] = None,
        full_name: Optional[str] = None,
        rut: Optional[str] = None,
        address: Optional[str] = None
    ) -> User:
        """
        Crear nuevo usuario con el nuevo modelo User/UserEmail.

        Args:
            session: Sesión de base de datos
            email: Email del usuario
            password_hash: Hash de contraseña (opcional para OAuth)
            status: Estado del usuario
            email_verified_at: Fecha de verificación del email
            full_name: Nombre completo del usuario
            rut: RUT chileno del usuario
            address: Dirección del usuario

        Returns:
            User: Usuario creado con su email primario
        """
        # 1. Crear el usuario con información personal
        user = User(
            password_hash=password_hash,
            status=status,
            full_name=full_name,
            rut=rut,
            address=address
        )
        session.add(user)
        await session.flush()  # Para obtener el ID del usuario

        # 2. Crear el email del usuario
        user_email = UserEmail(
            user_id=user.id,
            email=email.lower(),
            verified_at=email_verified_at,
            is_primary=True,
            email_type='personal'
        )
        session.add(user_email)
        await session.flush()  # Para obtener el ID del email

        # 3. Asignar el email como primario en el usuario
        user.primary_email_id = user_email.id
        await session.flush()

        # 4. Recargar el usuario con sus relaciones
        await session.refresh(user, ['primary_email', 'emails'])

        return user

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
            .options(
                selectinload(UserOauthIdentity.user).selectinload(User.primary_email),
                selectinload(UserOauthIdentity.user).selectinload(User.emails),
                selectinload(UserOauthIdentity.user).selectinload(User.role_assignments).selectinload(RoleAssignment.role),
                selectinload(UserOauthIdentity.user).selectinload(User.role_assignments).selectinload(RoleAssignment.tenant)
            )
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
        token_expires_at: Optional[datetime] = None,
        token_scope: Optional[str] = None
    ) -> UserOauthIdentity:
        """
        Crear nueva identidad OAuth.

        Args:
            session: Sesión de base de datos
            user_id: ID del usuario local
            provider: Proveedor OAuth
            provider_user_id: ID del usuario en el proveedor
            provider_email: Email del proveedor
            access_token: Token de acceso OAuth (será cifrado)
            refresh_token: Token de refresh OAuth (será cifrado)
            token_expires_at: Fecha de expiración del token
            token_scope: Scope del token OAuth

        Returns:
            UserOauthIdentity: Identidad OAuth creada
        """
        # Cifrar tokens usando el servicio de cifrado
        encryption_service = get_encryption_service()

        oauth_identity = UserOauthIdentity(
            user_id=user_id,
            provider=provider,
            provider_user_id=provider_user_id,
            provider_email=provider_email,
            encrypted_access_token=encryption_service.encrypt_token(access_token),
            encrypted_refresh_token=encryption_service.encrypt_token(refresh_token),
            token_expires_at=token_expires_at,
            token_scope=token_scope
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
        provider_email: Optional[str] = None,
        token_scope: Optional[str] = None
    ) -> None:
        """
        Actualizar tokens OAuth.

        Args:
            session: Sesión de base de datos
            oauth_identity: Identidad OAuth a actualizar
            access_token: Nuevo token de acceso (será cifrado)
            refresh_token: Nuevo token de refresh (será cifrado)
            token_expires_at: Nueva fecha de expiración
            provider_email: Nuevo email del proveedor
            token_scope: Nuevo scope del token
        """
        # Cifrar tokens usando el servicio de cifrado
        encryption_service = get_encryption_service()

        if access_token is not None:
            oauth_identity.encrypted_access_token = encryption_service.encrypt_token(access_token)
        if refresh_token is not None:
            oauth_identity.encrypted_refresh_token = encryption_service.encrypt_token(refresh_token)
        if token_expires_at is not None:
            oauth_identity.token_expires_at = token_expires_at
        if provider_email is not None:
            oauth_identity.provider_email = provider_email
        if token_scope is not None:
            oauth_identity.token_scope = token_scope

        oauth_identity.token_last_rotated_at = now_chile()

"""
Servicios de lógica de negocio para autenticación.

Contiene la lógica de negocio relacionada con autenticación, autorización
y gestión de usuarios.
"""

from typing import Optional, Dict, Any, List
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.database import User
from src.database.enums import (
    UserStatus,
    AuthProvider,
    AuthMethod,
    AuthResult,
    AuthFailureReason,
    RegistrationProvider,
)
from src.database.repositories import (
    AuthRepository,
    SessionRepository,
    LoginGatingRepository,
    RegistrationRequestRepository
)
from src.services.auth.log_service import create_auth_log_service
from src.core.logging import get_logger
from src.core.security import (
    verify_password, 
    get_password_hash, 
    create_user_tokens,
    create_user_tokens_with_session,
    hash_token,
    verify_token
)
from src.schemas import (
    UserResponse, 
    OAuthUserInfo,
    RoleResponse
)
from src.core.logging import get_logger


logger = get_logger(__name__)


class AuthService:
    """Servicio principal de autenticación."""

    @staticmethod
    def _get_all_user_role_names(user: User) -> List[str]:
        """
        Obtener todos los nombres de roles de un usuario de todas las asignaciones.

        Args:
            user: Usuario del cual obtener los roles

        Returns:
            List[str]: Lista de nombres de roles únicos
        """
        role_names = []
        # Obtener todos los roles del modelo unificado RoleAssignment
        for assignment in user.role_assignments:
            if assignment.role:
                role_names.append(assignment.role.name)

        return list(set(role_names))

    @staticmethod
    def _get_all_user_role_responses(user: User) -> List[RoleResponse]:
        """
        Obtener todas las respuestas de roles de un usuario de todas las asignaciones.

        Args:
            user: Usuario del cual obtener los roles

        Returns:
            List[RoleResponse]: Lista de respuestas de roles únicos
        """
        unique_roles = {}

        # Procesar todos los roles del modelo unificado RoleAssignment
        for assignment in user.role_assignments:
            if assignment.role:
                role_id = assignment.role.id
                if role_id not in unique_roles:
                    unique_roles[role_id] = RoleResponse(
                        id=assignment.role.id,
                        name=assignment.role.name,
                        created_at=assignment.role.created_at
                    )

        return list(unique_roles.values())

    @staticmethod
    async def authenticate_user(
        session: AsyncSession,
        email: str,
        password: str,
        user_agent: Optional[str] = None,
    ) -> Optional[tuple[User, UUID]]:
        """
        Autenticar usuario con email y contraseña incluyendo logging de seguridad.

        Args:
            session: Sesión de base de datos
            email: Email del usuario
            password: Contraseña en texto plano
            user_agent: User agent del navegador

        Returns:
            tuple[User, UUID]: Usuario autenticado y auth_log_id, o None si las credenciales son inválidas
        """
        auth_log_service = create_auth_log_service(session)
        user = None
        result = AuthResult.FAIL
        failure_reason = None

        try:
            # Verificar si el usuario puede hacer login (gated authentication)
            can_login = await LoginGatingRepository.can_user_login_by_email(session, email)

            if not can_login:
                # Usuario no puede hacer login (no está registrado/aprobado en el sistema)
                failure_reason = AuthFailureReason.ACCOUNT_SUSPENDED  # Usuario no registrado/aprobado
                user = None
            else:
                # Buscar usuario por email
                user = await AuthRepository.find_user_by_email(session, email)

                if not user:
                    failure_reason = AuthFailureReason.INVALID_EMAIL
                elif user.status != UserStatus.ACTIVE:
                    failure_reason = AuthFailureReason.ACCOUNT_SUSPENDED
                elif not user.password_hash:
                    failure_reason = AuthFailureReason.INVALID_PASSWORD
                elif not verify_password(password, user.password_hash):
                    failure_reason = AuthFailureReason.INVALID_PASSWORD
                    user = None  # Reset user para logging
                else:
                    result = AuthResult.SUCCESS

        except Exception as e:
            logger.error(f"Error during authentication: {e}", exc_info=True)
            failure_reason = AuthFailureReason.UNKNOWN_ERROR
            user = None

        finally:
            # Registrar intento de autenticación
            auth_log_result = await auth_log_service.log_authentication_attempt(
                email=email,
                provider=AuthProvider.LOCAL,
                method=AuthMethod.PASSWORD,
                result=result,
                failure_reason=failure_reason,
                user=user,
                user_agent=user_agent,
            )

        if result == AuthResult.SUCCESS:
            auth_log_id = UUID(auth_log_result['auth_log_id'])
            return user, auth_log_id
        else:
            return None

    @staticmethod
    async def create_user_with_password(
        session: AsyncSession,
        email: str,
        password: str,
        roles: Optional[List[str]] = None
    ) -> User:
        """
        Crear nuevo usuario con contraseña.

        Args:
            session: Sesión de base de datos
            email: Email del usuario
            password: Contraseña en texto plano
            roles: Lista de nombres de roles

        Returns:
            User: Usuario creado
        """
        # Crear hash de la contraseña
        password_hash = get_password_hash(password)

        # Crear usuario
        user = await AuthRepository.create_user(
            session,
            email=email,
            password_hash=password_hash,
            status=UserStatus.ACTIVE
        )

        # Asignar roles si se proporcionan
        if roles:
            await AuthRepository.assign_roles_to_user(session, user, roles)

        await session.commit()
        await session.refresh(user)

        return user

    @staticmethod
    async def get_user_by_id(session: AsyncSession, user_id: UUID) -> Optional[User]:
        """
        Obtener usuario por ID.

        Args:
            session: Sesión de base de datos
            user_id: ID del usuario

        Returns:
            User: Usuario encontrado o None
        """
        return await AuthRepository.find_user_by_id(session, user_id)

    @staticmethod
    async def refresh_access_token(
        session: AsyncSession, 
        refresh_token: str
    ) -> Optional[Dict[str, Any]]:
        """
        Refrescar token de acceso usando refresh token.

        Args:
            session: Sesión de base de datos
            refresh_token: Token de refresh

        Returns:
            Dict con nuevos tokens o None si el refresh token es inválido
        """
        # Verificar refresh token
        token_data = verify_token(refresh_token, expected_type="refresh")
        if not token_data:
            return None

        # Obtener usuario actual
        user = await AuthRepository.find_user_by_id(session, UUID(token_data.user_id))
        if not user or user.status != UserStatus.ACTIVE:
            return None

        # Crear nuevos tokens (deduplicar roles por nombre de todas las asignaciones)
        unique_role_names = AuthService._get_all_user_role_names(user)
        tokens = create_user_tokens(user.id, user.email, unique_role_names)

        return tokens

    @staticmethod
    def user_to_response(user: User) -> UserResponse:
        """
        Convertir modelo User a UserResponse.

        Args:
            user: Modelo de usuario

        Returns:
            UserResponse: Schema de respuesta
        """
        # Deduplicar roles por ID para evitar duplicados de todas las asignaciones
        role_responses = AuthService._get_all_user_role_responses(user)

        return UserResponse(
            id=user.id,
            email=user.email,
            email_verified_at=user.primary_email.verified_at if user.primary_email else None,
            status=user.status,
            roles=role_responses,
            created_at=user.created_at,
            updated_at=user.updated_at
        )

    @staticmethod
    async def create_session_for_user(
        session: AsyncSession,
        user: User,
        user_agent: Optional[str] = None,
        provider: AuthProvider = AuthProvider.LOCAL,
        method: AuthMethod = AuthMethod.PASSWORD,
        mfa_used: bool = False,
        log_authentication: bool = True
    ) -> Dict[str, Any]:
        """
        Crear sesión y tokens para un usuario con logging de autenticación opcional.

        Args:
            session: Sesión de base de datos
            user: Usuario para crear la sesión
            user_agent: User agent del cliente
            provider: Proveedor de autenticación
            method: Método de autenticación
            mfa_used: Si se utilizó MFA
            log_authentication: Si debe registrar el log de autenticación

        Returns:
            Dict: Tokens y metadatos de la sesión
        """
        auth_log_service = create_auth_log_service(session)

        # Crear tokens con metadatos de sesión (deduplicar roles por nombre de todas las asignaciones)
        unique_role_names = AuthService._get_all_user_role_names(user)
        token_data = create_user_tokens_with_session(
            user.id, 
            user.email, 
            unique_role_names,
            user_agent=user_agent
        )

        # Crear registro de sesión en base de datos
        user_session = await SessionRepository.create_session(
            session,
            user_id=user.id,
            tenant_id=user.tenant_id,
            access_token_hash=token_data["access_token_hash"],
            refresh_token_hash=token_data["refresh_token_hash"],
            expires_at=token_data["expires_at"],
            user_agent=user_agent
        )

        # Registrar autenticación exitosa con sesión creada (solo si se requiere)
        if log_authentication:
            await auth_log_service.log_authentication_attempt(
                email=user.email,
                provider=provider,
                method=method,
                result=AuthResult.SUCCESS,
                user=user,
                user_session=user_session,
                user_agent=user_agent,
                mfa_used=mfa_used,
            )

        await session.commit()

        # Retornar solo los datos necesarios para el cliente
        return {
            "access_token": token_data["access_token"],
            "refresh_token": token_data["refresh_token"],
            "expires_in": token_data["expires_in"],
            "token_type": token_data["token_type"],
            "session_id": str(user_session.id)
        }

    @staticmethod
    async def validate_session(
        session: AsyncSession,
        access_token: str
    ) -> Optional[User]:
        """
        Validar token de acceso contra sesiones activas.

        Args:
            session: Sesión de base de datos
            access_token: Token JWT de acceso

        Returns:
            User: Usuario si la sesión es válida, None en caso contrario
        """
        # Crear hash del token
        token_hash = hash_token(access_token)

        # Buscar sesión activa
        user_session = await SessionRepository.find_session_by_access_token(session, token_hash)

        if not user_session:
            return None

        # Verificar que la sesión sea válida
        if not user_session.is_valid():
            return None

        # Verificar que el token JWT sea válido
        token_data = verify_token(access_token)
        if not token_data:
            return None

        return user_session.user

    @staticmethod
    async def refresh_user_session(
        session: AsyncSession,
        refresh_token: str,
        user_agent: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Refrescar sesión usando refresh token.

        Args:
            session: Sesión de base de datos
            refresh_token: Token de refresh
            user_agent: User agent del cliente

        Returns:
            Dict: Nuevos tokens o None si el refresh token es inválido
        """
        # Verificar que el refresh token sea válido
        token_data = verify_token(refresh_token)
        if not token_data:
            return None

        # Buscar sesión por refresh token
        refresh_token_hash = hash_token(refresh_token)
        user_session = await SessionRepository.find_session_by_refresh_token(session, refresh_token_hash)

        if not user_session:
            return None

        # Verificar que la sesión sea válida
        if not user_session.is_valid():
            return None

        # Revocar la sesión actual
        await SessionRepository.revoke_session(session, user_session)

        # Crear nueva sesión
        return await AuthService.create_session_for_user(
            session,
            user_session.user,
            user_agent=user_agent
        )

    @staticmethod
    async def logout_user(
        session: AsyncSession,
        access_token: str
    ) -> bool:
        """
        Cerrar sesión de usuario revocando su sesión.

        Args:
            session: Sesión de base de datos
            access_token: Token de acceso a revocar

        Returns:
            bool: True si se revocó la sesión exitosamente
        """
        # Buscar sesión por access token
        token_hash = hash_token(access_token)
        user_session = await SessionRepository.find_session_by_access_token(session, token_hash)

        if not user_session:
            return False

        # Revocar sesión
        await SessionRepository.revoke_session(session, user_session)
        await session.commit()

        return True

    @staticmethod
    async def _create_oauth_registration_request(
        session: AsyncSession,
        oauth_info: OAuthUserInfo,
        user_agent: Optional[str] = None,
    ) -> None:
        """
        Crear solicitud de registro automática para usuarios OAuth no aprobados.

        Args:
            session: Sesión de base de datos
            oauth_info: Información del usuario OAuth
            user_agent: User agent del navegador
        """
        try:
            # Verificar si ya existe una solicitud pendiente
            existing_request = await RegistrationRequestRepository.find_pending_request_by_email(
                session, oauth_info.email
            )

            if existing_request:
                logger.debug(f"Registration request already exists for OAuth user")
                return

            # Obtener tenant y comunidad por defecto
            default_tenant = await LoginGatingRepository.find_default_tenant(session)
            if not default_tenant:
                logger.error("No default tenant configured for OAuth auto registration")
                return

            default_community = await LoginGatingRepository.find_default_community_for_tenant(
                session, default_tenant.id
            )
            if not default_community:
                logger.error(f"No default community configured for tenant {default_tenant.id}")
                return

            # Crear la solicitud
            await RegistrationRequestRepository.create_registration_request(
                session=session,
                tenant_id=default_tenant.id,
                community_id=default_community.id,
                email=oauth_info.email,
                provider=RegistrationProvider.GOOGLE,  # Asumiendo Google
                full_name=None  # Se puede extraer del OAuth info si está disponible
            )

            logger.debug(f"Created auto registration request for OAuth user")

        except Exception as e:
            logger.error(f"Error creating OAuth registration request: {e}", exc_info=True)

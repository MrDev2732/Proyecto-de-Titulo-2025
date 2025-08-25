"""
Servicios de lógica de negocio para autenticación.

Contiene la lógica de negocio relacionada con autenticación, autorización
y gestión de usuarios.
"""

from datetime import timedelta
from typing import Optional, Dict, Any, List
from uuid import UUID

import httpx
from authlib.integrations.requests_client import OAuth2Session
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import User
from src.database.enums import UserStatus, OAuthProvider, AuthProvider, AuthMethod, AuthResult, AuthFailureReason
from src.database.repositories.auth_repository import AuthRepository, OAuthRepository, SessionRepository
from src.services.auth_log_service import create_auth_log_service
from src.core.security import (
    verify_password, 
    get_password_hash, 
    create_user_tokens,
    create_user_tokens_with_session,
    hash_token,
    verify_token
)
from src.schemas.auth_schemas import (
    UserResponse, 
    OAuthUserInfo,
    RoleResponse
)
from src.core.config import settings
from src.database.timezone_utils import now_chile
from src.core.logging import get_logger


logger = get_logger(__name__)


class AuthService:
    """Servicio principal de autenticación."""

    @staticmethod
    async def authenticate_user(
        session: AsyncSession,
        email: str,
        password: str,
        ip: Optional[str] = None,
        user_agent: Optional[str] = None,
        geo_country: Optional[str] = None,
        tenant_id: Optional[UUID] = None
    ) -> Optional[tuple[User, UUID]]:
        """
        Autenticar usuario con email y contraseña incluyendo logging de seguridad.

        Args:
            session: Sesión de base de datos
            email: Email del usuario
            password: Contraseña en texto plano
            ip: Dirección IP del cliente
            user_agent: User agent del navegador
            geo_country: Código de país ISO-3166 alpha-2
            tenant_id: ID del tenant

        Returns:
            tuple[User, UUID]: Usuario autenticado y auth_log_id, o None si las credenciales son inválidas
        """
        auth_log_service = create_auth_log_service(session)
        user = None
        result = AuthResult.FAIL
        failure_reason = None

        try:
            # Verificar seguridad pre-autenticación
            # Solo hacer verificación si tenemos una IP válida (y no es localhost en desarrollo)
            if ip and ip not in ["127.0.0.1", "localhost", "::1"]:
                security_check = await auth_log_service.check_pre_auth_security(
                    ip=ip,
                    email=email,
                    user_agent=user_agent,
                    geo_country=geo_country
                )

                # Si está bloqueado, registrar y retornar None
                if security_check['block_request']:
                    await auth_log_service.log_authentication_attempt(
                        email=email,
                        provider=AuthProvider.LOCAL,
                        method=AuthMethod.PASSWORD,
                        result=AuthResult.FAIL,
                        failure_reason=AuthFailureReason.RATE_LIMITED,
                        ip=ip,
                        user_agent=user_agent,
                        geo_country=geo_country,
                        tenant_id=tenant_id
                    )
                    return None

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
                ip=ip,
                user_agent=user_agent,
                geo_country=geo_country,
                tenant_id=tenant_id
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

        # Crear nuevos tokens
        role_names = [role.name for role in user.roles]
        tokens = create_user_tokens(user.id, user.email, role_names)

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
        role_responses = [
            RoleResponse(
                id=role.id,
                name=role.name,
                created_at=role.created_at
            )
            for role in user.roles
        ]

        return UserResponse(
            id=user.id,
            email=user.email,
            email_verified_at=user.email_verified_at,
            status=user.status,
            roles=role_responses,
            created_at=user.created_at,
            updated_at=user.updated_at
        )

    @staticmethod
    async def create_session_for_user(
        session: AsyncSession,
        user: User,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        geo_country: Optional[str] = None,
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
            ip_address: Dirección IP del cliente
            user_agent: User agent del cliente
            geo_country: Código de país
            provider: Proveedor de autenticación
            method: Método de autenticación
            mfa_used: Si se utilizó MFA
            log_authentication: Si debe registrar el log de autenticación

        Returns:
            Dict: Tokens y metadatos de la sesión
        """
        auth_log_service = create_auth_log_service(session)

        # Crear tokens con metadatos de sesión
        role_names = [role.name for role in user.roles]
        token_data = create_user_tokens_with_session(
            user.id, 
            user.email, 
            role_names,
            ip_address=ip_address,
            user_agent=user_agent
        )

        # Crear registro de sesión en base de datos
        user_session = await SessionRepository.create_session(
            session,
            user_id=user.id,
            access_token_hash=token_data["access_token_hash"],
            refresh_token_hash=token_data["refresh_token_hash"],
            expires_at=token_data["expires_at"],
            ip_address=ip_address,
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
                ip=ip_address,
                user_agent=user_agent,
                geo_country=geo_country,
                mfa_used=mfa_used,
                tenant_id=getattr(user, 'tenant_id', None)
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
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Refrescar sesión usando refresh token.

        Args:
            session: Sesión de base de datos
            refresh_token: Token de refresh
            ip_address: Dirección IP del cliente
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
            ip_address=ip_address,
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


class GoogleOAuthService:
    """Servicio para autenticación OAuth con Google."""

    @staticmethod
    def get_authorization_url(state: str) -> str:
        """
        Generar URL de autorización de Google.

        Args:
            state: Estado para validación CSRF

        Returns:
            str: URL de autorización
        """
        oauth = OAuth2Session(
            client_id=settings.google_oauth.client_id,
            redirect_uri=settings.google_oauth.redirect_uri,
            scope=settings.google_oauth.scope
        )

        authorization_url, _ = oauth.create_authorization_url(
            'https://accounts.google.com/o/oauth2/auth',
            state=state
        )

        return authorization_url

    @staticmethod
    async def exchange_code_for_user_info(code: str) -> Optional[OAuthUserInfo]:
        """
        Intercambiar código de autorización por información del usuario.

        Args:
            code: Código de autorización de Google

        Returns:
            OAuthUserInfo: Información del usuario o None si hay error
        """
        try:
            # Intercambiar código por tokens
            async with httpx.AsyncClient() as client:
                token_response = await client.post(
                    'https://oauth2.googleapis.com/token',
                    data={
                        'client_id': settings.google_oauth.client_id,
                        'client_secret': settings.google_oauth.client_secret,
                        'code': code,
                        'grant_type': 'authorization_code',
                        'redirect_uri': settings.google_oauth.redirect_uri,
                    }
                )

                if token_response.status_code != 200:
                    logger.error(f"Error en OAuth token exchange: {token_response.text}")
                    return None

                token_data = token_response.json()
                access_token = token_data.get('access_token')
                refresh_token = token_data.get('refresh_token')
                expires_in = token_data.get('expires_in')

                if not access_token:
                    return None

                # Obtener información del usuario
                user_response = await client.get(
                    'https://www.googleapis.com/oauth2/v2/userinfo',
                    headers={'Authorization': f'Bearer {access_token}'}
                )

                if user_response.status_code != 200:
                    logger.error(f"Error obteniendo info de usuario: {user_response.text}")
                    return None

                user_data = user_response.json()

                # Calcular fecha de expiración
                token_expires_at = None
                if expires_in:
                    token_expires_at = now_chile() + timedelta(seconds=expires_in)

                return OAuthUserInfo(
                    provider_user_id=user_data['id'],
                    email=user_data['email'],
                    provider=OAuthProvider.GOOGLE,
                    access_token=access_token,
                    refresh_token=refresh_token,
                    token_expires_at=token_expires_at
                )

        except Exception as e:
            logger.error(f"Error en OAuth: {e}", exc_info=True)
            return None

    @staticmethod
    async def authenticate_or_create_oauth_user(
        session: AsyncSession,
        oauth_info: OAuthUserInfo,
        ip: Optional[str] = None,
        user_agent: Optional[str] = None,
        geo_country: Optional[str] = None
    ) -> tuple[User, UUID]:
        """
        Autenticar o crear usuario OAuth con logging de seguridad.

        Args:
            session: Sesión de base de datos
            oauth_info: Información del usuario OAuth
            ip: Dirección IP del cliente
            user_agent: User agent del navegador
            geo_country: Código de país

        Returns:
            tuple[User, UUID]: Usuario autenticado o creado y el ID del log de autenticación
        """
        auth_log_service = create_auth_log_service(session)
        user = None

        try:
            # Verificar seguridad pre-autenticación para OAuth (solo si tenemos IP)
            # NOTA: En desarrollo, deshabilitamos verificaciones estrictas para localhost
            if ip and settings.environment != "DEVELOPMENT":
                security_check = await auth_log_service.check_pre_auth_security(
                    ip=ip,
                    email=oauth_info.email,
                    user_agent=user_agent,
                    geo_country=geo_country
                )

                # OAuth es generalmente menos restrictivo, pero aún verificamos
                if security_check['block_request'] and security_check['metrics']['risk_score'] > 95:
                    await auth_log_service.log_authentication_attempt(
                        email=oauth_info.email,
                        provider=AuthProvider.GOOGLE,  # Asumiendo Google OAuth
                        method=AuthMethod.OAUTH,
                        result=AuthResult.FAIL,
                        failure_reason=AuthFailureReason.RATE_LIMITED,
                        ip=ip,
                        user_agent=user_agent,
                        geo_country=geo_country
                    )
                    raise Exception("OAuth authentication blocked due to high risk")

            # Buscar identidad OAuth existente
            oauth_identity = await OAuthRepository.find_oauth_identity(
                session,
                oauth_info.provider,
                oauth_info.provider_user_id
            )

            if oauth_identity:
                # Usuario existente - actualizar tokens
                await OAuthRepository.update_oauth_tokens(
                    session,
                    oauth_identity,
                    access_token=oauth_info.access_token,
                    refresh_token=oauth_info.refresh_token,
                    token_expires_at=oauth_info.token_expires_at,
                    provider_email=oauth_info.email
                )
                user = oauth_identity.user
            else:
                # Buscar usuario por email
                user = await AuthRepository.find_user_by_email(session, oauth_info.email)

                if not user:
                    # Crear nuevo usuario
                    user = await AuthRepository.create_user(
                        session,
                        email=oauth_info.email,
                        status=UserStatus.ACTIVE,
                        email_verified_at=now_chile()
                    )

                # Crear identidad OAuth
                await OAuthRepository.create_oauth_identity(
                    session,
                    user_id=user.id,
                    provider=oauth_info.provider,
                    provider_user_id=oauth_info.provider_user_id,
                    provider_email=oauth_info.email,
                    access_token=oauth_info.access_token,
                    refresh_token=oauth_info.refresh_token,
                    token_expires_at=oauth_info.token_expires_at
                )

            # Registrar autenticación OAuth exitosa
            auth_log_result = await auth_log_service.log_authentication_attempt(
                email=oauth_info.email,
                provider=AuthProvider.GOOGLE,  # Asumiendo Google OAuth
                method=AuthMethod.OAUTH,
                result=AuthResult.SUCCESS,
                user=user,
                ip=ip,
                user_agent=user_agent,
                geo_country=geo_country,
                tenant_id=getattr(user, 'tenant_id', None)
            )

            await session.commit()
            await session.refresh(user)

            # Retornar usuario y el ID del log para actualizarlo después con user_session_id
            auth_log_id = UUID(auth_log_result['auth_log_id'])
            return user, auth_log_id

        except Exception as e:
            # Registrar fallo OAuth
            await auth_log_service.log_authentication_attempt(
                email=oauth_info.email,
                provider=AuthProvider.GOOGLE,  # Asumiendo Google OAuth
                method=AuthMethod.OAUTH,
                result=AuthResult.FAIL,
                failure_reason=AuthFailureReason.OAUTH_ERROR,
                error_code=str(e),
                ip=ip,
                user_agent=user_agent,
                geo_country=geo_country
            )
            raise

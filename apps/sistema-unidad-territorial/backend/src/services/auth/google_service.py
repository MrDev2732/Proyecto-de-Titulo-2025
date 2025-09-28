from datetime import timedelta
from typing import Optional
from uuid import UUID

import httpx
from authlib.integrations.requests_client import OAuth2Session
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import User
from src.database.enums import (
    UserStatus,
    OAuthProvider,
    AuthProvider,
    AuthMethod,
    AuthResult,
    AuthFailureReason,
)
from src.database.repositories.auth_repository import AuthRepository, OAuthRepository
from src.database.repositories.login_gating_repository import LoginGatingRepository
from src.services.auth.log_service import create_auth_log_service
from src.schemas.auth_schemas import OAuthUserInfo
from src.core.config import settings
from src.database import now_chile
from src.core.logging import get_logger


logger = get_logger(__name__)


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
    ) -> Optional[tuple[User, UUID]]:
        """
        Autenticar usuario OAuth con gated access control.

        Args:
            session: Sesión de base de datos
            oauth_info: Información del usuario OAuth
            ip: Dirección IP del cliente
            user_agent: User agent del navegador
            geo_country: Código de país

        Returns:
            tuple[User, UUID]: Usuario autenticado y el ID del log, o None si no puede hacer login
        """
        logger.debug(f"Starting OAuth authentication for: {oauth_info.email}")
        auth_log_service = create_auth_log_service(session)
        user = None
        failure_reason = None

        try:
            # Verificar seguridad pre-autenticación para OAuth (solo si tenemos IP)
            if ip and settings.environment != "DEVELOPMENT":
                security_check = await auth_log_service.check_pre_auth_security(
                    ip=ip,
                    email=oauth_info.email,
                    user_agent=user_agent,
                    geo_country=geo_country
                )

                if security_check['block_request'] and security_check['metrics']['risk_score'] > 95:
                    await auth_log_service.log_authentication_attempt(
                        email=oauth_info.email,
                        provider=AuthProvider.GOOGLE,
                        method=AuthMethod.OAUTH,
                        result=AuthResult.FAIL,
                        failure_reason=AuthFailureReason.RATE_LIMITED,
                        ip=ip,
                        user_agent=user_agent,
                        geo_country=geo_country
                    )
                    return None

            # Verificar si el usuario puede hacer login OAuth (gated authentication)
            logger.debug(f"Checking OAuth login for: {oauth_info.email}")
            can_login = await LoginGatingRepository.can_user_login_by_oauth(
                session, 
                oauth_info.provider, 
                oauth_info.provider_user_id
            )
            logger.debug(f"OAuth login check completed")

            if not can_login:
                # Verificar si el usuario existe por email (para usuarios existentes sin OAuth)
                existing_user = await AuthRepository.find_user_by_email(session, oauth_info.email)

                logger.debug(f"Checking existing user for OAuth authentication")

                if existing_user and existing_user.status == UserStatus.ACTIVE:
                    # Usuario existe pero no tiene identidad OAuth - crear la identidad OAuth
                    logger.debug(f"Creating OAuth identity for existing user")

                    oauth_identity = await OAuthRepository.create_oauth_identity(
                        session,
                        user_id=existing_user.id,
                        provider=oauth_info.provider,
                        provider_user_id=oauth_info.provider_user_id,
                        provider_email=oauth_info.email,
                        access_token=oauth_info.access_token,
                        refresh_token=oauth_info.refresh_token,
                        token_expires_at=oauth_info.token_expires_at
                    )
                    logger.debug(f"OAuth identity created successfully")

                    # Ahora verificar si puede hacer login con la nueva identidad OAuth
                    can_login_now = await LoginGatingRepository.can_user_login_by_oauth(
                        session, 
                        oauth_info.provider, 
                        oauth_info.provider_user_id
                    )

                    if can_login_now:
                        # Proceder con la autenticación exitosa
                        user = existing_user
                    else:
                        failure_reason = AuthFailureReason.ACCOUNT_SUSPENDED
                        raise Exception("User access check failed after OAuth identity creation")
                else:
                    # Usuario no existe o no está activo - crear solicitud de registro automática
                    await AuthService._create_oauth_registration_request(
                        session, oauth_info, ip, user_agent, geo_country
                    )
                    failure_reason = AuthFailureReason.ACCOUNT_SUSPENDED

                    await auth_log_service.log_authentication_attempt(
                        email=oauth_info.email,
                        provider=AuthProvider.GOOGLE,
                        method=AuthMethod.OAUTH,
                        result=AuthResult.FAIL,
                        failure_reason=failure_reason,
                        ip=ip,
                        user_agent=user_agent,
                        geo_country=geo_country
                    )
                    return None
            else:
                # Usuario puede hacer login - buscar identidad OAuth existente
                oauth_identity = await OAuthRepository.find_oauth_identity(
                    session,
                    oauth_info.provider,
                    oauth_info.provider_user_id
                )

                if oauth_identity:
                    user = oauth_identity.user
                else:
                    logger.error(f"OAuth identity not found after login gate check")
                    failure_reason = AuthFailureReason.OAUTH_ERROR
                    raise Exception("OAuth identity not found after login gate verification")

            # Actualizar tokens OAuth si el usuario ya tenía una identidad
            if 'oauth_identity' in locals():
                # Usuario tenía identidad OAuth existente o acabamos de crear una nueva
                await OAuthRepository.update_oauth_tokens(
                    session,
                    oauth_identity,
                    access_token=oauth_info.access_token,
                    refresh_token=oauth_info.refresh_token,
                    token_expires_at=oauth_info.token_expires_at,
                    provider_email=oauth_info.email
                )
                if 'user' not in locals():
                    user = oauth_identity.user

            # Registrar autenticación OAuth exitosa
            auth_log_result = await auth_log_service.log_authentication_attempt(
                email=oauth_info.email,
                provider=AuthProvider.GOOGLE,
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

            auth_log_id = UUID(auth_log_result['auth_log_id'])
            return user, auth_log_id

        except Exception as e:
            logger.error(f"Exception in OAuth authentication: {e}", exc_info=True)
            # Registrar fallo OAuth
            await auth_log_service.log_authentication_attempt(
                email=oauth_info.email,
                provider=AuthProvider.GOOGLE,
                method=AuthMethod.OAUTH,
                result=AuthResult.FAIL,
                failure_reason=failure_reason or AuthFailureReason.OAUTH_ERROR,
                error_code=str(e),
                ip=ip,
                user_agent=user_agent,
                geo_country=geo_country
            )
            return None

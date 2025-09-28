"""
Servicio para logging de autenticación y análisis de seguridad.

Integra el logging robusto de autenticación con análisis de riesgo
y decisiones de seguridad automáticas.
"""

from datetime import datetime
from typing import Optional, Dict, Any
from uuid import UUID
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from src.database.repositories.auth_log_repository import AuthenticationLogRepository
from src.database.auth_security_utils import create_security_analyzer
from src.database.enums import AuthProvider, AuthMethod, AuthResult, AuthFailureReason
from src.database import User, UserSession
from src.core.logging import get_logger

logger = get_logger(__name__)


class AuthenticationLogService:
    """Servicio para logging de autenticación y análisis de seguridad."""

    def __init__(self, session: AsyncSession, security_profile: str = 'moderate'):
        self.session = session
        self.repository = AuthenticationLogRepository()
        self.security_analyzer = create_security_analyzer(session, security_profile)

    async def log_authentication_attempt(
        self,
        email: Optional[str] = None,
        provider: AuthProvider = AuthProvider.LOCAL,
        method: AuthMethod = AuthMethod.PASSWORD,
        result: AuthResult = AuthResult.FAIL,
        failure_reason: Optional[AuthFailureReason] = None,
        user: Optional[User] = None,
        user_session: Optional[UserSession] = None,
        ip: Optional[str] = None,
        user_agent: Optional[str] = None,
        geo_country: Optional[str] = None,
        error_code: Optional[str] = None,
        mfa_used: bool = False,
        tenant_id: Optional[UUID] = None,
        request_id: Optional[UUID] = None
    ) -> Dict[str, Any]:
        """
        Registrar intento de autenticación con análisis de riesgo.

        Args:
            email: Email utilizado en el intento
            provider: Proveedor de autenticación
            method: Método de autenticación
            result: Resultado del intento
            failure_reason: Razón del fallo (si aplica)
            user: Usuario (si se identificó)
            user_session: Sesión creada (si el login fue exitoso)
            ip: Dirección IP del cliente
            user_agent: User agent del navegador
            geo_country: Código de país ISO-3166 alpha-2
            error_code: Código de error interno
            mfa_used: Si se utilizó MFA
            tenant_id: ID del tenant
            request_id: ID de correlación

        Returns:
            Dict con el log creado y métricas de seguridad
        """
        try:
            # Generar request_id si no se proporciona
            if not request_id:
                request_id = uuid.uuid4()

            # Calcular risk score antes del logging
            risk_score = 0
            if ip:
                risk_score = await self.security_analyzer.calculate_risk_score(
                    ip=ip,
                    email=email,
                    user_agent=user_agent,
                    geo_country=geo_country
                )

            # Crear log de autenticación
            auth_log = await self.repository.create_auth_log(
                session=self.session,
                tenant_id=tenant_id or (user.tenant_id if hasattr(user, 'tenant_id') and user else None),
                user_id=user.id if user else None,
                user_session_id=user_session.id if user_session else None,
                email=email,
                provider=provider,
                method=method,
                result=result,
                failure_reason=failure_reason,
                error_code=error_code,
                mfa_used=mfa_used,
                risk_score=risk_score,
                ip=ip,
                user_agent=user_agent,
                geo_country=geo_country,
                request_id=request_id
            )

            # Log estructurado para aplicación
            log_data = {
                'auth_log_id': str(auth_log.id),
                'email': email,
                'result': result.value,
                'provider': provider.value,
                'method': method.value,
                'ip': ip,
                'risk_score': risk_score,
                'geo_country': geo_country,
                'request_id': str(request_id)
            }

            if result == AuthResult.SUCCESS:
                logger.info(f"Successful authentication: {log_data}")
            else:
                logger.warning(f"Failed authentication: {log_data}")

            # Commit para que los triggers puedan ejecutarse
            await self.session.commit()

            return {
                'auth_log': auth_log,
                'auth_log_id': str(auth_log.id),
                'risk_score': risk_score,
                'request_id': request_id,
                'logged_at': auth_log.created_at
            }

        except Exception as e:
            await self.session.rollback()
            logger.error(f"Error logging authentication attempt: {e}", exc_info=True)
            raise

    async def check_pre_auth_security(
        self,
        ip: str,
        email: Optional[str] = None,
        user_agent: Optional[str] = None,
        geo_country: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Verificar seguridad antes del intento de autenticación.

        Args:
            ip: Dirección IP del cliente
            email: Email del intento (opcional)
            user_agent: User agent del cliente (opcional)
            geo_country: País de origen (opcional)

        Returns:
            Dict con recomendaciones de seguridad
        """
        try:
            recommendations = await self.security_analyzer.get_security_recommendations(
                ip=ip,
                email=email,
                user_agent=user_agent,
                geo_country=geo_country
            )

            # Log de decisiones de seguridad importantes
            if recommendations['block_request']:
                logger.warning(
                    f"Blocking authentication attempt - IP: {ip}, email: {email}, "
                    f"risk_score: {recommendations['metrics']['risk_score']}"
                )
            elif recommendations['require_mfa']:
                logger.info(
                    f"MFA required for authentication - IP: {ip}, email: {email}, "
                    f"risk_score: {recommendations['metrics']['risk_score']}"
                )

            return recommendations

        except Exception as e:
            logger.error(f"Error in pre-auth security check: {e}", exc_info=True)
            # En caso de error, permitir el intento pero con precaución
            return {
                'allow_attempt': True,
                'require_captcha': True,
                'require_mfa': False,
                'require_email_verification': False,
                'block_request': False,
                'delay_response': True,
                'metrics': {
                    'risk_score': 50,
                    'error': str(e)
                }
            }


# Función helper para crear el servicio
def create_auth_log_service(
    session: AsyncSession,
    security_profile: str = 'moderate'
) -> AuthenticationLogService:
    """
    Factory function para crear el servicio de logging de autenticación.

    Args:
        session: Sesión de SQLAlchemy
        security_profile: Perfil de seguridad ('strict', 'moderate', 'lenient')

    Returns:
        AuthenticationLogService configurado
    """
    return AuthenticationLogService(session, security_profile)

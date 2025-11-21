"""
Servicio para logging de autenticación y análisis de seguridad.

Integra el logging robusto de autenticación con análisis de riesgo
y decisiones de seguridad automáticas.
"""

from typing import Optional, Dict, Any
from uuid import UUID
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from src.database.repositories import AuthenticationLogRepository
from src.database.enums import AuthProvider, AuthMethod, AuthResult, AuthFailureReason
from src.database import User, UserSession
from src.core.logging import get_logger


logger = get_logger(__name__)


class AuthenticationLogService:
    """Servicio para logging de autenticación y análisis de seguridad."""

    def __init__(self, session: AsyncSession, security_profile: str = 'moderate'):
        self.session = session
        self.repository = AuthenticationLogRepository()

    async def log_authentication_attempt(
        self,
        email: Optional[str] = None,
        provider: AuthProvider = AuthProvider.LOCAL,
        method: AuthMethod = AuthMethod.PASSWORD,
        result: AuthResult = AuthResult.FAIL,
        failure_reason: Optional[AuthFailureReason] = None,
        user: Optional[User] = None,
        user_session: Optional[UserSession] = None,
        user_agent: Optional[str] = None,
        error_code: Optional[str] = None,
        mfa_used: bool = False,
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
            user_agent: User agent del navegador
            error_code: Código de error interno
            mfa_used: Si se utilizó MFA
            request_id: ID de correlación

        Returns:
            Dict con el log creado y métricas de seguridad
        """
        try:
            # Generar request_id si no se proporciona
            if not request_id:
                request_id = uuid.uuid4()

            # Crear log de autenticación
            auth_log = await self.repository.create_auth_log(
                session=self.session,
                tenant_id=user.tenant_id if user else None,
                user_id=user.id if user else None,
                user_session_id=user_session.id if user_session else None,
                email=email,
                provider=provider,
                method=method,
                result=result,
                failure_reason=failure_reason,
                error_code=error_code,
                mfa_used=mfa_used,
                user_agent=user_agent,
                request_id=request_id
            )

            # Log estructurado para aplicación
            log_data = {
                'auth_log_id': str(auth_log.id),
                'email': email,
                'result': result.value,
                'provider': provider.value,
                'method': method.value,
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
                'request_id': request_id,
                'logged_at': auth_log.created_at
            }

        except Exception as e:
            await self.session.rollback()
            logger.error(f"Error logging authentication attempt: {e}", exc_info=True)
            raise


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

"""
Repository para manejo de datos de logging de autenticación.

Contiene todas las consultas y operaciones de base de datos relacionadas con
el logging de eventos de autenticación, análisis de seguridad y detección de amenazas.
"""

from datetime import timedelta
from typing import List, Optional, Dict, Any
from uuid import UUID

from sqlalchemy import select, func, and_, or_, desc, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import (
    AuthenticationLog,
    AuthResult,
    AuthFailureReason,
    AuthProvider,
    AuthMethod,
)
from src.database.utils import now_chile
from src.core.logging import get_logger


logger = get_logger(__name__)


class AuthenticationLogRepository:
    """Repository para operaciones con logs de autenticación."""

    @staticmethod
    async def create_auth_log(
        session: AsyncSession,
        tenant_id: Optional[UUID] = None,
        user_id: Optional[UUID] = None,
        user_session_id: Optional[UUID] = None,
        email: Optional[str] = None,
        provider: AuthProvider = AuthProvider.LOCAL,
        method: AuthMethod = AuthMethod.PASSWORD,
        result: AuthResult = AuthResult.FAIL,
        failure_reason: Optional[AuthFailureReason] = None,
        error_code: Optional[str] = None,
        mfa_used: bool = False,
        user_agent: Optional[str] = None,
        request_id: Optional[UUID] = None
    ) -> AuthenticationLog:
        """
        Crear nuevo log de autenticación.

        Args:
            session: Sesión de base de datos
            tenant_id: ID del tenant (opcional)
            user_id: ID del usuario (opcional)
            user_session_id: ID de la sesión creada (opcional)
            email: Email utilizado en el intento
            provider: Proveedor de autenticación
            method: Método de autenticación
            result: Resultado del intento
            failure_reason: Razón del fallo (si aplica)
            error_code: Código de error interno (opcional)
            mfa_used: Si se utilizó MFA
            user_agent: User agent del navegador
            request_id: ID de correlación con logs de aplicación

        Returns:
            AuthenticationLog: Log de autenticación creado
        """
        auth_log = AuthenticationLog(
            tenant_id=tenant_id,
            user_id=user_id,
            user_session_id=user_session_id,
            email=email.lower() if email else None,
            provider=provider,
            method=method,
            result=result,
            failure_reason=failure_reason,
            error_code=error_code,
            mfa_used=mfa_used,
            user_agent=user_agent,
            request_id=request_id
        )

        session.add(auth_log)
        await session.flush()
        return auth_log

    @staticmethod
    async def count_failures_by_email(
        session: AsyncSession,
        email: str,
        minutes: int = 15
    ) -> int:
        """
        Contar fallos por email en ventana de tiempo.

        Args:
            session: Sesión de base de datos
            email: Email del usuario
            minutes: Ventana de tiempo en minutos

        Returns:
            int: Número de fallos
        """
        time_threshold = now_chile() - timedelta(minutes=minutes)

        result = await session.execute(
            select(func.count(AuthenticationLog.id)).where(
                and_(
                    AuthenticationLog.email == email.lower(),
                    AuthenticationLog.result == AuthResult.FAIL,
                    AuthenticationLog.created_at > time_threshold
                )
            )
        )
        return result.scalar() or 0

    @staticmethod
    async def get_email_analysis(
        session: AsyncSession,
        email: str,
        days: int = 7
    ) -> Dict[str, Any]:
        """
        Obtener análisis completo de un email.

        Args:
            session: Sesión de base de datos
            email: Email del usuario
            days: Días hacia atrás para el análisis

        Returns:
            Dict: Análisis del email
        """
        time_threshold = now_chile() - timedelta(days=days)

        result = await session.execute(
            select(
                func.count(AuthenticationLog.id).label('total_attempts'),
                func.count(AuthenticationLog.id).filter(
                    AuthenticationLog.result == AuthResult.FAIL
                ).label('failed_attempts'),
            ).where(
                and_(
                    AuthenticationLog.email == email.lower(),
                    AuthenticationLog.created_at > time_threshold
                )
            )
        )

        row = result.fetchone()
        if not row or row.total_attempts == 0:
            return {
                'total_attempts': 0,
                'failed_attempts': 0,
                'unique_countries': 0,
                'failure_rate': 0.0,
                'avg_risk_score': 0.0
            }

        failure_rate = (row.failed_attempts / row.total_attempts) * 100 if row.total_attempts > 0 else 0

        return {
            'total_attempts': row.total_attempts,
            'failed_attempts': row.failed_attempts,
            'failure_rate': round(failure_rate, 2),
            'avg_risk_score': 0
        }

    @staticmethod
    async def count_recent_attempts(
        session: AsyncSession,
        email: Optional[str] = None,
        minutes: int = 5
    ) -> int:
        """
        Contar intentos recientes (para análisis de velocidad).

        Args:
            session: Sesión de base de datos
            email: Email (opcional)
            minutes: Ventana de tiempo en minutos

        Returns:
            int: Número de intentos recientes
        """
        time_threshold = now_chile() - timedelta(minutes=minutes)

        conditions = [AuthenticationLog.created_at > time_threshold]

        if email:
            conditions.append(AuthenticationLog.email == email.lower())
        else:
            return 0

        result = await session.execute(
            select(func.count(AuthenticationLog.id)).where(and_(*conditions))
        )
        return result.scalar() or 0

    @staticmethod
    async def update_auth_log_session(
        session: AsyncSession,
        auth_log_id: UUID,
        user_session_id: UUID
    ) -> bool:
        """
        Actualizar un log de autenticación con el ID de sesión.

        Args:
            session: Sesión de base de datos
            auth_log_id: ID del log de autenticación
            user_session_id: ID de la sesión de usuario

        Returns:
            True si se actualizó correctamente
        """
        try:
            result = await session.execute(
                update(AuthenticationLog)
                .where(AuthenticationLog.id == auth_log_id)
                .values(user_session_id=user_session_id)
            )

            await session.commit()
            return result.rowcount > 0

        except Exception as e:
            logger.error(f"Error updating auth log {auth_log_id} with session {user_session_id}: {e}")
            await session.rollback()
            return False

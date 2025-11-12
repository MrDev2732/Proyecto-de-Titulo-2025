from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.database import (
    User, 
    UserSession,
    RoleAssignment,
    ResidentMembership,
)
from src.core.logging import get_logger


logger = get_logger(__name__)


class SessionRepository:
    """Repository para operaciones con sesiones de usuario."""

    @staticmethod
    async def create_session(
        session: AsyncSession,
        user_id: UUID,
        tenant_id: UUID,
        access_token_hash: str,
        refresh_token_hash: Optional[str],
        expires_at: datetime,
        user_agent: Optional[str] = None
    ) -> UserSession:
        """
        Crear nueva sesión de usuario.

        Args:
            session: Sesión de base de datos
            user_id: ID del usuario
            tenant_id: ID del tenant
            access_token_hash: Hash del access token
            refresh_token_hash: Hash del refresh token (opcional)
            expires_at: Fecha de expiración
            user_agent: User agent del cliente

        Returns:
            UserSession: Sesión creada
        """
        user_session = UserSession(
            user_id=user_id,
            tenant_id=tenant_id,
            access_token_hash=access_token_hash,
            refresh_token_hash=refresh_token_hash,
            expires_at=expires_at,
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
            .options(
                selectinload(UserSession.user).selectinload(User.primary_email),
                selectinload(UserSession.user).selectinload(User.emails),
                selectinload(UserSession.user).selectinload(User.role_assignments).selectinload(RoleAssignment.role),
                selectinload(UserSession.user).selectinload(User.memberships).selectinload(ResidentMembership.community)
            )
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
            .options(
                selectinload(UserSession.user).selectinload(User.primary_email),
                selectinload(UserSession.user).selectinload(User.emails),
                selectinload(UserSession.user).selectinload(User.role_assignments).selectinload(RoleAssignment.role),
                selectinload(UserSession.user).selectinload(User.memberships).selectinload(ResidentMembership.community)
            )
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

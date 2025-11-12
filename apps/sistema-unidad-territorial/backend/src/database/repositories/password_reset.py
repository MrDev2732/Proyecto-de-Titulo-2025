"""
Repository para gestión de tokens de recuperación de contraseñas.
Solo contiene queries a la base de datos.
"""

from datetime import timedelta
from typing import Optional, List
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import and_, or_, select
from sqlalchemy.orm import selectinload

from src.core.logging import get_logger
from src.database.models.auth import User, UserEmail
from src.database.models.system import PasswordResetToken, Outbox
from src.database.utils import now_chile


logger = get_logger(__name__)


class PasswordResetRepository:
    """Repository para queries de tokens de recuperación de contraseñas."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def find_user_by_email(self, email: str) -> Optional[User]:
        """
        Buscar usuario por email.

        Args:
            email: Email del usuario

        Returns:
            Usuario encontrado o None
        """
        email_result = await self.db.execute(
            select(UserEmail).where(UserEmail.email.ilike(email))
        )
        user_email = email_result.scalar_one_or_none()

        user = None
        if user_email:
            # Luego buscar el usuario usando el primary_email_id
            # Cargar explícitamente la relación primary_email para evitar lazy loading
            user_result = await self.db.execute(
                select(User)
                .options(selectinload(User.primary_email))
                .where(
                    and_(
                        User.primary_email_id == user_email.id,
                        User.deleted_at.is_(None)  # Usuario no eliminado
                    )
                )
            )
            user = user_result.scalar_one_or_none()

        return user

    async def get_user_email(self, user: User) -> Optional[str]:
        """
        Obtener email del usuario desde la base de datos.

        Args:
            user: Usuario

        Returns:
            Email del usuario o None
        """
        if not user.primary_email_id:
            return None

        email_result = await self.db.execute(
            select(UserEmail.email).where(UserEmail.id == user.primary_email_id)
        )
        return email_result.scalar_one_or_none()

    async def invalidate_existing_tokens(self, user_id: UUID) -> None:
        """
        Invalidar todos los tokens de reset existentes para un usuario.

        Args:
            user_id: ID del usuario
        """
        # Obtener todos los tokens activos del usuario (no consumidos y no expirados)
        result = await self.db.execute(
            select(PasswordResetToken).where(
                and_(
                    PasswordResetToken.user_id == user_id,
                    PasswordResetToken.consumed_at.is_(None),
                    PasswordResetToken.expires_at > now_chile()
                )
            )
        )

        existing_tokens = result.scalars().all()

        # Marcar cada token como consumido
        for token in existing_tokens:
            token.mark_as_consumed()

        logger.info(f"🗑️ Invalidated {len(existing_tokens)} existing reset tokens for user {user_id}")

    async def create_reset_token(
        self, 
        user_id: UUID, 
        expires_in_minutes: int = 15,
        user_agent: Optional[str] = None
    ) -> PasswordResetToken:
        """
        Crear nuevo token de reset.

        Args:
            user_id: ID del usuario
            expires_in_minutes: Minutos hasta expiración
            user_agent: User agent del cliente

        Returns:
            Token creado
        """
        reset_token = PasswordResetToken.create_for_user(
            user_id=user_id,
            expires_in_minutes=expires_in_minutes,
            user_agent=user_agent
        )

        self.db.add(reset_token)
        await self.db.flush()

        return reset_token

    async def create_outbox_message(self, message_type: str, payload: dict) -> Outbox:
        """
        Crear mensaje en outbox.

        Args:
            message_type: Tipo de mensaje (email, webhook, etc.)
            payload: Datos del mensaje

        Returns:
            Mensaje de outbox creado
        """
        outbox_message = Outbox(
            type=message_type,
            payload=payload
        )

        self.db.add(outbox_message)
        return outbox_message

    async def find_reset_token_by_code_and_email(
        self, 
        code: str, 
        email: str
    ) -> Optional[PasswordResetToken]:
        """
        Buscar token de reset por código y email.

        Args:
            code: Código de reset
            email: Email del usuario

        Returns:
            Token encontrado o None
        """
        email_result = await self.db.execute(
            select(UserEmail).where(UserEmail.email.ilike(email))
        )
        user_email = email_result.scalar_one_or_none()

        reset_token = None
        if user_email:
            # Luego buscar el token usando el user_id
            # Cargar explícitamente la relación primary_email del usuario
            result = await self.db.execute(
                select(PasswordResetToken)
                .join(User)
                .options(selectinload(PasswordResetToken.user).selectinload(User.primary_email))
                .where(
                    and_(
                        PasswordResetToken.code == code,
                        User.primary_email_id == user_email.id,
                        User.deleted_at.is_(None),
                        PasswordResetToken.consumed_at.is_(None),
                        PasswordResetToken.expires_at > now_chile()
                    )
                )
            )
            reset_token = result.scalar_one_or_none()
        else:
            reset_token = None
            
        return reset_token

    async def update_token_as_used(self, token: PasswordResetToken) -> None:
        """
        Actualizar token como usado en la base de datos.

        Args:
            token: Token a actualizar
        """
        token.mark_as_consumed()

    async def update_user_password_hash(self, user: User, password_hash: str) -> None:
        """
        Actualizar hash de contraseña del usuario.

        Args:
            user: Usuario
            password_hash: Hash de la contraseña
        """
        user.password_hash = password_hash

    async def find_expired_tokens(self, older_than_hours: int = 24) -> List[PasswordResetToken]:
        """
        Buscar tokens de reset expirados.

        Args:
            older_than_hours: Buscar tokens más antiguos que estas horas

        Returns:
            Lista de tokens expirados
        """
        cutoff_time = now_chile() - timedelta(hours=older_than_hours)

        result = await self.db.execute(
            select(PasswordResetToken).where(
                or_(
                    PasswordResetToken.expires_at < now_chile(),  # Expirados
                    PasswordResetToken.created_at < cutoff_time   # Muy antiguos
                )
            )
        )

        return result.scalars().all()

    async def delete_token(self, token: PasswordResetToken) -> None:
        """
        Eliminar token de la base de datos.

        Args:
            token: Token a eliminar
        """
        await self.db.delete(token)

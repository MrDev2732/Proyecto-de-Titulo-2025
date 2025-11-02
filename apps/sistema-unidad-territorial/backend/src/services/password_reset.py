"""
Servicio de negocio para recuperación de contraseñas.
"""

from typing import Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.logging import get_logger
from src.core.security import get_password_hash
from src.database.enums import UserStatus
from src.database.repositories.password_reset import PasswordResetRepository
from src.services.email import EmailService
from src.schemas import (
    PasswordResetRequest,
    PasswordResetResponse,
    PasswordResetCodeValidationRequest,
    PasswordResetCodeValidationResponse,
    PasswordResetConfirmationRequest,
    PasswordResetConfirmationResponse
)

logger = get_logger(__name__)


class PasswordResetService:
    """Servicio de negocio para recuperación de contraseñas."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repository = PasswordResetRepository(db)

    async def request_password_reset(
        self,
        request: PasswordResetRequest,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> PasswordResetResponse:
        """
        Solicitar recuperación de contraseña.

        Args:
            request: Datos de la solicitud
            user_agent: User agent del cliente

        Returns:
            Respuesta con información del token generado
            
        Raises:
            ValueError: Si el usuario no existe o está inactivo
        """
        try:
            # Debug: Log del email recibido
            logger.info(f"🔍 Searching for user with email: '{request.email}'")

            # Buscar usuario por email
            user = await self.repository.find_user_by_email(request.email)

            # Debug: Log adicional
            if user:
                logger.info(f"✅ User found: {user.id}, email: '{user.email}', status: '{user.status}'")
            else:
                logger.warning(f"❌ No user found with email: '{request.email}'")

            if not user:
                # Por seguridad, no revelamos si el email existe o no
                logger.warning(f"Password reset requested for non-existent email: {request.email}")
                # Retornamos una respuesta genérica para evitar enumeration attacks
                fake_token_id = UUID('00000000-0000-0000-0000-000000000000')
                return PasswordResetResponse(
                    message="Si el email existe en nuestro sistema, recibirás un código de recuperación.",
                    reset_token_id=fake_token_id,
                    expires_in_minutes=15
                )

            # Verificar que el usuario esté activo
            if user.status != UserStatus.ACTIVE:
                logger.warning(f"Password reset requested for inactive user: {user.id}")
                raise ValueError("La cuenta no está activa")

            # Invalidar tokens anteriores del usuario
            await self.repository.invalidate_existing_tokens(user.id)

            # Crear nuevo token de reset
            reset_token = await self.repository.create_reset_token(
                user_id=user.id,
                expires_in_minutes=15,
                ip_address=ip_address,
                user_agent=user_agent
            )

            # Crear mensaje en outbox para envío de email
            email_data = {
                "to": user.email,
                "subject": "Código de recuperación de contraseña",
                "template": "password_reset",
                "context": {
                    "user_name": user.display_name,
                    "reset_code": reset_token.code,
                    "expires_at": reset_token.expires_at.isoformat(),
                    "expires_in_minutes": 15
                }
            }
            
            await self.repository.create_outbox_message(
                message_type="email.password_reset",
                payload=email_data
            )

            # TEMPORAL: Enviar email directamente hasta implementar worker
            await self._send_reset_email_directly(user, reset_token)

            await self.db.commit()

            logger.info(f"✅ Password reset token created for user {user.id}")
            logger.debug(f"   📧 Email: {user.email}")
            logger.debug(f"   🔑 Code: {reset_token.code}")
            logger.debug(f"   ⏰ Expires at: {reset_token.expires_at}")

            return PasswordResetResponse(
                message="Si el email existe en nuestro sistema, recibirás un código de recuperación.",
                reset_token_id=reset_token.id,
                expires_in_minutes=15
            )

        except Exception as e:
            await self.db.rollback()
            logger.error(f"❌ Error requesting password reset: {e}")
            raise

    async def validate_reset_code(
        self,
        request: PasswordResetCodeValidationRequest
    ) -> PasswordResetCodeValidationResponse:
        """
        Validar código de recuperación de contraseña.

        Args:
            request: Datos de validación del código

        Returns:
            Respuesta con información de validación

        Raises:
            ValueError: Si el código es inválido, expirado o ya usado
        """
        try:
            # Buscar token por código y email del usuario
            reset_token = await self.repository.find_reset_token_by_code_and_email(
                request.code, 
                request.email
            )

            if not reset_token:
                logger.warning(f"Invalid reset code attempted: {request.code} for email: {request.email}")
                raise ValueError("Código inválido o expirado")

            logger.info(f"✅ Valid reset code for user {reset_token.user_id}")

            return PasswordResetCodeValidationResponse(
                message="Código válido. Puedes proceder a cambiar tu contraseña.",
                reset_token_id=reset_token.id,
                expires_at=reset_token.expires_at
            )

        except Exception as e:
            logger.error(f"❌ Error validating reset code: {e}")
            raise

    async def confirm_password_reset(
        self,
        request: PasswordResetConfirmationRequest
    ) -> PasswordResetConfirmationResponse:
        """
        Confirmar cambio de contraseña con código de reset.

        Args:
            request: Datos de confirmación

        Returns:
            Respuesta de confirmación

        Raises:
            ValueError: Si el código es inválido o la contraseña no cumple requisitos
        """
        try:
            # Buscar token por código y email
            reset_token = await self.repository.find_reset_token_by_code_and_email(
                request.code,
                request.email
            )

            if not reset_token:
                logger.warning(f"Invalid reset code for confirmation: {request.code} for email: {request.email}")
                raise ValueError("Código inválido o expirado")

            # Obtener usuario
            user = await self.repository.find_user_by_email(request.email)
            if not user:
                logger.error(f"User not found during password reset confirmation: {request.email}")
                raise ValueError("Usuario no encontrado")

            # Actualizar contraseña
            password_hash = get_password_hash(request.new_password)
            await self.repository.update_user_password_hash(user, password_hash)

            # Marcar token como usado
            await self.repository.update_token_as_used(reset_token)

            # Invalidar otros tokens del usuario
            await self.repository.invalidate_existing_tokens(user.id)

            await self.db.commit()

            logger.info(f"✅ Password reset completed for user {user.id}")

            return PasswordResetConfirmationResponse(
                message="Contraseña actualizada exitosamente. Ya puedes iniciar sesión con tu nueva contraseña."
            )

        except Exception as e:
            await self.db.rollback()
            logger.error(f"❌ Error confirming password reset: {e}")
            raise

    async def cleanup_expired_tokens(self, older_than_hours: int = 24) -> int:
        """
        Limpiar tokens de recuperación expirados.

        Args:
            older_than_hours: Eliminar tokens más antiguos que estas horas

        Returns:
            Número de tokens eliminados
        """
        try:
            # Buscar tokens expirados
            expired_tokens = await self.repository.find_expired_tokens(older_than_hours)

            # Eliminar cada token
            for token in expired_tokens:
                await self.repository.delete_token(token)

            deleted_count = len(expired_tokens)
            logger.info(f"🗑️ Cleaned up {deleted_count} expired password reset tokens")

            await self.db.commit()
            return deleted_count
        except Exception as e:
            await self.db.rollback()
            logger.error(f"❌ Error cleaning up expired tokens: {e}")
            raise

    async def _send_reset_email_directly(self, user, reset_token) -> None:
        """
        Enviar email de reset directamente (temporal hasta implementar worker).

        Args:
            user: Usuario
            reset_token: Token de reset
        """
        # Obtener email usando el repository
        user_email = await self.repository.get_user_email(user)
        
        if not user_email:
            logger.error(f"❌ No se pudo obtener email para usuario {user.id}")
            return

        # Usar full_name si está disponible, sino usar el email
        display_name = user.full_name if user.full_name else user_email

        # Crear cuerpo del email
        email_body = f"""
        Hola {display_name},

        Has solicitado recuperar tu contraseña. Usa el siguiente código para continuar:

        Código de recuperación: {reset_token.code}

        Este código expira en 15 minutos ({reset_token.expires_at.strftime('%H:%M:%S')}).

        Si no solicitaste este cambio, puedes ignorar este mensaje.

        Saludos,
        Sistema Unidad Territorial
        """

        try:
            success = await EmailService.send_email(
                to_email=user_email,
                subject="Código de recuperación de contraseña",
                body=email_body.strip(),
                is_html=False
            )

            if success:
                logger.info(f"✅ Password reset email sent directly to {user_email}")
            else:
                logger.error(f"❌ Failed to send password reset email to {user_email}")

        except Exception as e:
            logger.error(f"❌ Error sending password reset email to {user_email}: {e}")

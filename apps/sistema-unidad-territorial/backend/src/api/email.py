"""
Endpoints para testing y configuración de email.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, EmailStr

from src.database.session import get_db_session
from src.core.dependencies import get_current_active_user
from src.database import User
from src.services.email import EmailService
from src.core.config import settings
from src.core.logging import get_logger


logger = get_logger(__name__)

# Router para endpoints de email
router = APIRouter(prefix="/email", tags=["Email"])


class EmailTestRequest(BaseModel):
    """Request para probar envío de email."""
    to_email: EmailStr
    subject: str = "Prueba de Email - Sistema Unidad Territorial"
    message: str = "Este es un mensaje de prueba para verificar la configuración de email."


class EmailTestResponse(BaseModel):
    """Response para prueba de email."""
    success: bool
    message: str
    email_enabled: bool
    email_configured: bool


@router.get(
    "/status",
    response_model=EmailTestResponse,
    summary="Verificar estado de configuración de email",
    description="Verifica si el email está habilitado y configurado correctamente"
)
async def get_email_status(
    current_user: User = Depends(get_current_active_user)
) -> EmailTestResponse:
    """
    Verificar el estado de la configuración de email.

    Retorna información sobre si el email está habilitado y configurado.
    """
    return EmailTestResponse(
        success=True,
        message="Estado de configuración de email obtenido",
        email_enabled=settings.email.enabled,
        email_configured=settings.email.is_configured
    )


@router.post(
    "/test",
    response_model=EmailTestResponse,
    summary="Probar envío de email",
    description="Envía un email de prueba para verificar la configuración SMTP"
)
async def test_email_sending(
    test_request: EmailTestRequest,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_active_user)
) -> EmailTestResponse:
    """
    Probar el envío de email.

    Envía un email de prueba al destinatario especificado para verificar
    que la configuración SMTP está funcionando correctamente.
    """
    if not settings.email.enabled:
        return EmailTestResponse(
            success=False,
            message="El envío de emails está deshabilitado",
            email_enabled=False,
            email_configured=settings.email.is_configured
        )

    if not settings.email.is_configured:
        return EmailTestResponse(
            success=False,
            message="La configuración de email está incompleta",
            email_enabled=settings.email.enabled,
            email_configured=False
        )

    try:
        # Crear cuerpo del email de prueba
        test_body = f"""
        <html>
        <body>
            <h2>✅ Prueba de Email Exitosa</h2>
            <p><strong>Mensaje:</strong> {test_request.message}</p>
            <p><strong>Enviado por:</strong> {current_user.email}</p>
            <p><strong>Fecha:</strong> {logger.handlers[0].formatter.formatTime(logger.makeRecord('test', 20, '', 0, '', (), None)) if logger.handlers else 'N/A'}</p>
            <hr>
            <small>Este es un email de prueba del Sistema Unidad Territorial</small>
        </body>
        </html>
        """

        # Enviar email de prueba
        success = await EmailService.send_email(
            to_email=test_request.to_email,
            subject=test_request.subject,
            body=test_body,
            is_html=True
        )

        if success:
            logger.info(f"✅ Test email sent successfully to {test_request.to_email} by {current_user.email}")
            return EmailTestResponse(
                success=True,
                message=f"Email de prueba enviado exitosamente a {test_request.to_email}",
                email_enabled=True,
                email_configured=True
            )
        else:
            logger.error(f"❌ Failed to send test email to {test_request.to_email}")
            return EmailTestResponse(
                success=False,
                message="Error al enviar el email de prueba",
                email_enabled=True,
                email_configured=True
            )

    except Exception as e:
        logger.error(f"❌ Exception sending test email: {e}")
        return EmailTestResponse(
            success=False,
            message=f"Error interno: {str(e)}",
            email_enabled=settings.email.enabled,
            email_configured=settings.email.is_configured
        )


@router.post(
    "/test-configuration",
    response_model=EmailTestResponse,
    summary="Probar configuración de email (auto-envío)",
    description="Envía un email de prueba a la dirección configurada como remitente"
)
async def test_email_configuration(
    current_user: User = Depends(get_current_active_user)
) -> EmailTestResponse:
    """
    Probar la configuración de email enviando un correo a la dirección remitente.

    Útil para verificar rápidamente que la configuración SMTP funciona.
    """
    if not settings.email.enabled:
        return EmailTestResponse(
            success=False,
            message="El envío de emails está deshabilitado",
            email_enabled=False,
            email_configured=settings.email.is_configured
        )

    if not settings.email.is_configured:
        return EmailTestResponse(
            success=False,
            message="La configuración de email está incompleta",
            email_enabled=settings.email.enabled,
            email_configured=False
        )

    try:
        success = await EmailService.test_email_configuration()

        if success:
            logger.info(f"✅ Email configuration test successful, initiated by {current_user.email}")
            return EmailTestResponse(
                success=True,
                message=f"Configuración de email verificada. Email enviado a {settings.email.from_email}",
                email_enabled=True,
                email_configured=True
            )
        else:
            logger.error(f"❌ Email configuration test failed")
            return EmailTestResponse(
                success=False,
                message="Error en la configuración de email",
                email_enabled=True,
                email_configured=True
            )

    except Exception as e:
        logger.error(f"❌ Exception testing email configuration: {e}")
        return EmailTestResponse(
            success=False,
            message=f"Error interno: {str(e)}",
            email_enabled=settings.email.enabled,
            email_configured=settings.email.is_configured
        )

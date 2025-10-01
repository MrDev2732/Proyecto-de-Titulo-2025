"""
Servicio simplificado para envío de correos electrónicos usando SMTP.
"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Optional, Dict, Any
from datetime import datetime

from src.core.config import settings
from src.core.logging import get_logger
from .templates import EmailTemplates, EmailType


logger = get_logger(__name__)


class EmailService:
    """Servicio simplificado para envío de correos electrónicos."""

    @staticmethod
    def _create_smtp_connection() -> smtplib.SMTP:
        """
        Crear conexión SMTP con Gmail.

        Returns:
            smtplib.SMTP: Conexión SMTP configurada

        Raises:
            Exception: Si no se puede conectar al servidor SMTP
        """
        try:
            # Crear conexión SMTP
            server = smtplib.SMTP(settings.email.smtp_server, settings.email.smtp_port)

            if settings.email.use_tls:
                server.starttls()  # Habilitar TLS

            # Autenticarse
            server.login(settings.email.smtp_username, settings.email.smtp_password)

            logger.debug(f"✅ Conexión SMTP establecida con {settings.email.smtp_server}")
            return server

        except Exception as e:
            logger.error(f"❌ Error conectando a SMTP: {e}")
            raise

    @staticmethod
    async def send_email(
        to_email: str,
        subject: str,
        body: str,
        is_html: bool = False,
        cc: Optional[List[str]] = None,
        bcc: Optional[List[str]] = None
    ) -> bool:
        """
        Enviar un correo electrónico.

        Args:
            to_email: Email del destinatario
            subject: Asunto del correo
            body: Cuerpo del correo
            is_html: Si el cuerpo es HTML
            cc: Lista de emails en copia
            bcc: Lista de emails en copia oculta

        Returns:
            bool: True si se envió correctamente, False si no
        """
        if not settings.email.enabled:
            logger.warning("📧 Envío de emails deshabilitado - email no enviado")
            return False

        if not settings.email.is_configured:
            logger.error("❌ Configuración de email incompleta")
            return False

        try:
            # Crear mensaje
            msg = MIMEMultipart()
            msg['From'] = f"{settings.email.from_name} <{settings.email.from_email}>"
            msg['To'] = to_email
            msg['Subject'] = subject

            if cc:
                msg['Cc'] = ', '.join(cc)

            # Agregar cuerpo del mensaje
            mime_type = 'html' if is_html else 'plain'
            msg.attach(MIMEText(body, mime_type, 'utf-8'))

            # Crear lista de destinatarios
            recipients = [to_email]
            if cc:
                recipients.extend(cc)
            if bcc:
                recipients.extend(bcc)

            # Enviar email
            with EmailService._create_smtp_connection() as server:
                server.send_message(msg, to_addrs=recipients)

            logger.info(f"✅ Email enviado exitosamente a {to_email}")
            logger.debug(f"   📧 Asunto: {subject}")
            return True

        except Exception as e:
            logger.error(f"❌ Error enviando email a {to_email}: {e}")
            return False

    @staticmethod
    async def send_templated_email(
        email_type: EmailType,
        to_email: str,
        **template_data
    ) -> bool:
        """
        Enviar email usando una plantilla predefinida.

        Args:
            email_type: Tipo de email a enviar
            to_email: Email del destinatario
            **template_data: Datos para formatear la plantilla

        Returns:
            bool: True si se envió correctamente, False si no
        """
        try:
            # Obtener contenido formateado de la plantilla
            email_content = EmailTemplates.format_email_content(
                email_type=email_type,
                to_email=to_email,
                **template_data
            )

            # Enviar email
            return await EmailService.send_email(
                to_email=to_email,
                subject=email_content['subject'],
                body=email_content['body'],
                is_html=True
            )

        except ValueError as e:
            logger.error(f"❌ Error en plantilla de email: {e}")
            return False
        except Exception as e:
            logger.error(f"❌ Error enviando email templated a {to_email}: {e}")
            return False

    @staticmethod
    async def send_welcome_email(
        to_email: str,
        full_name: str,
        temporary_password: str,
        community_name: str
    ) -> bool:
        """
        Enviar email de bienvenida con contraseña temporal.

        Args:
            to_email: Email del nuevo usuario
            full_name: Nombre completo del usuario
            temporary_password: Contraseña temporal generada
            community_name: Nombre de la comunidad

        Returns:
            bool: True si se envió correctamente
        """
        return await EmailService.send_templated_email(
            email_type=EmailType.WELCOME,
            to_email=to_email,
            full_name=full_name,
            temporary_password=temporary_password,
            community_name=community_name
        )

    @staticmethod
    async def send_registration_decision_email(
        to_email: str,
        full_name: str,
        community_name: str,
        approved: bool,
        notes: Optional[str] = None
    ) -> bool:
        """
        Enviar email de decisión de registro (aprobado o rechazado).

        Args:
            to_email: Email del usuario
            full_name: Nombre completo del usuario
            community_name: Nombre de la comunidad
            approved: True si fue aprobado, False si fue rechazado
            notes: Notas del moderador

        Returns:
            bool: True si se envió correctamente
        """
        if approved:
            return await EmailService.send_templated_email(
                email_type=EmailType.REGISTRATION_APPROVED,
                to_email=to_email,
                full_name=full_name,
                community_name=community_name,
                moderator_notes=notes
            )
        else:
            return await EmailService.send_templated_email(
                email_type=EmailType.REGISTRATION_REJECTED,
                to_email=to_email,
                full_name=full_name,
                community_name=community_name,
                rejection_reason=notes
            )

    @staticmethod
    async def test_email_configuration() -> bool:
        """
        Probar la configuración de email enviando un correo de prueba.

        Returns:
            bool: True si la configuración funciona
        """
        if not settings.email.is_configured:
            logger.error("❌ Configuración de email incompleta para prueba")
            return False

        return await EmailService.send_templated_email(
            email_type=EmailType.TEST_EMAIL,
            to_email=settings.email.from_email,  # Enviar a sí mismo
            timestamp=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            smtp_server=settings.email.smtp_server,
            smtp_port=settings.email.smtp_port,
            smtp_username=settings.email.smtp_username,
            additional_info=""
        )

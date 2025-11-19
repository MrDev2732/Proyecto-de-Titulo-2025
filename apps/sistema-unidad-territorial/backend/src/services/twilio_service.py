"""
Servicio para enviar mensajes de WhatsApp usando Twilio.
"""

from typing import Optional

from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException

from src.core.config import settings
from src.core.logging import get_logger


logger = get_logger(__name__)


class TwilioService:
    """Servicio para enviar mensajes de WhatsApp mediante Twilio."""

    def __init__(self):
        """Inicializar el cliente de Twilio."""
        self.account_sid = settings.twilio.account_sid
        self.auth_token = settings.twilio.auth_token
        self.whatsapp_from = settings.twilio.whatsapp_from

        # Verificar si el servicio está habilitado
        self.enabled = settings.twilio.enabled and settings.twilio.is_configured

        if self.enabled:
            try:
                self.client = Client(self.account_sid, self.auth_token)
                logger.info("✅ Twilio service initialized successfully")
                logger.info(f"   WhatsApp From: {self.whatsapp_from}")
                logger.info(f"   Account SID: {self.account_sid[:10] if self.account_sid else 'N/A'}...")
            except Exception as e:
                logger.error(f"❌ Error initializing Twilio client: {e}")
                self.enabled = False
        else:
            if not settings.twilio.enabled:
                logger.warning("⚠️ Twilio service disabled - TWILIO_ENABLED=false in .env")
            elif not settings.twilio.is_configured:
                logger.warning("⚠️ Twilio service disabled - missing credentials in .env")
                logger.info("   Required: TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_WHATSAPP_FROM")
                logger.info("   Also set: TWILIO_ENABLED=true")

    async def send_whatsapp_message(
        self,
        to_phone: str,
        message: str,
        media_url: Optional[str] = None
    ) -> bool:
        """
        Enviar un mensaje de WhatsApp.

        Args:
            to_phone: Número de teléfono destino (con código de país, ej: +56912345678)
            message: Contenido del mensaje
            media_url: URL de imagen/video para adjuntar (opcional)

        Returns:
            True si el mensaje se envió exitosamente, False en caso contrario
        """
        if not self.enabled:
            logger.warning("⚠️ Twilio service is disabled - cannot send WhatsApp message")
            return False

        # Asegurar que ambos números tengan el prefijo whatsapp:
        if not to_phone.startswith('whatsapp:'):
            to_phone = f'whatsapp:{to_phone}'

        from_phone = self.whatsapp_from
        if not from_phone.startswith('whatsapp:'):
            from_phone = f'whatsapp:{from_phone}'

        logger.info(f"📤 Preparing to send WhatsApp message:")
        logger.info(f"   From: {from_phone}")
        logger.info(f"   To: {to_phone}")

        try:
            message_params = {
                'from_': from_phone,
                'body': message,
                'to': to_phone
            }

            # Agregar media si se proporciona
            if media_url:
                message_params['media_url'] = [media_url]

            # Enviar el mensaje
            twilio_message = self.client.messages.create(**message_params)

            logger.info(f"💬 WhatsApp message sent successfully")
            logger.info(f"   To: {to_phone}")
            logger.info(f"   SID: {twilio_message.sid}")
            logger.info(f"   Status: {twilio_message.status}")

            return True

        except TwilioRestException as e:
            logger.error(f"❌ Twilio error sending WhatsApp message: {e}")
            logger.error(f"   Error code: {e.code}")
            logger.error(f"   Error message: {e.msg}")
            return False

        except Exception as e:
            logger.error(f"❌ Unexpected error sending WhatsApp message: {e}")
            return False

    async def send_whatsapp_template(
        self,
        to_phone: str,
        template_name: str,
        template_variables: dict
    ) -> bool:
        """
        Enviar un mensaje de WhatsApp usando una plantilla aprobada.

        Args:
            to_phone: Número de teléfono destino
            template_name: Nombre de la plantilla aprobada en Twilio
            template_variables: Variables para la plantilla

        Returns:
            True si el mensaje se envió exitosamente, False en caso contrario
        """
        if not self.enabled:
            logger.warning("⚠️ Twilio service is disabled - cannot send WhatsApp template")
            return False

        # Asegurar que el número tenga el prefijo whatsapp:
        if not to_phone.startswith('whatsapp:'):
            to_phone = f'whatsapp:{to_phone}'

        try:
            # Nota: Para usar plantillas, necesitas tener Content Templates aprobados en Twilio
            # Este es un ejemplo básico
            message = self.client.messages.create(
                from_=self.whatsapp_from,
                to=to_phone,
                content_sid=template_name,
                content_variables=template_variables
            )

            logger.info(f"💬 WhatsApp template message sent successfully")
            logger.info(f"   To: {to_phone}")
            logger.info(f"   Template: {template_name}")
            logger.info(f"   SID: {message.sid}")

            return True

        except TwilioRestException as e:
            logger.error(f"❌ Twilio error sending WhatsApp template: {e}")
            return False

        except Exception as e:
            logger.error(f"❌ Unexpected error sending WhatsApp template: {e}")
            return False

    def is_enabled(self) -> bool:
        """
        Verificar si el servicio de Twilio está habilitado.

        Returns:
            True si el servicio está habilitado, False en caso contrario
        """
        return self.enabled


# Instancia global del servicio de Twilio
twilio_service = TwilioService()

"""
Observador para manejar notificaciones por email y WhatsApp.
"""

from typing import Dict, Callable

from src.events.base import Event, Observer, EventType
from src.services.twilio_service import twilio_service
from src.services.email import EmailService
from src.database.repositories import AuthRepository
from src.database.session import get_db_session
from src.core.logging import get_logger


logger = get_logger(__name__)


class NotificationObserver(Observer):
    """
    Observador que envía notificaciones por email y WhatsApp según las preferencias del usuario.

    Este observador se puede extender fácilmente agregando más tipos de eventos
    y sus respectivos manejadores de mensajes.
    """

    def __init__(self):
        """Inicializar el observador de notificaciones."""
        # Mapeo de tipos de evento a funciones generadoras de mensajes
        self.message_generators: Dict[EventType, Callable[[Event], Dict[str, str]]] = {
            EventType.REGISTRATION_APPROVED: self._generate_registration_approved_message,
            EventType.REGISTRATION_REJECTED: self._generate_registration_rejected_message,
            EventType.USER_REGISTERED_MANUALLY: self._generate_manual_registration_message,
            EventType.RESERVATION_CREATED: self._generate_reservation_created_message,
            EventType.RESERVATION_CONFIRMED: self._generate_reservation_confirmed_message,
            EventType.RESERVATION_CANCELLED: self._generate_reservation_cancelled_message,
            EventType.RESERVATION_EXPIRED: self._generate_reservation_expired_message,
            EventType.PROJECT_SUBMITTED: self._generate_project_submitted_message,
            EventType.PROJECT_APPROVED: self._generate_project_approved_message,
            EventType.PROJECT_REJECTED: self._generate_project_rejected_message,
            EventType.PROJECT_COMPLETED: self._generate_project_completed_message,
            EventType.NEWS_PUBLISHED: self._generate_news_published_message,
            EventType.COMMUNITY_ANNOUNCEMENT: self._generate_community_announcement_message,
        }

    def get_subscribed_events(self) -> list[EventType]:
        """Retorna todos los eventos para los que hay generadores de mensajes."""
        return list(self.message_generators.keys())

    async def update(self, event: Event) -> None:
        """
        Procesar un evento y enviar notificaciones según las preferencias del usuario.

        Args:
            event: El evento a procesar
        """
        logger.info(f"📬 NotificationObserver processing event: {event.event_type}")

        # Obtener el generador de mensajes para este tipo de evento
        message_generator = self.message_generators.get(event.event_type)

        if not message_generator:
            logger.warning(f"⚠️ No message generator found for event type: {event.event_type}")
            return

        # Generar los mensajes
        messages = message_generator(event)

        # Obtener las preferencias del usuario
        async for session in get_db_session():
            try:
                user = await AuthRepository.find_user_by_id(session, event.user_id)

                if not user:
                    logger.warning(f"⚠️ User {event.user_id} not found - cannot send notifications")
                    return

                # Enviar email si está habilitado
                if user.email_notifications_enabled and messages.get('email_subject') and messages.get('email_body'):
                    await self._send_email_notification(
                        to_email=user.email,
                        subject=messages['email_subject'],
                        body=messages['email_body']
                    )

                # Enviar WhatsApp si está habilitado y el usuario tiene teléfono
                if user.whatsapp_notifications_enabled and user.phone_number and messages.get('whatsapp_message'):
                    await self._send_whatsapp_notification(
                        to_phone=user.phone_number,
                        message=messages['whatsapp_message']
                    )

                break  # Salir del async for después de procesar

            except Exception as e:
                logger.error(f"❌ Error processing notification for user {event.user_id}: {e}")

    async def _send_email_notification(self, to_email: str, subject: str, body: str) -> None:
        """
        Enviar una notificación por email.

        Args:
            to_email: Email destino
            subject: Asunto del email
            body: Cuerpo del email
        """
        try:
            success = await EmailService.send_notification_email(
                to_email=to_email,
                subject=subject,
                body=body
            )

            if success:
                logger.info(f"✅ Email notification sent to {to_email}")
            else:
                logger.warning(f"⚠️ Failed to send email notification to {to_email}")

        except Exception as e:
            logger.error(f"❌ Error sending email notification: {e}")

    async def _send_whatsapp_notification(self, to_phone: str, message: str) -> None:
        """
        Enviar una notificación por WhatsApp.

        Args:
            to_phone: Número de teléfono destino
            message: Mensaje a enviar
        """
        try:
            success = await twilio_service.send_whatsapp_message(
                to_phone=to_phone,
                message=message
            )

            if success:
                logger.info(f"✅ WhatsApp notification sent to {to_phone}")
            else:
                logger.warning(f"⚠️ Failed to send WhatsApp notification to {to_phone}")

        except Exception as e:
            logger.error(f"❌ Error sending WhatsApp notification: {e}")

    # ========================================
    # GENERADORES DE MENSAJES POR TIPO DE EVENTO
    # ========================================

    def _generate_registration_approved_message(self, event: Event) -> Dict[str, str]:
        """Generar mensajes para solicitud de registro aprobada."""
        community_name = event.data.get('community_name', 'la comunidad')
        full_name = event.data.get('full_name', 'vecino/a')
        is_new_user = event.data.get('is_new_user', False)
        temporary_password = event.data.get('temporary_password', '')
        moderator_notes = event.data.get('moderator_notes', '')

        # Si es un nuevo usuario, incluir la contraseña temporal
        if is_new_user and temporary_password:
            email_body = f"""
                <h2>¡Tu solicitud ha sido aprobada! 🎉</h2>
                <p>Estimado/a {full_name},</p>
                <p>Tu solicitud de registro en <strong>{community_name}</strong> ha sido aprobada.</p>
                <p><strong>Contraseña temporal:</strong> <code>{temporary_password}</code></p>
                <p>Por favor, <strong>cambia tu contraseña</strong> al iniciar sesión por primera vez por seguridad.</p>
                <p>Ya puedes acceder al sistema y disfrutar de todos los servicios de la comunidad.</p>
                {f"<p><em>Nota del moderador: {moderator_notes}</em></p>" if moderator_notes else ""}
                <p>¡Bienvenido/a!</p>
            """
            whatsapp_message = f"""🎉 ¡Solicitud aprobada!

Hola {full_name},

Tu solicitud de registro en *{community_name}* ha sido aprobada.

🔑 *Contraseña temporal:* {temporary_password}

⚠️ Por favor, cambia tu contraseña al iniciar sesión.

Ya puedes acceder al sistema. ¡Bienvenido/a! 🏘️"""
        else:
            # Usuario existente - no incluir contraseña
            email_body = f"""
                <h2>¡Tu solicitud ha sido aprobada! 🎉</h2>
                <p>Estimado/a {full_name},</p>
                <p>Tu solicitud de registro en <strong>{community_name}</strong> ha sido aprobada.</p>
                <p>Ya puedes acceder al sistema y disfrutar de todos los servicios de la comunidad.</p>
                {f"<p><em>Nota del moderador: {moderator_notes}</em></p>" if moderator_notes else ""}
                <p>¡Bienvenido/a!</p>
            """
            whatsapp_message = f"""🎉 ¡Solicitud aprobada!

Hola {full_name},

Tu solicitud de registro en *{community_name}* ha sido aprobada.

Ya puedes acceder al sistema. ¡Bienvenido/a! 🏘️"""

        return {
            'email_subject': f'✅ Solicitud aprobada - Bienvenido a {community_name}',
            'email_body': email_body,
            'whatsapp_message': whatsapp_message
        }

    def _generate_registration_rejected_message(self, event: Event) -> Dict[str, str]:
        """Generar mensajes para solicitud de registro rechazada."""
        community_name = event.data.get('community_name', 'la comunidad')
        full_name = event.data.get('full_name', 'vecino/a')
        rejection_reason = event.data.get('rejection_reason', 'No se especificó una razón')

        return {
            'email_subject': f'❌ Solicitud de registro - {community_name}',
            'email_body': f"""
                <h2>Solicitud de registro</h2>
                <p>Estimado/a {full_name},</p>
                <p>Lamentamos informarte que tu solicitud de registro en <strong>{community_name}</strong> no pudo ser aprobada.</p>
                <p><strong>Motivo:</strong> {rejection_reason}</p>
                <p>Si tienes dudas, por favor contacta con la administración de la comunidad.</p>
            """,
            'whatsapp_message': f"""❌ Solicitud rechazada

Hola {full_name},

Tu solicitud de registro en *{community_name}* no pudo ser aprobada.

Motivo: {rejection_reason}

Para más información, contacta con la administración."""
        }

    def _generate_manual_registration_message(self, event: Event) -> Dict[str, str]:
        """Generar mensajes para registro manual por moderador."""
        community_name = event.data.get('community_name', 'la comunidad')
        full_name = event.data.get('full_name', 'vecino/a')
        temporary_password = event.data.get('temporary_password', '')
        notes = event.data.get('notes', '')

        return {
            'email_subject': f'🎉 Bienvenido/a a {community_name}',
            'email_body': f"""
                <h2>¡Bienvenido/a! 🎉</h2>
                <p>Estimado/a {full_name},</p>
                <p>Has sido registrado/a en <strong>{community_name}</strong> por un moderador de la comunidad.</p>
                <p><strong>Contraseña temporal:</strong> <code>{temporary_password}</code></p>
                <p>Por favor, <strong>cambia tu contraseña</strong> al iniciar sesión por primera vez por seguridad.</p>
                {f"<p><em>Nota del moderador: {notes}</em></p>" if notes else ""}
                <p>Ya puedes acceder al sistema y disfrutar de todos los servicios de la comunidad.</p>
                <p>¡Bienvenido/a!</p>
            """,
            'whatsapp_message': f"""🎉 ¡Bienvenido/a!

Hola {full_name},

Has sido registrado/a en *{community_name}*.

🔑 *Contraseña temporal:* {temporary_password}

⚠️ Por favor, cambia tu contraseña al iniciar sesión por primera vez.

Ya puedes acceder al sistema. ¡Bienvenido/a! 🏘️"""
        }

    def _generate_reservation_created_message(self, event: Event) -> Dict[str, str]:
        """Generar mensajes para reserva creada."""
        space_name = event.data.get('space_name', 'el espacio')
        start_time = event.data.get('start_time', '')
        end_time = event.data.get('end_time', '')

        return {
            'email_subject': f'Reserva pendiente - {space_name}',
            'email_body': f"""
                <h2>Reserva creada ⏰</h2>
                <p>Tu reserva de <strong>{space_name}</strong> ha sido creada.</p>
                <p><strong>Inicio:</strong> {start_time}</p>
                <p><strong>Fin:</strong> {end_time}</p>
                <p><strong>Estado:</strong> Pendiente de confirmación</p>
            """,
            'whatsapp_message': f"""⏰ Reserva creada

Espacio: *{space_name}*
Inicio: {start_time}
Fin: {end_time}
Estado: Pendiente de confirmación"""
        }

    def _generate_reservation_confirmed_message(self, event: Event) -> Dict[str, str]:
        """Generar mensajes para reserva confirmada."""
        space_name = event.data.get('space_name', 'el espacio')
        start_time = event.data.get('start_time', '')

        return {
            'email_subject': f'✅ Reserva confirmada - {space_name}',
            'email_body': f"""
                <h2>¡Reserva confirmada! ✅</h2>
                <p>Tu reserva de <strong>{space_name}</strong> ha sido confirmada.</p>
                <p><strong>Fecha y hora:</strong> {start_time}</p>
                <p>¡Te esperamos!</p>
            """,
            'whatsapp_message': f"""✅ ¡Reserva confirmada!

Espacio: *{space_name}*
Fecha: {start_time}

¡Te esperamos! 😊"""
        }

    def _generate_reservation_cancelled_message(self, event: Event) -> Dict[str, str]:
        """Generar mensajes para reserva cancelada."""
        space_name = event.data.get('space_name', 'el espacio')

        return {
            'email_subject': f'Reserva cancelada - {space_name}',
            'email_body': f"""
                <h2>Reserva cancelada</h2>
                <p>Tu reserva de <strong>{space_name}</strong> ha sido cancelada.</p>
            """,
            'whatsapp_message': f"""❌ Reserva cancelada

Tu reserva de *{space_name}* ha sido cancelada."""
        }

    def _generate_reservation_expired_message(self, event: Event) -> Dict[str, str]:
        """Generar mensajes para reserva expirada."""
        space_name = event.data.get('space_name', 'el espacio')

        return {
            'email_subject': f'Reserva expirada - {space_name}',
            'email_body': f"""
                <h2>Reserva expirada ⏱️</h2>
                <p>Tu reserva de <strong>{space_name}</strong> ha expirado por falta de confirmación.</p>
                <p>Puedes crear una nueva reserva cuando lo desees.</p>
            """,
            'whatsapp_message': f"""⏱️ Reserva expirada

Tu reserva de *{space_name}* expiró por falta de confirmación.

Puedes crear una nueva reserva cuando quieras."""
        }

    def _generate_project_submitted_message(self, event: Event) -> Dict[str, str]:
        """Generar mensajes para proyecto enviado."""
        project_title = event.data.get('project_title', 'tu proyecto')

        return {
            'email_subject': f'Proyecto enviado - {project_title}',
            'email_body': f"""
                <h2>Proyecto enviado 📋</h2>
                <p>Tu propuesta de proyecto <strong>{project_title}</strong> ha sido enviada.</p>
                <p>Será revisada por los moderadores de la comunidad.</p>
                <p>Te notificaremos cuando haya una decisión.</p>
            """,
            'whatsapp_message': f"""📋 Proyecto enviado

Tu propuesta "*{project_title}*" ha sido enviada.

Será revisada por los moderadores. Te notificaremos pronto."""
        }

    def _generate_project_approved_message(self, event: Event) -> Dict[str, str]:
        """Generar mensajes para proyecto aprobado."""
        project_title = event.data.get('project_title', 'tu proyecto')

        return {
            'email_subject': f'✅ Proyecto aprobado - {project_title}',
            'email_body': f"""
                <h2>¡Proyecto aprobado! 🎉</h2>
                <p>Tu proyecto <strong>{project_title}</strong> ha sido aprobado.</p>
                <p>¡Felicitaciones! Ahora puedes comenzar a trabajar en él.</p>
            """,
            'whatsapp_message': f"""🎉 ¡Proyecto aprobado!

Tu proyecto "*{project_title}*" ha sido aprobado.

¡Felicitaciones! Ya puedes comenzar a trabajar en él."""
        }

    def _generate_project_rejected_message(self, event: Event) -> Dict[str, str]:
        """Generar mensajes para proyecto rechazado."""
        project_title = event.data.get('project_title', 'tu proyecto')
        reason = event.data.get('reason', 'No se especificó una razón')

        return {
            'email_subject': f'Proyecto - {project_title}',
            'email_body': f"""
                <h2>Proyecto revisado</h2>
                <p>Tu proyecto <strong>{project_title}</strong> ha sido revisado.</p>
                <p><strong>Comentarios:</strong> {reason}</p>
                <p>Puedes realizar ajustes y enviar una nueva propuesta.</p>
            """,
            'whatsapp_message': f"""Proyecto revisado

Tu proyecto "*{project_title}*" ha sido revisado.

Comentarios: {reason}

Puedes ajustarlo y enviar una nueva propuesta."""
        }

    def _generate_project_completed_message(self, event: Event) -> Dict[str, str]:
        """Generar mensajes para proyecto completado."""
        project_title = event.data.get('project_title', 'tu proyecto')

        return {
            'email_subject': f'✅ Proyecto completado - {project_title}',
            'email_body': f"""
                <h2>¡Proyecto completado! ✅</h2>
                <p>Tu proyecto <strong>{project_title}</strong> ha sido marcado como completado.</p>
                <p>¡Gracias por tu contribución a la comunidad!</p>
            """,
            'whatsapp_message': f"""✅ ¡Proyecto completado!

Tu proyecto "*{project_title}*" ha sido completado.

¡Gracias por tu contribución a la comunidad! 🏘️"""
        }

    def _generate_news_published_message(self, event: Event) -> Dict[str, str]:
        """Generar mensajes para noticia publicada."""
        news_title = event.data.get('news_title', 'Nueva noticia')
        news_body = event.data.get('news_body', '')

        return {
            'email_subject': f'📰 {news_title}',
            'email_body': f"""
                <h2>📰 {news_title}</h2>
                <p>{news_body}</p>
            """,
            'whatsapp_message': f"""📰 {news_title}

{news_body[:200]}{'...' if len(news_body) > 200 else ''}"""
        }

    def _generate_community_announcement_message(self, event: Event) -> Dict[str, str]:
        """Generar mensajes para anuncio comunitario."""
        title = event.data.get('title', 'Anuncio importante')
        message = event.data.get('message', '')

        return {
            'email_subject': f'📢 {title}',
            'email_body': f"""
                <h2>📢 {title}</h2>
                <p>{message}</p>
            """,
            'whatsapp_message': f"""📢 {title}

{message}"""
        }


# Instancia global del observador de notificaciones
notification_observer = NotificationObserver()

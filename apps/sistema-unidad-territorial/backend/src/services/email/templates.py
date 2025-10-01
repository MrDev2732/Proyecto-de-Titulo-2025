"""
Plantillas y constantes para emails del sistema.
"""

from enum import Enum
from typing import Dict, Any


class EmailType(Enum):
    """Tipos de emails del sistema."""
    WELCOME = "welcome"
    REGISTRATION_APPROVED = "registration_approved"
    REGISTRATION_REJECTED = "registration_rejected"
    TEST_EMAIL = "test_email"


class EmailTemplates:
    """Plantillas de emails del sistema."""

    @staticmethod
    def get_template(email_type: EmailType) -> Dict[str, str]:
        """
        Obtener plantilla de email por tipo.

        Args:
            email_type: Tipo de email

        Returns:
            Dict con 'subject' y 'body' de la plantilla
        """
        templates = {
            EmailType.WELCOME: {
                "subject": "Bienvenido al Sistema - {community_name}",
                "body": """
                <html>
                <body>
                    <h2>¡Bienvenido al Sistema Unidad Territorial!</h2>

                    <p>Estimado/a <strong>{full_name}</strong>,</p>

                    <p>Su registro en la comunidad <strong>{community_name}</strong> ha sido aprobado exitosamente.</p>

                    <h3>Datos de acceso:</h3>
                    <ul>
                        <li><strong>Email:</strong> {to_email}</li>
                        <li><strong>Contraseña temporal:</strong> <code>{temporary_password}</code></li>
                    </ul>

                    <p><strong>⚠️ Importante:</strong></p>
                    <ul>
                        <li>Esta es una contraseña temporal generada automáticamente</li>
                        <li>Por seguridad, le recomendamos cambiarla en su primer inicio de sesión</li>
                        <li>Mantenga esta información segura y no la comparta</li>
                    </ul>

                    <p>Puede acceder al sistema usando sus credenciales.</p>

                    <p>Si tiene alguna pregunta, no dude en contactar a los moderadores de su comunidad.</p>

                    <br>
                    <p>Saludos cordiales,<br>
                    <strong>Equipo Sistema Unidad Territorial</strong></p>

                    <hr>
                    <small>Este es un mensaje automático, por favor no responda a este correo.</small>
                </body>
                </html>
                """
            },

            EmailType.REGISTRATION_APPROVED: {
                "subject": "Registro Aprobado - {community_name}",
                "body": """
                <html>
                <body>
                    <h2>¡Su registro ha sido aprobado!</h2>

                    <p>Estimado/a <strong>{full_name}</strong>,</p>

                    <p>Nos complace informarle que su solicitud de registro en la comunidad 
                    <strong>{community_name}</strong> ha sido <strong>aprobada</strong>.</p>

                    {notes_section}

                    <p>Ya puede acceder al sistema con sus credenciales habituales.</p>

                    <p>¡Bienvenido/a a nuestra comunidad!</p>

                    <br>
                    <p>Saludos cordiales,<br>
                    <strong>Moderadores de {community_name}</strong></p>

                    <hr>
                    <small>Este es un mensaje automático, por favor no responda a este correo.</small>
                </body>
                </html>
                """
            },

            EmailType.REGISTRATION_REJECTED: {
                "subject": "Solicitud de Registro - {community_name}",
                "body": """
                <html>
                <body>
                    <h2>Solicitud de Registro</h2>

                    <p>Estimado/a <strong>{full_name}</strong>,</p>

                    <p>Lamentamos informarle que su solicitud de registro en la comunidad 
                    <strong>{community_name}</strong> no ha sido aprobada en esta ocasión.</p>

                    {reason_section}

                    <p>Si considera que esto es un error o desea más información, 
                    puede contactar a los moderadores de la comunidad.</p>

                    <p>Agradecemos su interés en formar parte de nuestra comunidad.</p>

                    <br>
                    <p>Saludos cordiales,<br>
                    <strong>Moderadores de {community_name}</strong></p>

                    <hr>
                    <small>Este es un mensaje automático, por favor no responda a este correo.</small>
                </body>
                </html>
                """
            },

            EmailType.TEST_EMAIL: {
                "subject": "Prueba de Configuración - Sistema Unidad Territorial",
                "body": """
                <html>
                <body>
                    <h2>✅ Configuración de Email Exitosa</h2>
                    <p>Este es un correo de prueba para verificar que la configuración SMTP está funcionando correctamente.</p>
                    <p><strong>Fecha:</strong> {timestamp}</p>
                    <p><strong>Servidor:</strong> {smtp_server}:{smtp_port}</p>
                    <p><strong>Usuario:</strong> {smtp_username}</p>
                    {additional_info}
                </body>
                </html>
                """
            }
        }

        return templates.get(email_type, {})

    @staticmethod
    def format_email_content(email_type: EmailType, **kwargs) -> Dict[str, str]:
        """
        Formatear contenido de email con los datos proporcionados.

        Args:
            email_type: Tipo de email
            **kwargs: Datos para formatear la plantilla

        Returns:
            Dict con 'subject' y 'body' formateados
        """
        template = EmailTemplates.get_template(email_type)

        if not template:
            raise ValueError(f"Plantilla no encontrada para tipo: {email_type}")

        # Procesar secciones especiales según el tipo
        if email_type == EmailType.REGISTRATION_APPROVED:
            notes_section = ""
            if kwargs.get('moderator_notes'):
                notes_section = f"""
                <h3>Notas del moderador:</h3>
                <p><em>{kwargs['moderator_notes']}</em></p>
                """
            kwargs['notes_section'] = notes_section

        elif email_type == EmailType.REGISTRATION_REJECTED:
            reason_section = ""
            if kwargs.get('rejection_reason'):
                reason_section = f"""
                <h3>Motivo:</h3>
                <p><em>{kwargs['rejection_reason']}</em></p>
                """
            kwargs['reason_section'] = reason_section

        # Formatear plantilla
        try:
            formatted_subject = template['subject'].format(**kwargs)
            formatted_body = template['body'].format(**kwargs)

            return {
                'subject': formatted_subject,
                'body': formatted_body
            }
        except KeyError as e:
            raise ValueError(f"Falta parámetro requerido para plantilla {email_type}: {e}")


# Constantes para facilitar el uso
WELCOME_EMAIL = EmailType.WELCOME
REGISTRATION_APPROVED_EMAIL = EmailType.REGISTRATION_APPROVED
REGISTRATION_REJECTED_EMAIL = EmailType.REGISTRATION_REJECTED
TEST_EMAIL = EmailType.TEST_EMAIL

from enum import Enum


class NotificationStatus(str, Enum):
    """Notification delivery status enumeration."""

    SENT = "SENT"
    FAILED = "FAILED"


class NotificationType(str, Enum):
    """Notification type enumeration."""

    EMAIL = "email"
    WHATSAPP = "whatsapp"
    WEBHOOK = "webhook"
    SMS = "sms"

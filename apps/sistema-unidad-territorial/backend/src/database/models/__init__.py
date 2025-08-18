from src.database.models.base import BaseModel, TenantBaseModel, UUIDMixin, TimestampMixin, TenantMixin
from src.database.models.auth import User, Role, AuthMagicLink, UserOauthIdentity, UserSession, user_roles_table
from src.database.models.residents import Resident, AddressEvidence
from src.database.models.certificates import Certificate
from src.database.models.spaces import Space, Reservation
from src.database.models.projects import Project, ProjectAttachment
from src.database.models.news import News
from src.database.models.system import Tenant, Outbox, NotificationLog, AuditLog


__all__ = [
    # Base
    "BaseModel",
    "TenantBaseModel", 
    "UUIDMixin",
    "TimestampMixin",
    "TenantMixin",

    # Auth
    "User",
    "Role",
    "AuthMagicLink",
    "UserOauthIdentity",
    "UserSession",
    "user_roles_table",

    # Residents
    "Resident",
    "AddressEvidence",

    # Certificates
    "Certificate",

    # Spaces
    "Space",
    "Reservation",

    # Projects
    "Project",
    "ProjectAttachment",

    # News
    "News",

    # System
    "Tenant",
    "Outbox",
    "NotificationLog",
    "AuditLog",
]

from src.database.models.base import (
    BaseModel,
    TenantBaseModel,
    UUIDMixin,
    TimestampMixin,
    TenantMixin,
)
from src.database.models.auth import (
    User,
    Role,
    AuthMagicLink,
    UserOauthIdentity,
    UserSession,
    AuthenticationLog,
    RoleAssignment,
)
from src.database.models.residents import Resident, AddressEvidence
from src.database.models.certificates import Certificate
from src.database.models.spaces import Space, Reservation
from src.database.models.projects import Project, ProjectAttachment
from src.database.models.news import News
from src.database.models.system import Tenant, Outbox, NotificationLog, AuditLog
from src.database.models.community import (
    Community,
    ResidentMembership,
    RegistrationRequest,
    RegistrationRequestAttachment,
)


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
    "AuthenticationLog",
    "RoleAssignment",

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

    # Community
    "Community",
    "ResidentMembership",
    "RegistrationRequest",
    "RegistrationRequestAttachment",
]

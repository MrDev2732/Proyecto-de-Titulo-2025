from src.database.models.base import (
    BaseModel,
    SoftDeleteBaseModel,
    TenantBaseModel,
    TenantSoftDeleteModel,
    UUIDMixin,
    TimestampMixin,
    TenantMixin,
    SoftDeleteMixin,
)
from src.database.models.auth import (
    User,
    UserEmail,
    Role,
    UserOauthIdentity,
    UserSession,
    AuthenticationLog,
    SystemRoleAssignment,
    TenantRoleAssignment,
    CommunityRoleAssignment,
)
from src.database.models.evidences import AddressEvidence
from src.database.models.certificates import Certificate
from src.database.models.spaces import Space, Reservation
from src.database.models.projects import Project, ProjectAttachment
from src.database.models.news import News
from src.database.models.system import Tenant, Outbox, NotificationLog, AuditLog, PasswordResetToken
from src.database.models.community import (
    Community,
    ResidentMembership,
    RegistrationRequest,
    RegistrationRequestAttachment,
)


__all__ = [
    # Base
    "BaseModel",
    "SoftDeleteBaseModel",
    "TenantBaseModel",
    "TenantSoftDeleteModel",
    "UUIDMixin",
    "TimestampMixin",
    "TenantMixin",
    "SoftDeleteMixin",

    # Auth
    "User",
    "UserEmail",
    "Role",
    "UserOauthIdentity",
    "UserSession",
    "AuthenticationLog",
    "SystemRoleAssignment",
    "TenantRoleAssignment",
    "CommunityRoleAssignment",

    # Evidences
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
    "PasswordResetToken",

    # Community
    "Community",
    "ResidentMembership",
    "RegistrationRequest",
    "RegistrationRequestAttachment",
]

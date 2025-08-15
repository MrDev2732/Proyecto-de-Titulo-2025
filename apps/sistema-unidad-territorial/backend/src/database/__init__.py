from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import MetaData

# Create shared MetaData instance
metadata = MetaData()
Base = declarative_base(metadata=metadata)

SCHEMA = 'sistema_unidad_territorial'

# Import all models to make them available
from src.database.models import *
from src.database.enums import *

from src.database.utils import DatabaseSetup


# Export everything
__all__ = [
    # Base
    "Base",
    "metadata",
    "SCHEMA",

    # Models (imported from models.__init__)
    "BaseModel",
    "TenantBaseModel", 
    "UUIDMixin",
    "TimestampMixin",
    "TenantMixin",
    "User",
    "Role",
    "AuthMagicLink",
    "UserOauthIdentity",
    "user_roles_table",
    "Resident",
    "AddressEvidence",
    "Certificate",
    "Space",
    "Reservation",
    "Project",
    "ProjectAttachment",
    "News",
    "Tenant",
    "Outbox",
    "NotificationLog",
    "AuditLog",

    # Enums (imported from enums.__init__)
    "UserStatus",
    "OAuthProvider",
    "CertificateStatus",
    "EvidenceType",
    "ReservationStatus",
    "ProjectStatus",
    "NotificationStatus",
    "NotificationType",

    # Timezone utilities
    "now_chile",

    # Utilities
    "DatabaseSetup",
]

from enum import Enum


class MembershipStatus(str, Enum):
    """Status for resident memberships in communities."""
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    NEEDS_CHANGES = "NEEDS_CHANGES"


class RegistrationStatus(str, Enum):
    """Status for registration requests."""
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    NEEDS_CHANGES = "NEEDS_CHANGES"


class RegistrationProvider(str, Enum):
    """Authentication providers for registration."""
    LOCAL = "local"
    GOOGLE = "google"
    MAGIC_LINK = "magic_link"


class AttachmentKind(str, Enum):
    """Types of attachments for registration requests."""
    ID_CARD_FRONT = "id_card_front"  # Foto frontal del carnet
    ID_CARD_BACK = "id_card_back"    # Foto trasera del carnet
    UTILITY_BILL = "utility_bill"    # Foto de cuenta (luz, agua, etc.)
    RENT_CONTRACT = "rent_contract"
    OTHER = "other"


class RoleScope(str, Enum):
    """Scope levels for roles."""
    GLOBAL = "GLOBAL"
    TENANT = "TENANT"
    COMMUNITY = "COMMUNITY"
    SYSTEM = "SYSTEM"

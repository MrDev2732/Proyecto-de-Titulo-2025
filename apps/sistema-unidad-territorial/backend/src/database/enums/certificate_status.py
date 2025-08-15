from enum import Enum


class CertificateStatus(str, Enum):
    """Certificate processing status enumeration."""

    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    ISSUED = "ISSUED"


class EvidenceType(str, Enum):
    """Address evidence type enumeration."""

    UTILITY_BILL = "utility_bill"
    RENTAL_CONTRACT = "rental_contract"
    OTHER = "other"

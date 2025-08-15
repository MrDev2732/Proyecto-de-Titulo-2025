
from enum import Enum


class ReservationStatus(str, Enum):
    """Space reservation status enumeration."""

    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    CANCELLED = "CANCELLED"

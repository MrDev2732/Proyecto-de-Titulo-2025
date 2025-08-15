
from enum import Enum


class ProjectStatus(str, Enum):
    """Community project status enumeration."""

    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    REJECTED = "REJECTED"

from enum import Enum


class UserStatus(str, Enum):
    """User account status enumeration."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    BLOCKED = "blocked"


class OAuthProvider(str, Enum):
    """OAuth provider enumeration."""

    GOOGLE = "google"
    # Add more providers as needed
    # FACEBOOK = "facebook"
    # GITHUB = "github"

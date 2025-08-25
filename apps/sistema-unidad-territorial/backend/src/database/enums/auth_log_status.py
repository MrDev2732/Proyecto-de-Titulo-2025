from enum import Enum


class AuthProvider(str, Enum):
    """Authentication provider enum."""
    LOCAL = "local"
    GOOGLE = "google"
    MAGIC_LINK = "magic_link"


class AuthMethod(str, Enum):
    """Authentication method enum."""
    PASSWORD = "password"
    OAUTH = "oauth"
    MAGIC_LINK = "magic_link"


class AuthResult(str, Enum):
    """Authentication result enum."""
    SUCCESS = "SUCCESS"
    FAIL = "FAIL"


class AuthFailureReason(str, Enum):
    """Authentication failure reason enum."""
    INVALID_PASSWORD = "INVALID_PASSWORD"
    INVALID_EMAIL = "INVALID_EMAIL"
    ACCOUNT_SUSPENDED = "ACCOUNT_SUSPENDED"
    EMAIL_NOT_VERIFIED = "EMAIL_NOT_VERIFIED"
    OAUTH_ERROR = "OAUTH_ERROR"
    OAUTH_EMAIL_MISMATCH = "OAUTH_EMAIL_MISMATCH"
    TOKEN_EXPIRED = "TOKEN_EXPIRED"
    TOKEN_INVALID = "TOKEN_INVALID"
    RATE_LIMITED = "RATE_LIMITED"
    ACCOUNT_LOCKED = "ACCOUNT_LOCKED"
    MFA_REQUIRED = "MFA_REQUIRED"
    MFA_INVALID = "MFA_INVALID"
    UNKNOWN_ERROR = "UNKNOWN_ERROR"

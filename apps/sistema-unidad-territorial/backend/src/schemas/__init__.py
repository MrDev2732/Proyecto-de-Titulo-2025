# Esquemas Pydantic para validación de datos

from src.schemas.auth import *
from src.schemas.community import *


__all__ = [
    # Auth schemas
    "LoginRequest",
    "TokenResponse",
    "RefreshTokenRequest", 
    "UserCreateRequest",
    "UserResponse",
    "TokenData",
    "GoogleOAuthRequest",
    "OAuthUserInfo", 
    "ErrorResponse",
    "RoleResponse",
    # Password Reset schemas
    "PasswordResetRequest",
    "PasswordResetResponse",
    "PasswordResetCodeValidationRequest",
    "PasswordResetCodeValidationResponse",
    "PasswordResetConfirmRequest",
    "PasswordResetConfirmResponse",
    "PasswordResetConfirmationRequest",
    "PasswordResetConfirmationResponse",
    "PasswordResetTokenInfo",
    # Community schemas
    "RegistrationRequestResponse"
    "CertificateRequest"
]

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    """Request schema para login con email y contraseña."""
    email: EmailStr = Field(..., description="Email del usuario")
    password: str = Field(..., min_length=8, description="Contraseña del usuario")


class TokenResponse(BaseModel):
    """Response schema para tokens de autenticación."""
    access_token: str = Field(..., description="Token de acceso JWT")
    refresh_token: str = Field(..., description="Token de refresh")
    token_type: str = Field(default="bearer", description="Tipo de token")
    expires_in: int = Field(..., description="Tiempo de expiración en segundos")
    user: "UserResponse" = Field(..., description="Información del usuario autenticado")


class RefreshTokenRequest(BaseModel):
    """Request schema para refresh de token."""
    refresh_token: str = Field(..., description="Token de refresh")


class UserCreateRequest(BaseModel):
    """Request schema para crear un nuevo usuario."""
    email: EmailStr = Field(..., description="Email del usuario")
    password: str = Field(..., min_length=8, description="Contraseña del usuario")
    roles: Optional[List[str]] = Field(default=None, description="Roles del usuario")


class RoleResponse(BaseModel):
    """Response schema para roles."""
    id: UUID = Field(..., description="ID del rol")
    name: str = Field(..., description="Nombre del rol")
    created_at: datetime = Field(..., description="Fecha de creación")

    class Config:
        from_attributes = True


class UserResponse(BaseModel):
    """Response schema para información del usuario."""
    id: UUID = Field(..., description="ID del usuario")
    email: Optional[str] = Field(None, description="Email del usuario")
    email_verified_at: Optional[datetime] = Field(None, description="Fecha de verificación del email")
    status: str = Field(..., description="Estado del usuario")
    roles: List[RoleResponse] = Field(default_factory=list, description="Roles del usuario")
    created_at: datetime = Field(..., description="Fecha de creación")
    updated_at: datetime = Field(..., description="Fecha de última actualización")

    class Config:
        from_attributes = True


class TokenData(BaseModel):
    """Schema para datos decodificados del token."""
    user_id: Optional[str] = None
    email: Optional[str] = None
    roles: List[str] = Field(default_factory=list)
    token_type: str = "access"  # "access" or "refresh"


class GoogleOAuthRequest(BaseModel):
    """Request schema para OAuth con Google."""
    code: str = Field(..., description="Código de autorización de Google")
    state: Optional[str] = Field(None, description="Estado para validación CSRF")


class OAuthUserInfo(BaseModel):
    """Schema para información del usuario de OAuth."""
    provider_user_id: str
    email: str
    provider: str = "google"
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    token_expires_at: Optional[datetime] = None


class ErrorResponse(BaseModel):
    """Response schema para errores."""
    detail: str = Field(..., description="Descripción del error")
    error_code: Optional[str] = Field(None, description="Código de error específico")


# ========================================
# SCHEMAS PARA RECUPERACIÓN DE CONTRASEÑA
# ========================================
class PasswordResetRequest(BaseModel):
    """Request schema para solicitar recuperación de contraseña."""
    email: EmailStr = Field(..., description="Email del usuario que solicita el reset")


class PasswordResetResponse(BaseModel):
    """Response schema para solicitud de recuperación de contraseña."""
    message: str = Field(..., description="Mensaje de confirmación")
    reset_token_id: UUID = Field(..., description="ID del token de reset generado")
    expires_in_minutes: int = Field(..., description="Minutos hasta expiración del código")


class PasswordResetCodeValidationRequest(BaseModel):
    """Request schema para validar código de recuperación."""
    email: EmailStr = Field(..., description="Email del usuario")
    code: str = Field(..., min_length=6, max_length=6, description="Código de 6 dígitos recibido por email")


class PasswordResetCodeValidationResponse(BaseModel):
    """Response schema para validación de código."""
    message: str = Field(..., description="Mensaje de confirmación")
    reset_token_id: UUID = Field(..., description="ID del token de reset")
    expires_at: datetime = Field(..., description="Fecha y hora de expiración del token")


class PasswordResetConfirmRequest(BaseModel):
    """Request schema para confirmar cambio de contraseña."""
    reset_token: str = Field(..., description="Token de reset obtenido tras validar código")
    new_password: str = Field(..., min_length=8, description="Nueva contraseña")
    confirm_password: str = Field(..., min_length=8, description="Confirmación de nueva contraseña")

    def validate_passwords_match(self) -> bool:
        """Validar que las contraseñas coincidan."""
        return self.new_password == self.confirm_password


class PasswordResetConfirmResponse(BaseModel):
    """Response schema para confirmación de cambio de contraseña."""
    message: str = Field(..., description="Mensaje de confirmación")
    user_id: UUID = Field(..., description="ID del usuario que cambió la contraseña")


class PasswordResetConfirmationRequest(BaseModel):
    """Request schema para confirmar cambio de contraseña con código."""
    email: EmailStr = Field(..., description="Email del usuario")
    code: str = Field(..., min_length=6, max_length=6, description="Código de 6 dígitos recibido por email")
    new_password: str = Field(..., min_length=8, description="Nueva contraseña")


class PasswordResetConfirmationResponse(BaseModel):
    """Response schema para confirmación de cambio de contraseña con código."""
    message: str = Field(..., description="Mensaje de confirmación")


# Schema para información del token (uso interno)
class PasswordResetTokenInfo(BaseModel):
    """Schema para información del token de reset."""
    id: UUID = Field(..., description="ID del token")
    user_id: UUID = Field(..., description="ID del usuario")
    code: str = Field(..., description="Código de 6 dígitos")
    token: str = Field(..., description="Token seguro")
    expires_at: datetime = Field(..., description="Fecha de expiración")
    is_used: bool = Field(..., description="Si el token ya fue usado")
    created_at: datetime = Field(..., description="Fecha de creación")

    class Config:
        from_attributes = True

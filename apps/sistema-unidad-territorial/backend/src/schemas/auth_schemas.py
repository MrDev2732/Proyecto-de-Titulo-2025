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

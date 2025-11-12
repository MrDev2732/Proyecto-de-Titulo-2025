from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field

from src.database.enums import (
    MembershipStatus,
    RegistrationStatus,
    RegistrationProvider,
    AttachmentKind
)


class CommunityResponse(BaseModel):
    """Response schema para comunidades."""
    id: UUID = Field(..., description="ID de la comunidad")
    tenant_id: UUID = Field(..., description="ID del tenant (municipalidad)")
    name: str = Field(..., description="Nombre de la comunidad")
    description: Optional[str] = Field(None, description="Descripción de la comunidad")
    created_at: datetime = Field(..., description="Fecha de creación")
    updated_at: datetime = Field(..., description="Fecha de última actualización")

    class Config:
        from_attributes = True


class RegistrationRequestAttachmentCreate(BaseModel):
    """Schema para adjuntos en solicitudes de registro."""
    bucket: str = Field(..., description="Bucket donde se almacena el archivo")
    storage_key: str = Field(..., description="Clave de almacenamiento del archivo")
    sha256: str = Field(..., description="Hash SHA256 del archivo")
    mime_type: str = Field(..., description="Tipo MIME del archivo")
    kind: AttachmentKind = Field(..., description="Tipo de documento")


class RegistrationRequestCreateData(BaseModel):
    """Datos básicos para crear una solicitud de registro (sin archivos)."""
    tenant_id: UUID = Field(..., description="ID del tenant (municipalidad)")
    community_id: UUID = Field(..., description="ID de la comunidad donde registrarse")
    email: EmailStr = Field(..., description="Email del solicitante")
    full_name: str = Field(..., description="Nombre completo del solicitante")
    rut: str = Field(..., description="RUT del solicitante")
    address: str = Field(..., description="Dirección del solicitante")
    provider: RegistrationProvider = Field(default=RegistrationProvider.GOOGLE, description="Proveedor de autenticación")


class RegistrationRequestAttachmentResponse(BaseModel):
    """Response schema para adjuntos de solicitudes de registro."""
    id: UUID = Field(..., description="ID del adjunto")
    bucket: str = Field(..., description="Bucket donde se almacena el archivo")
    storage_key: str = Field(..., description="Clave de almacenamiento del archivo")
    sha256: str = Field(..., description="Hash SHA256 del archivo")
    mime_type: str = Field(..., description="Tipo MIME del archivo")
    kind: AttachmentKind = Field(..., description="Tipo de adjunto")
    created_at: datetime = Field(..., description="Fecha de creación")
    url: str = Field(..., description="URL del archivo (generada desde storage_key)")

    class Config:
        from_attributes = True


class RegistrationRequestResponse(BaseModel):
    """Response schema para solicitudes de registro."""
    id: UUID = Field(..., description="ID de la solicitud")
    tenant_id: UUID = Field(..., description="ID del tenant")
    community_id: UUID = Field(..., description="ID de la comunidad")
    email: str = Field(..., description="Email del solicitante")
    full_name: Optional[str] = Field(None, description="Nombre completo")
    rut: Optional[str] = Field(None, description="RUT del solicitante")
    address: Optional[str] = Field(None, description="Dirección")
    provider: RegistrationProvider = Field(..., description="Proveedor de autenticación")
    status: RegistrationStatus = Field(..., description="Estado de la solicitud")
    decided_by: Optional[UUID] = Field(None, description="ID del moderador que decidió")
    decided_at: Optional[datetime] = Field(None, description="Fecha de decisión")
    decision_notes: Optional[str] = Field(None, description="Notas de la decisión")
    attachments: List[RegistrationRequestAttachmentResponse] = Field(default_factory=list, description="Adjuntos de la solicitud")
    created_at: datetime = Field(..., description="Fecha de creación")
    updated_at: datetime = Field(..., description="Fecha de última actualización")

    class Config:
        from_attributes = True


class RegistrationRequestDecision(BaseModel):
    """Request schema para aprobar/rechazar solicitudes de registro."""
    decision_notes: Optional[str] = Field(None, description="Notas de la decisión del moderador")


class ResidentMembershipResponse(BaseModel):
    """Response schema para membresías de residentes."""
    id: UUID = Field(..., description="ID de la membresía")
    user_id: UUID = Field(..., description="ID del usuario")
    community_id: UUID = Field(..., description="ID de la comunidad")
    status: MembershipStatus = Field(..., description="Estado de la membresía")
    verified: bool = Field(..., description="Si la membresía está verificada")
    verified_at: Optional[datetime] = Field(None, description="Fecha de verificación")
    community: Optional[CommunityResponse] = Field(None, description="Información de la comunidad")
    created_at: datetime = Field(..., description="Fecha de creación")
    updated_at: datetime = Field(..., description="Fecha de última actualización")

    class Config:
        from_attributes = True


class RegistrationRequestListResponse(BaseModel):
    """Response schema para lista de solicitudes de registro."""
    requests: List[RegistrationRequestResponse] = Field(..., description="Lista de solicitudes")
    total: int = Field(..., description="Total de solicitudes")


class TenantResponse(BaseModel):
    """Response schema para tenants."""
    id: UUID = Field(..., description="ID del tenant")
    name: str = Field(..., description="Nombre del tenant (municipalidad)")
    created_at: datetime = Field(..., description="Fecha de creación")

    class Config:
        from_attributes = True


class TenantWithCommunitiesResponse(BaseModel):
    """Response schema para tenant con sus comunidades."""
    tenant: TenantResponse = Field(..., description="Información del tenant")
    communities: List[CommunityResponse] = Field(..., description="Comunidades del tenant")
    total_communities: int = Field(..., description="Total de comunidades")


class TenantsAndCommunitiesResponse(BaseModel):
    """Response schema para estructura completa de tenants y comunidades."""
    tenants: List[TenantWithCommunitiesResponse] = Field(..., description="Lista de tenants con sus comunidades")
    total_tenants: int = Field(..., description="Total de tenants")
    total_communities: int = Field(..., description="Total de comunidades en el sistema")


class TenantListResponse(BaseModel):
    """Response schema para lista de tenants."""
    tenants: List[TenantResponse] = Field(..., description="Lista de tenants")
    total: int = Field(..., description="Total de tenants")


class CommunitiesByTenantResponse(BaseModel):
    """Response schema para comunidades de un tenant específico."""
    tenant: TenantResponse = Field(..., description="Información del tenant")
    communities: List[CommunityResponse] = Field(..., description="Comunidades del tenant")
    total: int = Field(..., description="Total de comunidades")


class ManualRegistrationRequest(BaseModel):
    """Request schema para registro manual de vecinos por moderadores/admins."""
    email: EmailStr = Field(..., description="Email del vecino")
    full_name: str = Field(..., description="Nombre completo del vecino")
    rut: str = Field(..., description="RUT del vecino")
    address: str = Field(..., description="Dirección del vecino")
    notes: Optional[str] = Field(None, description="Notas del moderador sobre el registro")


class ManualRegistrationResponse(BaseModel):
    """Response schema para registro manual de vecinos."""
    user_id: UUID = Field(..., description="ID del usuario creado/encontrado")
    membership_id: UUID = Field(..., description="ID de la membresía creada")
    email: str = Field(..., description="Email del vecino")
    full_name: str = Field(..., description="Nombre completo del vecino")
    rut: str = Field(..., description="RUT del vecino")
    address: str = Field(..., description="Dirección del vecino")
    community: CommunityResponse = Field(..., description="Información de la comunidad")
    registered_by: UUID = Field(..., description="ID del moderador que registró al vecino")
    temporary_password: Optional[str] = Field(None, description="Contraseña temporal generada (solo si es usuario nuevo)")
    created_at: datetime = Field(..., description="Fecha de registro")

    class Config:
        from_attributes = True


class CertificateRequest(BaseModel):
    """Request schema para generar certificado de residencia."""
    save_to_file: bool = Field(default=False, description="Si guardar el certificado en archivo")


class CertificateResponse(BaseModel):
    """Response schema para certificado de residencia generado."""
    certificate_number: str = Field(..., description="Número del certificado")
    issue_date: datetime = Field(..., description="Fecha de emisión")
    resident_name: str = Field(..., description="Nombre del residente")
    resident_rut: str = Field(..., description="RUT del residente")
    community_name: str = Field(..., description="Nombre de la comunidad")
    file_size: int = Field(..., description="Tamaño del archivo en bytes")
    file_path: Optional[str] = Field(None, description="Ruta del archivo guardado (si se guardó)")

    class Config:
        from_attributes = True

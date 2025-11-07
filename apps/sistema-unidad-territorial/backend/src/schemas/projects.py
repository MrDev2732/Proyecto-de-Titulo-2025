"""
Schemas para proyectos vecinales.
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class ProjectAttachmentResponse(BaseModel):
    """Schema de respuesta para un adjunto de proyecto."""
    id: str
    original_filename: Optional[str]
    mime_type: str
    file_url: str
    created_at: datetime

    class Config:
        from_attributes = True


class ProjectCreate(BaseModel):
    """
    Schema para creación de proyecto.
    
    Requiere que el usuario tenga un board_role (miembro de la junta de vecinos).
    El community_id se obtiene automáticamente de las membresías del usuario.
    """
    title: str = Field(..., description="Título del proyecto", min_length=5, max_length=200)
    description: str = Field(..., description="Descripción detallada del proyecto", min_length=20)

    class Config:
        json_schema_extra = {
            "example": {
                "title": "Mejoramiento de áreas verdes",
                "description": "Propuesta para mejorar las áreas verdes del sector norte de la comunidad, incluyendo plantación de árboles nativos y mejora del sistema de riego."
            }
        }


class ProjectUpdate(BaseModel):
    """Schema para actualización de proyecto por parte de administradores."""
    status: Optional[str] = Field(None, description="Estado del proyecto (PENDING, IN_PROGRESS, COMPLETED, REJECTED)")
    observations: Optional[str] = Field(None, description="Observaciones sobre el proyecto")

    class Config:
        json_schema_extra = {
            "example": {
                "status": "IN_PROGRESS",
                "observations": "Proyecto aprobado, se iniciará la licitación en marzo"
            }
        }


class ProjectResponse(BaseModel):
    """Schema de respuesta para un proyecto individual."""
    id: str
    title: str
    description: str
    status: str
    observations: Optional[str]
    community_id: str
    requesting_user_id: str
    created_at: datetime
    updated_at: datetime
    attachments: List[ProjectAttachmentResponse] = Field(default_factory=list, description="Archivos adjuntos del proyecto")

    class Config:
        from_attributes = True


class ProjectListResponse(BaseModel):
    """Schema para respuesta de lista paginada de proyectos."""
    projects: List[ProjectResponse]
    total: int
    page: int
    per_page: int
    total_pages: int


class ProjectApprovalRequest(BaseModel):
    """Schema para aprobar o rechazar un proyecto."""
    status: str = Field(..., description="Estado: IN_PROGRESS (aprobar) o REJECTED (rechazar)")
    observations: Optional[str] = Field(None, description="Observaciones sobre la decisión")

    class Config:
        json_schema_extra = {
            "example": {
                "status": "IN_PROGRESS",
                "observations": "Proyecto aprobado para su implementación en el primer trimestre del año"
            }
        }

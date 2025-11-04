from pydantic import BaseModel, validator, root_validator, Field
from typing import Optional, List
from uuid import UUID
from datetime import datetime

class NewsCreate(BaseModel):
    """Schema para creación de noticia. tenant_id ahora es opcional y puede ser omitido por el cliente."""
    title: str
    body: str
    visible_from: datetime
    visible_until: Optional[datetime] = None
    
    def validate_dates(cls, values):
        visible_from = values.get('visible_from')
        visible_until = values.get('visible_until')
        if (
            visible_from
            and visible_until is not None
            and visible_until <= visible_from
        ):
            raise ValueError(
                "El campo visible_until debe ser posterior a visible_from (o null)"
            )
        return values


class NewsUpdate(BaseModel):
    """Schema para edición de noticia (campos opcionales)."""
    title: Optional[str] = None
    body: Optional[str] = None
    visible_from: Optional[datetime] = None
    visible_until: Optional[datetime] = None
  
    def validate_dates(cls, values):
        visible_from = values.get('visible_from')
        visible_until = values.get('visible_until')
        if (
            visible_from
            and visible_until is not None
            and visible_until <= visible_from
        ):
            raise ValueError(
                "El campo visible_until debe ser posterior a visible_from (o null)"
            )
        return values


class NewsResponse(BaseModel):
    """Schema de respuesta para una noticia individual."""
    id: str
    title: str
    body: str
    visible_from: datetime
    visible_until: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class NewsListResponse(BaseModel):
    """Schema para respuesta de lista paginada de noticias."""
    news: List[NewsResponse]
    total: int
    page: int
    per_page: int
    total_pages: int

"""
Schemas para espacios y reservas.
"""
from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Dict
from uuid import UUID
from datetime import datetime


# ==================== Space Schemas ====================

class SpaceCreate(BaseModel):
    """Schema para creación de espacio."""
    name: str = Field(..., description="Nombre del espacio", min_length=3, max_length=200)
    description: Optional[str] = Field(None, description="Descripción del espacio")
    capacity: Optional[int] = Field(None, description="Capacidad máxima", ge=1)
    requires_approval: bool = Field(True, description="Si requiere aprobación de reservas")
    rules_json: Optional[Dict] = Field(default_factory=dict, description="Reglas y restricciones del espacio")

    @field_validator('capacity')
    @classmethod
    def validate_capacity(cls, v):
        """Validar que la capacidad sea positiva."""
        if v is not None and v < 1:
            raise ValueError('La capacidad debe ser al menos 1')
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "name": "Cancha de Fútbol Principal",
                "description": "Cancha de fútbol techada con pasto sintético",
                "capacity": 22,
                "requires_approval": True,
                "rules_json": {
                    "max_hours_daily": 2,
                    "max_hours_weekly": 4,
                    "min_duration_hours": 1,
                    "max_duration_hours": 3,
                    "advance_days_required": 7
                }
            }
        }


class SpaceUpdate(BaseModel):
    """Schema para actualización de espacio."""
    name: Optional[str] = Field(None, description="Nombre del espacio", min_length=3, max_length=200)
    description: Optional[str] = Field(None, description="Descripción del espacio")
    capacity: Optional[int] = Field(None, description="Capacidad máxima", ge=1)
    requires_approval: Optional[bool] = Field(None, description="Si requiere aprobación de reservas")
    rules_json: Optional[Dict] = Field(None, description="Reglas y restricciones del espacio")

    @field_validator('capacity')
    @classmethod
    def validate_capacity(cls, v):
        """Validar que la capacidad sea positiva."""
        if v is not None and v < 1:
            raise ValueError('La capacidad debe ser al menos 1')
        return v


class SpaceResponse(BaseModel):
    """Schema de respuesta para un espacio individual."""
    id: UUID
    community_id: UUID
    name: str
    description: Optional[str]
    capacity: Optional[int]
    requires_approval: bool
    rules_json: Optional[Dict]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
        # Configuración para serializar UUID como string en JSON
        json_encoders = {
            UUID: str
        }


class SpaceListResponse(BaseModel):
    """Schema para respuesta de lista de espacios."""
    spaces: List[SpaceResponse]
    total: int


# ==================== Reservation Schemas ====================

class ReservationCreate(BaseModel):
    """Schema para creación de reserva."""
    space_id: UUID = Field(..., description="ID del espacio a reservar")
    start_time: datetime = Field(..., description="Hora de inicio de la reserva")
    end_time: datetime = Field(..., description="Hora de fin de la reserva")

    @field_validator('end_time')
    @classmethod
    def validate_end_time(cls, v, info):
        """Validar que end_time sea posterior a start_time."""
        if 'start_time' in info.data and v <= info.data['start_time']:
            raise ValueError('La hora de fin debe ser posterior a la hora de inicio')
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "space_id": "550e8400-e29b-41d4-a716-446655440000",
                "start_time": "2025-11-15T10:00:00-03:00",
                "end_time": "2025-11-15T12:00:00-03:00"
            }
        }


class ReservationUpdate(BaseModel):
    """Schema para actualización de reserva (cancelación)."""
    cancel_reason: Optional[str] = Field(None, description="Razón de cancelación")


class ReservationApprovalRequest(BaseModel):
    """Schema para aprobar o rechazar una reserva."""
    status: str = Field(..., description="Estado: CONFIRMED (aprobar) o CANCELLED (rechazar)")
    cancel_reason: Optional[str] = Field(None, description="Razón de rechazo (si aplica)")

    @field_validator('status')
    @classmethod
    def validate_status(cls, v):
        """Validar que el estado sea válido."""
        if v not in ['CONFIRMED', 'CANCELLED']:
            raise ValueError('El estado debe ser CONFIRMED o CANCELLED')
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "status": "CONFIRMED",
                "cancel_reason": None
            }
        }


class ReservationResponse(BaseModel):
    """Schema de respuesta para una reserva individual."""
    id: UUID
    space_id: UUID
    requesting_user_id: UUID
    start_time: datetime
    end_time: datetime
    status: str
    canceled_at: Optional[datetime]
    cancel_reason: Optional[str]
    created_at: datetime
    updated_at: datetime

    # Información adicional del espacio y usuario (opcional, cargada con relaciones)
    space_name: Optional[str] = None
    user_email: Optional[str] = None

    class Config:
        from_attributes = True
        # Configuración para serializar UUID como string en JSON
        json_encoders = {
            UUID: str
        }


class ReservationListResponse(BaseModel):
    """Schema para respuesta de lista de reservas."""
    reservations: List[ReservationResponse]
    total: int
    page: int
    per_page: int
    total_pages: int


class ReservationCalendarResponse(BaseModel):
    """Schema para respuesta de calendario de reservas."""
    space_id: str
    space_name: str
    reservations: List[ReservationResponse]


class AvailabilityCheckRequest(BaseModel):
    """Schema para verificar disponibilidad de un espacio."""
    space_id: UUID = Field(..., description="ID del espacio")
    start_time: datetime = Field(..., description="Hora de inicio")
    end_time: datetime = Field(..., description="Hora de fin")

    @field_validator('end_time')
    @classmethod
    def validate_end_time(cls, v, info):
        """Validar que end_time sea posterior a start_time."""
        if 'start_time' in info.data and v <= info.data['start_time']:
            raise ValueError('La hora de fin debe ser posterior a la hora de inicio')
        return v


class AvailabilityCheckResponse(BaseModel):
    """Schema de respuesta para verificación de disponibilidad."""
    is_available: bool
    conflicting_reservations: List[ReservationResponse] = Field(default_factory=list)
    message: str

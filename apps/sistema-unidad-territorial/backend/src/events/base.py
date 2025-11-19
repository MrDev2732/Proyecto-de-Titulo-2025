"""
Clases base para el sistema de eventos y observadores.
"""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Dict
from uuid import UUID
from datetime import datetime


class EventType(str, Enum):
    """Tipos de eventos del sistema."""

    # Eventos de registro y aprobación
    REGISTRATION_APPROVED = "registration_approved"
    REGISTRATION_REJECTED = "registration_rejected"
    USER_REGISTERED_MANUALLY = "user_registered_manually"

    # Eventos de reservas
    RESERVATION_CREATED = "reservation_created"
    RESERVATION_CONFIRMED = "reservation_confirmed"
    RESERVATION_CANCELLED = "reservation_cancelled"
    RESERVATION_EXPIRED = "reservation_expired"

    # Eventos de proyectos
    PROJECT_SUBMITTED = "project_submitted"
    PROJECT_APPROVED = "project_approved"
    PROJECT_REJECTED = "project_rejected"
    PROJECT_COMPLETED = "project_completed"

    # Eventos de noticias
    NEWS_PUBLISHED = "news_published"

    # Eventos de comunidad
    COMMUNITY_ANNOUNCEMENT = "community_announcement"


class Event:
    """Clase base para todos los eventos del sistema."""

    def __init__(
        self,
        event_type: EventType,
        user_id: UUID,
        data: Dict[str, Any],
        tenant_id: UUID | None = None,
        community_id: UUID | None = None
    ):
        """
        Inicializar un evento.

        Args:
            event_type: Tipo de evento
            user_id: ID del usuario relacionado con el evento
            data: Datos adicionales del evento
            tenant_id: ID del tenant (opcional)
            community_id: ID de la comunidad (opcional)
        """
        self.event_type = event_type
        self.user_id = user_id
        self.data = data
        self.tenant_id = tenant_id
        self.community_id = community_id
        self.timestamp = datetime.utcnow()

    def __repr__(self) -> str:
        return f"Event(type={self.event_type}, user_id={self.user_id}, timestamp={self.timestamp})"


class Observer(ABC):
    """Clase base abstracta para observadores de eventos."""

    @abstractmethod
    async def update(self, event: Event) -> None:
        """
        Método llamado cuando se dispara un evento.

        Args:
            event: El evento que se ha disparado
        """
        pass

    @abstractmethod
    def get_subscribed_events(self) -> list[EventType]:
        """
        Retorna la lista de tipos de eventos a los que este observador está suscrito.

        Returns:
            Lista de tipos de eventos
        """
        pass

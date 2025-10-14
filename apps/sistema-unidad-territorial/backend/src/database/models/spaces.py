from datetime import datetime
from typing import List, Optional
from uuid import UUID as PyUUID

from sqlalchemy import (
    Column,
    ForeignKey,
    String,
    Text,
    CheckConstraint,
    Index,
    Integer,
    Boolean,
)
from sqlalchemy.dialects.postgresql import UUID, TIMESTAMP, JSONB
from sqlalchemy.orm import relationship, Mapped

from src.database import SCHEMA
from src.database.models.base import SoftDeleteBaseModel
from src.database.enums import ReservationStatus


class Space(SoftDeleteBaseModel):
    """Reservable space model."""

    __tablename__ = 'spaces'

    community_id: Mapped[PyUUID] = Column(
        UUID(as_uuid=True), 
        ForeignKey(f'{SCHEMA}.communities.id', ondelete='CASCADE'), 
        nullable=False,
        comment="Community ID that owns this space"
    )
    name: Mapped[str] = Column(
        Text, 
        nullable=False,
        comment="Space name"
    )
    description: Mapped[Optional[str]] = Column(
        Text, 
        nullable=True,
        comment="Space description"
    )
    capacity: Mapped[Optional[int]] = Column(
        Integer,
        nullable=True,
        comment="Maximum capacity"
    )
    requires_approval: Mapped[bool] = Column(
        Boolean,
        nullable=False,
        default=True,
        server_default='true',
        comment="Whether reservations require approval"
    )
    rules_json: Mapped[Optional[dict]] = Column(
        JSONB,
        nullable=True,
        default={},
        server_default='{}',
        comment="Space rules and restrictions"
    )

    # Constraints and schema
    __table_args__ = (
        Index('idx_space_community', 'community_id'),
        {'schema': SCHEMA}
    )

    # Relationships
    community: Mapped["Community"] = relationship("Community", foreign_keys=[community_id])
    reservations: Mapped[List["Reservation"]] = relationship(
        "Reservation",
        back_populates="space",
        cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"Space(id={self.id}, name={self.name})"


class Reservation(SoftDeleteBaseModel):
    """Space reservation model."""

    __tablename__ = 'reservations'

    # Relationships
    space_id: Mapped[PyUUID] = Column(
        UUID(as_uuid=True), 
        ForeignKey(f'{SCHEMA}.spaces.id', ondelete='CASCADE'), 
        nullable=False,
        comment="Space ID for the reservation"
    )
    requesting_user_id: Mapped[PyUUID] = Column(
        UUID(as_uuid=True), 
        ForeignKey(f'{SCHEMA}.users.id', ondelete='RESTRICT'), 
        nullable=False,
        comment="User ID who made the reservation"
    )

    # Time information
    start_time: Mapped[datetime] = Column(
        TIMESTAMP,
        nullable=False,
        comment="Reservation start time"
    )
    end_time: Mapped[datetime] = Column(
        TIMESTAMP,
        nullable=False,
        comment="Reservation end time"
    )

    # Status y cancelación
    status: Mapped[str] = Column(
        String(20), 
        nullable=False,
        comment="Reservation status"
    )
    canceled_at: Mapped[Optional[datetime]] = Column(
        TIMESTAMP,
        nullable=True,
        comment="Cancellation timestamp"
    )
    cancel_reason: Mapped[Optional[str]] = Column(
        Text,
        nullable=True,
        comment="Reason for cancellation"
    )

    # Constraints and schema
    __table_args__ = (
        CheckConstraint('end_time > start_time', name='ck_reservation_end_after_start'),
        CheckConstraint(
            f"status IN ('{ReservationStatus.PENDING}', "
            f"'{ReservationStatus.CONFIRMED}', "
            f"'{ReservationStatus.CANCELLED}')",
            name='ck_reservation_status'
        ),
        # Indexes for optimizing queries
        Index('idx_reservation_space_start', 'space_id', 'start_time'),
        Index('idx_reservation_user', 'requesting_user_id'),
        # EXCLUDE constraint para prevenir solapes (requiere btree_gist)
        # Se implementará en la migración SQL directamente
        {'schema': SCHEMA}
    )

    # Relationships
    space: Mapped[Space] = relationship("Space", back_populates="reservations")
    requesting_user: Mapped["User"] = relationship("User", foreign_keys=[requesting_user_id])

    def __repr__(self) -> str:
        return (
            f"Reservation(id={self.id}, space_id={self.space_id}, "
            f"start_time={self.start_time}, end_time={self.end_time}, status={self.status})"
        )

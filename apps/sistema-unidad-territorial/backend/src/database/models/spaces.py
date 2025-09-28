from datetime import datetime
from typing import List, Optional
from uuid import UUID as PyUUID

from sqlalchemy import (
    Column,
    ForeignKey,
    String,
    Text,
    DateTime,
    CheckConstraint,
    Index,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, Mapped

from src.database import SCHEMA
from src.database.models.base import BaseModel
from src.database.enums import ReservationStatus


class Space(BaseModel):
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


class Reservation(BaseModel):
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
        DateTime(timezone=True), 
        nullable=False,
        comment="Reservation start time"
    )
    end_time: Mapped[datetime] = Column(
        DateTime(timezone=True), 
        nullable=False,
        comment="Reservation end time"
    )

    # Status
    status: Mapped[str] = Column(
        String(20), 
        nullable=False,
        comment="Reservation status"
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
        # EXCLUDE constraint for preventing overlaps
        # Note: This requires btree_gist extension in PostgreSQL
        # ExcludeConstraint is better handled at application level or via direct SQL
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

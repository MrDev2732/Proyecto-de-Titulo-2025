from datetime import datetime, timedelta
from typing import List, Optional

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
from src.database.models.base import TenantBaseModel
from src.database.enums import ReservationStatus
from src.database.timezone_utils import now_chile


class Space(TenantBaseModel):
    """Reservable space model."""

    __tablename__ = 'spaces'
    __table_args__ = {'schema': SCHEMA}

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

    # Relationships
    reservations: Mapped[List["Reservation"]] = relationship(
        "Reservation",
        back_populates="space",
        cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"Space(id={self.id}, name={self.name})"


class Reservation(TenantBaseModel):
    """Space reservation model."""

    __tablename__ = 'reservations'

    # Relationships
    space_id: Mapped[UUID] = Column(
        UUID(as_uuid=True), 
        ForeignKey(f'{SCHEMA}.spaces.id', ondelete='CASCADE'), 
        nullable=False,
        comment="Space ID for the reservation"
    )
    requesting_resident_id: Mapped[UUID] = Column(
        UUID(as_uuid=True), 
        ForeignKey(f'{SCHEMA}.residents.id', ondelete='RESTRICT'), 
        nullable=False,
        comment="Resident ID who made the reservation"
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
        Index('idx_reservation_resident', 'requesting_resident_id'),
        # EXCLUDE constraint for preventing overlaps
        # Note: This requires btree_gist extension in PostgreSQL
        # ExcludeConstraint is better handled at application level or via direct SQL
        {'schema': SCHEMA}
    )

    # Relationships
    space: Mapped[Space] = relationship("Space", back_populates="reservations")
    requesting_resident: Mapped["Resident"] = relationship("Resident", back_populates="reservations")

    def __repr__(self) -> str:
        return (
            f"Reservation(id={self.id}, space_id={self.space_id}, "
            f"start_time={self.start_time}, end_time={self.end_time}, status={self.status})"
        )

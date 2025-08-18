from datetime import date
from typing import List, Optional
import re

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    ForeignKey,
    String,
    Text,
    CheckConstraint,
    text,
)
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, Mapped

from src.database import SCHEMA
from src.database.models.base import TenantBaseModel
from src.database.enums import EvidenceType


class Resident(TenantBaseModel):
    """Resident model for the system."""

    __tablename__ = 'residents'

    # User reference (optional)
    user_id: Mapped[Optional[UUID]] = Column(
        UUID(as_uuid=True), 
        ForeignKey(f'{SCHEMA}.users.id', ondelete='SET NULL'), 
        nullable=True,
        comment="Associated user ID (optional)"
    )

    # Personal information
    rut: Mapped[str] = Column(
        String(15), 
        nullable=False, 
        unique=True,
        comment="Chilean RUT (national ID)"
    )
    name: Mapped[str] = Column(
        Text, 
        nullable=False,
        comment="Full name of the resident"
    )
    address: Mapped[str] = Column(
        Text, 
        nullable=False,
        comment="Complete address"
    )
    neighborhood_unit: Mapped[Optional[str]] = Column(
        Text, 
        nullable=True, 
        comment="Neighborhood unit (UV - Unidad Vecinal)"
    )

    # Status and dates
    verified: Mapped[bool] = Column(
        Boolean, 
        nullable=False, 
        default=False, 
        server_default='false',
        comment="Whether the resident is verified"
    )
    registration_date: Mapped[date] = Column(
        Date, 
        nullable=False, 
        default=date.today, 
        server_default=func.current_date(),
        comment="Date when the resident was registered"
    )

    # Constraints and schema
    __table_args__ = (
        CheckConstraint(
            r"rut ~ '^[0-9]{1,2}\.?[0-9]{3}\.?[0-9]{3}-[0-9kK]{1}$'",
            name='ck_resident_rut_format'
        ),
        {'schema': SCHEMA}
    )

    # Relationships
    user: Mapped[Optional["User"]] = relationship("User", back_populates="resident")
    address_evidences: Mapped[List["AddressEvidence"]] = relationship(
        "AddressEvidence",
        back_populates="resident",
        cascade="all, delete-orphan"
    )
    certificates: Mapped[List["Certificate"]] = relationship(
        "Certificate",
        back_populates="resident",
        cascade="delete"  # RESTRICT in SQL, handled by application
    )
    reservations: Mapped[List["Reservation"]] = relationship(
        "Reservation",
        back_populates="requesting_resident",
        cascade="delete"  # RESTRICT in SQL, handled by application
    )
    projects: Mapped[List["Project"]] = relationship(
        "Project",
        back_populates="requesting_resident",
        cascade="delete"  # RESTRICT in SQL, handled by application
    )

    @property
    def masked_rut(self) -> str:
        """Return the RUT masked for public display."""
        # Apply the same logic as the v_vecino_publico view
        return re.sub(r'(^[0-9]{1,2}\.?[0-9]{3}\.?)[0-9]{3}', r'\1***', self.rut)

    def __repr__(self) -> str:
        return f"Resident(id={self.id}, rut={self.masked_rut}, name={self.name})"


class AddressEvidence(TenantBaseModel):
    """Address evidence model for residents."""

    __tablename__ = 'address_evidences'

    resident_id: Mapped[UUID] = Column(
        UUID(as_uuid=True), 
        ForeignKey(f'{SCHEMA}.residents.id', ondelete='CASCADE'), 
        nullable=False,
        comment="Resident ID for the evidence"
    )
    type: Mapped[str] = Column(
        String(30), 
        nullable=False,
        comment="Type of address evidence"
    )
    url: Mapped[str] = Column(
        Text, 
        nullable=False, 
        comment="URL of the evidence file"
    )

    # Constraints and schema
    __table_args__ = (
        CheckConstraint(
            f"type IN ('{EvidenceType.UTILITY_BILL}', "
            f"'{EvidenceType.RENTAL_CONTRACT}', "
            f"'{EvidenceType.OTHER}')",
            name='ck_evidence_type'
        ),
        {'schema': SCHEMA}
    )

    # Relationships
    resident: Mapped[Resident] = relationship("Resident", back_populates="address_evidences")

    def __repr__(self) -> str:
        return f"AddressEvidence(id={self.id}, resident_id={self.resident_id}, type={self.type})"

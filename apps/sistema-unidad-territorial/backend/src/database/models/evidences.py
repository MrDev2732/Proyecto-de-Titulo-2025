from sqlalchemy import (
    Column,
    ForeignKey,
    String,
    Text,
    CheckConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, Mapped

from src.database import SCHEMA
from src.database.models.base import TenantSoftDeleteModel
from src.database.enums import EvidenceType


class AddressEvidence(TenantSoftDeleteModel):
    """Address evidence model for users."""

    __tablename__ = 'address_evidences'

    user_id: Mapped[UUID] = Column(
        UUID(as_uuid=True), 
        ForeignKey(f'{SCHEMA}.users.id', ondelete='CASCADE'), 
        nullable=False,
        comment="User ID for the evidence"
    )
    type: Mapped[str] = Column(
        String(30), 
        nullable=False,
        comment="Type of address evidence"
    )
    bucket: Mapped[str] = Column(
        Text,
        nullable=False,
        comment="Bucket donde se almacena la evidencia"
    )
    storage_key: Mapped[str] = Column(
        Text,
        nullable=False,
        comment="Clave de almacenamiento de la evidencia"
    )
    sha256: Mapped[str] = Column(
        String(64),
        nullable=False,
        comment="SHA256 hash del archivo"
    )
    mime_type: Mapped[str] = Column(
        String(100),
        nullable=False,
        comment="Tipo MIME del archivo"
    )

    # Constraints and schema
    __table_args__ = (
        CheckConstraint(
            f"type IN ('{EvidenceType.UTILITY_BILL.value}', "
            f"'{EvidenceType.RENTAL_CONTRACT.value}', "
            f"'{EvidenceType.OTHER.value}')",
            name='ck_evidence_type'
        ),
        {'schema': SCHEMA}
    )

    # Relationships
    user: Mapped["User"] = relationship("User", foreign_keys=[user_id])

    def __repr__(self) -> str:
        return f"AddressEvidence(id={self.id}, user_id={self.user_id}, type={self.type})"

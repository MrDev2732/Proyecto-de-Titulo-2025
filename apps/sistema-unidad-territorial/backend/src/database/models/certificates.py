from typing import Optional

from sqlalchemy import (
    Column,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
    CheckConstraint,
    event,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, Mapped
from sqlalchemy.exc import IntegrityError

from src.database import SCHEMA
from src.database.models.base import TenantBaseModel
from src.database.enums import CertificateStatus


class Certificate(TenantBaseModel):
    """Residence certificate model."""

    __tablename__ = 'certificates'

    # Basic relationships
    resident_id: Mapped[UUID] = Column(
        UUID(as_uuid=True), 
        ForeignKey('residents.id', ondelete='RESTRICT'), 
        nullable=False,
        comment="Resident ID for the certificate"
    )
    approver_id: Mapped[Optional[UUID]] = Column(
        UUID(as_uuid=True), 
        ForeignKey('users.id', ondelete='SET NULL'), 
        nullable=True,
        comment="User ID who approved the certificate"
    )

    # Certificate information
    status: Mapped[str] = Column(
        String(20), 
        nullable=False,
        comment="Certificate processing status"
    )
    reason: Mapped[Optional[str]] = Column(
        Text, 
        nullable=True, 
        comment="Reason for rejection or observations"
    )
    folio: Mapped[str] = Column(
        Text, 
        nullable=False,
        comment="Certificate folio number"
    )

    # PDF file information
    pdf_url: Mapped[Optional[str]] = Column(
        Text, 
        nullable=True,
        comment="URL of the generated PDF certificate"
    )
    pdf_sha256: Mapped[Optional[str]] = Column(
        String(64), 
        nullable=True,
        comment="SHA256 hash of the PDF file"
    )

    # Constraints and schema
    __table_args__ = (
        CheckConstraint(
            f"status IN ('{CertificateStatus.PENDING}', "
            f"'{CertificateStatus.APPROVED}', "
            f"'{CertificateStatus.REJECTED}', "
            f"'{CertificateStatus.ISSUED}')",
            name='ck_certificate_status'
        ),
        CheckConstraint(
            r"pdf_sha256 IS NULL OR pdf_sha256 ~ '^[0-9a-f]{64}$'",
            name='ck_certificate_sha256_format'
        ),
        UniqueConstraint('tenant_id', 'folio', name='uq_certificate_tenant_folio'),
        {'schema': SCHEMA}
    )

    # Relationships
    resident: Mapped["Resident"] = relationship("Resident", back_populates="certificates")
    approver: Mapped[Optional["User"]] = relationship("User", foreign_keys=[approver_id])

    def __repr__(self) -> str:
        return f"Certificate(id={self.id}, folio={self.folio}, status={self.status})"


# Event listener to validate ISSUED status
@event.listens_for(Certificate, 'before_insert')
@event.listens_for(Certificate, 'before_update')
def validate_certificate_issued(mapper, connection, target):
    """
    Validate that a certificate marked as ISSUED has pdf_url and pdf_sha256.

    Equivalent to the trg_certificado_emitido_chk() trigger in PostgreSQL.
    """
    if (target.status == CertificateStatus.ISSUED and 
        (target.pdf_url is None or target.pdf_sha256 is None)):
        raise IntegrityError(
            "Cannot mark as ISSUED without pdf_url and pdf_sha256",
            None,
            None
        )

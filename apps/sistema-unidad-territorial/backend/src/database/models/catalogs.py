"""
Catálogos de estado para el sistema.

Estos catálogos reemplazan los enums de string por tablas con FK,
siguiendo las decisiones de base del plan de saneamiento.
"""

from sqlalchemy import Column, String, Text, Integer, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped
from uuid import UUID as PyUUID

from src.database import SCHEMA
from src.database.models.base import BaseModel


class StatusReservation(BaseModel):
    """Catálogo de estados para reservas."""

    __tablename__ = 'status_reservation'
    __table_args__ = {'schema': SCHEMA}

    code: Mapped[str] = Column(
        String(20),
        primary_key=True,
        comment="Código del estado de reserva"
    )
    name: Mapped[str] = Column(
        String(50),
        nullable=False,
        comment="Nombre descriptivo del estado"
    )
    description: Mapped[str] = Column(
        Text,
        nullable=True,
        comment="Descripción del estado"
    )
    sort_order: Mapped[int] = Column(
        Integer,
        nullable=False,
        default=0,
        comment="Orden de visualización"
    )

    def __repr__(self) -> str:
        return f"StatusReservation(code={self.code}, name={self.name})"


class StatusCertificate(BaseModel):
    """Catálogo de estados para certificados."""

    __tablename__ = 'status_certificate'
    __table_args__ = {'schema': SCHEMA}

    code: Mapped[str] = Column(
        String(20),
        primary_key=True,
        comment="Código del estado de certificado"
    )
    name: Mapped[str] = Column(
        String(50),
        nullable=False,
        comment="Nombre descriptivo del estado"
    )
    description: Mapped[str] = Column(
        Text,
        nullable=True,
        comment="Descripción del estado"
    )
    sort_order: Mapped[int] = Column(
        Integer,
        nullable=False,
        default=0,
        comment="Orden de visualización"
    )

    def __repr__(self) -> str:
        return f"StatusCertificate(code={self.code}, name={self.name})"


class StatusProject(BaseModel):
    """Catálogo de estados para proyectos."""

    __tablename__ = 'status_project'
    __table_args__ = {'schema': SCHEMA}

    code: Mapped[str] = Column(
        String(20),
        primary_key=True,
        comment="Código del estado de proyecto"
    )
    name: Mapped[str] = Column(
        String(50),
        nullable=False,
        comment="Nombre descriptivo del estado"
    )
    description: Mapped[str] = Column(
        Text,
        nullable=True,
        comment="Descripción del estado"
    )
    sort_order: Mapped[int] = Column(
        Integer,
        nullable=False,
        default=0,
        comment="Orden de visualización"
    )

    def __repr__(self) -> str:
        return f"StatusProject(code={self.code}, name={self.name})"


class StatusMembership(BaseModel):
    """Catálogo de estados para membresías."""

    __tablename__ = 'status_membership'
    __table_args__ = {'schema': SCHEMA}

    code: Mapped[str] = Column(
        String(20),
        primary_key=True,
        comment="Código del estado de membresía"
    )
    name: Mapped[str] = Column(
        String(50),
        nullable=False,
        comment="Nombre descriptivo del estado"
    )
    description: Mapped[str] = Column(
        Text,
        nullable=True,
        comment="Descripción del estado"
    )
    sort_order: Mapped[int] = Column(
        Integer,
        nullable=False,
        default=0,
        comment="Orden de visualización"
    )

    def __repr__(self) -> str:
        return f"StatusMembership(code={self.code}, name={self.name})"


class StatusRegistration(BaseModel):
    """Catálogo de estados para solicitudes de registro."""

    __tablename__ = 'status_registration'
    __table_args__ = {'schema': SCHEMA}

    code: Mapped[str] = Column(
        String(20),
        primary_key=True,
        comment="Código del estado de solicitud de registro"
    )
    name: Mapped[str] = Column(
        String(50),
        nullable=False,
        comment="Nombre descriptivo del estado"
    )
    description: Mapped[str] = Column(
        Text,
        nullable=True,
        comment="Descripción del estado"
    )
    sort_order: Mapped[int] = Column(
        Integer,
        nullable=False,
        default=0,
        comment="Orden de visualización"
    )

    def __repr__(self) -> str:
        return f"StatusRegistration(code={self.code}, name={self.name})"


class TenantFolioSeq(BaseModel):
    """Secuencia de folios por tenant para certificados."""

    __tablename__ = 'tenant_folio_seq'
    __table_args__ = {'schema': SCHEMA}

    tenant_id: Mapped[PyUUID] = Column(
        UUID(as_uuid=True),
        ForeignKey(f'{SCHEMA}.tenants.id', ondelete='CASCADE'),
        primary_key=True,
        comment="ID del tenant"
    )
    last_folio: Mapped[int] = Column(
        Integer,
        nullable=False,
        default=0,
        comment="Último folio emitido"
    )

    def __repr__(self) -> str:
        return f"TenantFolioSeq(tenant_id={self.tenant_id}, last_folio={self.last_folio})"

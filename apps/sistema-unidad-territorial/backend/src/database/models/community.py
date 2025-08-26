from datetime import datetime
from typing import List, Optional
from uuid import UUID as PyUUID

from sqlalchemy import (
    Boolean,
    Column,
    Enum,
    ForeignKey,
    Text,
    UniqueConstraint,
    Index,
    DateTime,
)
from sqlalchemy.dialects.postgresql import UUID, CITEXT
from sqlalchemy.orm import relationship, Mapped

from src.database import SCHEMA
from src.database.models.base import BaseModel
from src.database.enums import (
    MembershipStatus,
    RegistrationStatus,
    RegistrationProvider,
    AttachmentKind
)


class Community(BaseModel):
    """Community model (Juntas Vecinales) under Municipalities (Tenants)."""

    __tablename__ = 'communities'

    tenant_id: Mapped[PyUUID] = Column(
        UUID(as_uuid=True), 
        ForeignKey(f'{SCHEMA}.tenants.id', ondelete='RESTRICT'), 
        nullable=False,
        comment="Municipality (tenant) ID that owns this community"
    )
    name: Mapped[str] = Column(
        Text, 
        nullable=False,
        comment="Community name (e.g., 'Junta Vecinos Villa Norte')"
    )
    description: Mapped[Optional[str]] = Column(
        Text, 
        nullable=True,
        comment="Community description"
    )

    # Constraints and schema
    __table_args__ = (
        UniqueConstraint('tenant_id', 'name', name='uq_community_tenant_name'),
        Index('idx_community_tenant', 'tenant_id'),
        {'schema': SCHEMA}
    )

    # Relationships
    tenant = relationship(
        "Tenant",
        foreign_keys=[tenant_id],
        back_populates=None
    )
    memberships = relationship(
        "ResidentMembership",
        back_populates="community",
        cascade="all, delete-orphan"
    )
    registration_requests = relationship(
        "RegistrationRequest",
        back_populates="community",
        cascade="all, delete-orphan"
    )
    # Role assignments via unified system
    role_assignments = relationship(
        "RoleAssignment",
        foreign_keys="RoleAssignment.community_id",
        back_populates="community"
    )

    def __repr__(self) -> str:
        return f"Community(id={self.id}, name={self.name}, tenant_id={self.tenant_id})"


class ResidentMembership(BaseModel):
    """Formal membership linking residents to communities."""

    __tablename__ = 'resident_memberships'

    user_id: Mapped[PyUUID] = Column(
        UUID(as_uuid=True), 
        ForeignKey(f'{SCHEMA}.users.id', ondelete='CASCADE'), 
        nullable=False,
        comment="User ID for the membership"
    )
    community_id: Mapped[PyUUID] = Column(
        UUID(as_uuid=True), 
        ForeignKey(f'{SCHEMA}.communities.id', ondelete='CASCADE'), 
        nullable=False,
        comment="Community ID for the membership"
    )
    status: Mapped[MembershipStatus] = Column(
        Enum(MembershipStatus, name='membership_status_enum', values_callable=lambda obj: [e.value for e in obj]),
        nullable=False,
        comment="Membership status"
    )
    verified: Mapped[bool] = Column(
        Boolean, 
        nullable=False, 
        default=False,
        server_default='false',
        comment="Whether the membership is verified"
    )
    verified_at: Mapped[Optional[datetime]] = Column(
        DateTime(timezone=True), 
        nullable=True,
        comment="Verification timestamp"
    )

    # Constraints and schema
    __table_args__ = (
        UniqueConstraint('user_id', 'community_id', name='uq_membership_user_community'),
        Index('idx_membership_community_status', 'community_id', 'status'),
        Index('idx_membership_user', 'user_id'),
        {'schema': SCHEMA}
    )

    # Relationships
    user = relationship(
        "User",
        foreign_keys=[user_id],
        back_populates=None
    )
    community = relationship(
        "Community",
        back_populates="memberships"
    )

    def __repr__(self) -> str:
        return f"ResidentMembership(id={self.id}, user_id={self.user_id}, community_id={self.community_id}, status={self.status})"


class RegistrationRequest(BaseModel):
    """Registration workflow model that blocks login until approval."""

    __tablename__ = 'registration_requests'

    tenant_id: Mapped[PyUUID] = Column(
        UUID(as_uuid=True), 
        ForeignKey(f'{SCHEMA}.tenants.id', ondelete='RESTRICT'), 
        nullable=False,
        comment="Municipality (tenant) ID"
    )
    community_id: Mapped[PyUUID] = Column(
        UUID(as_uuid=True), 
        ForeignKey(f'{SCHEMA}.communities.id', ondelete='RESTRICT'), 
        nullable=False,
        comment="Community ID where user wants to register"
    )
    email: Mapped[str] = Column(
        CITEXT, 
        nullable=False,
        comment="Applicant email address"
    )
    full_name: Mapped[Optional[str]] = Column(
        Text, 
        nullable=True,
        comment="Applicant full name"
    )
    rut: Mapped[Optional[str]] = Column(
        Text, 
        nullable=True,
        comment="Chilean RUT (optional at submission; validated on approval)"
    )
    address: Mapped[Optional[str]] = Column(
        Text, 
        nullable=True,
        comment="Applicant address"
    )
    provider: Mapped[RegistrationProvider] = Column(
        Enum(RegistrationProvider, name='registration_provider_enum', values_callable=lambda obj: [e.value for e in obj]),
        nullable=False,
        comment="Authentication provider"
    )
    status: Mapped[RegistrationStatus] = Column(
        Enum(RegistrationStatus, name='registration_status_enum', values_callable=lambda obj: [e.value for e in obj]),
        nullable=False, 
        default=RegistrationStatus.PENDING,
        server_default='PENDING',
        comment="Request status"
    )
    decided_by: Mapped[Optional[PyUUID]] = Column(
        UUID(as_uuid=True), 
        ForeignKey(f'{SCHEMA}.users.id', ondelete='SET NULL'), 
        nullable=True,
        comment="Moderator who made the decision"
    )
    decided_at: Mapped[Optional[datetime]] = Column(
        DateTime(timezone=True), 
        nullable=True,
        comment="Decision timestamp"
    )
    decision_notes: Mapped[Optional[str]] = Column(
        Text, 
        nullable=True,
        comment="Notes from the moderator decision"
    )

    # Constraints and schema
    __table_args__ = (
        Index('idx_registration_tenant_community_status', 'tenant_id', 'community_id', 'status'),
        Index('idx_registration_email', 'email'),
        Index('idx_registration_status_created', 'status', 'created_at'),
        {'schema': SCHEMA}
    )

    # Relationships
    tenant = relationship(
        "Tenant",
        foreign_keys=[tenant_id],
        back_populates=None
    )
    community = relationship(
        "Community",
        back_populates="registration_requests"
    )
    decided_by_user = relationship(
        "User",
        foreign_keys=[decided_by],
        back_populates=None
    )
    attachments = relationship(
        "RegistrationRequestAttachment",
        back_populates="registration_request",
        cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"RegistrationRequest(id={self.id}, email={self.email}, community_id={self.community_id}, status={self.status})"


class RegistrationRequestAttachment(BaseModel):
    """Evidence attachments for registration requests."""

    __tablename__ = 'registration_request_attachments'

    registration_request_id: Mapped[PyUUID] = Column(
        UUID(as_uuid=True), 
        ForeignKey(f'{SCHEMA}.registration_requests.id', ondelete='CASCADE'), 
        nullable=False,
        comment="Registration request ID"
    )
    url: Mapped[str] = Column(
        Text, 
        nullable=False,
        comment="URL of the attachment file"
    )
    kind: Mapped[AttachmentKind] = Column(
        Enum(AttachmentKind, name='attachment_kind_enum', values_callable=lambda obj: [e.value for e in obj]),
        nullable=False,
        comment="Type of attachment"
    )

    # Constraints and schema
    __table_args__ = (
        Index('idx_attachment_request', 'registration_request_id'),
        {'schema': SCHEMA}
    )

    # Relationships
    registration_request = relationship(
        "RegistrationRequest",
        back_populates="attachments"
    )

    def __repr__(self) -> str:
        return f"RegistrationRequestAttachment(id={self.id}, registration_request_id={self.registration_request_id}, kind={self.kind})"

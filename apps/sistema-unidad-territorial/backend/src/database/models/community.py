from datetime import datetime
from typing import Optional
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
    String,
)
from sqlalchemy.dialects.postgresql import UUID, CITEXT, TIMESTAMP
from sqlalchemy.orm import relationship, Mapped, foreign

from src.database import SCHEMA
from src.database.models.base import BaseModel, SoftDeleteBaseModel
from src.database.enums import (
    MembershipStatus,
    RegistrationStatus,
    RegistrationProvider,
    AttachmentKind,
    BoardRole
)


class Community(SoftDeleteBaseModel):
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
        back_populates=None,
        lazy="noload"
    )
    memberships = relationship(
        "ResidentMembership",
        back_populates="community",
        cascade="all, delete-orphan",
        lazy="noload"
    )
    registration_requests = relationship(
        "RegistrationRequest",
        back_populates="community",
        cascade="all, delete-orphan",
        lazy="noload"
    )
    # Role assignments for this community (unified table)
    role_assignments = relationship(
        "RoleAssignment",
        primaryjoin="and_(Community.id == foreign(RoleAssignment.scope_id), RoleAssignment.scope_type == 'community')",
        viewonly=True,
        lazy="noload"
    )

    def __repr__(self) -> str:
        return f"Community(id={self.id}, name={self.name}, tenant_id={self.tenant_id})"


class ResidentMembership(SoftDeleteBaseModel):
    """
    Formal membership linking users to communities.

    MULTI-TENANT SUPPORT:
    - Users can have multiple memberships across different communities/tenants
    - Always filter by community_id or tenant_id in queries to avoid context mixing
    - Board roles are community-specific (user can be president in one, member in another)

    Example:
        # Juan lives in both Recoleta and Maipú
        juan_recoleta = ResidentMembership(user_id=juan_id, community_id=recoleta_id, board_role=BoardRole.PRESIDENT)
        juan_maipu = ResidentMembership(user_id=juan_id, community_id=maipu_id, board_role=None)
    """

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
        TIMESTAMP(timezone=True),
        nullable=True,
        comment="Verification timestamp"
    )
    verified_by: Mapped[Optional[PyUUID]] = Column(
        UUID(as_uuid=True),
        ForeignKey(f'{SCHEMA}.users.id', ondelete='SET NULL'),
        nullable=True,
        comment="User who verified the membership"
    )
    verification_method: Mapped[Optional[str]] = Column(
        String(50),
        nullable=True,
        comment="Method used for verification"
    )
    board_role: Mapped[Optional[BoardRole]] = Column(
        Enum(BoardRole, name='board_role_enum', values_callable=lambda obj: [e.value for e in obj]),
        nullable=True,
        comment="Board role if member is part of community governance"
    )

    # Constraints and schema
    __table_args__ = (
        UniqueConstraint('user_id', 'community_id', name='uq_membership_user_community'),
        # Partial unique index to ensure only one person per board role per community (except vocal)
        Index('idx_membership_unique_board_role', 'community_id', 'board_role', unique=True,
              postgresql_where="board_role IS NOT NULL AND board_role != 'vocal'"),
        Index('idx_membership_community_status', 'community_id', 'status'),
        Index('idx_membership_user', 'user_id'),
        Index('idx_membership_board', 'community_id', 'board_role'),
        {'schema': SCHEMA}
    )

    # Relationships
    user = relationship(
        "User",
        foreign_keys=[user_id],
        back_populates="memberships",
        lazy="noload"
    )
    community = relationship(
        "Community",
        back_populates="memberships",
        lazy="noload"
    )

    @property
    def is_board_member(self) -> bool:
        """Check if this membership includes a board role."""
        return self.board_role is not None

    @property
    def is_executive_board_member(self) -> bool:
        """Check if this is an executive board role (president, secretary, treasurer)."""
        return self.board_role is not None and self.board_role.is_executive

    def __repr__(self) -> str:
        board_info = f", board_role={self.board_role.value}" if self.board_role else ""
        return f"ResidentMembership(id={self.id}, user_id={self.user_id}, community_id={self.community_id}, status={self.status}{board_info})"


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
        TIMESTAMP(timezone=True),
        nullable=True,
        comment="Decision timestamp"
    )
    expires_at: Mapped[Optional[datetime]] = Column(
        TIMESTAMP(timezone=True),
        nullable=True,
        comment="Request expiration timestamp"
    )
    decision_notes: Mapped[Optional[str]] = Column(
        Text, 
        nullable=True,
        comment="Notes from the moderator decision"
    )

    # Constraints and schema
    __table_args__ = (
        # Solo una solicitud activa por comunidad+email
        Index(
            'idx_registration_active_unique',
            'community_id', 'email',
            unique=True,
            postgresql_where="status IN ('pending', 'under_review')"
        ),
        Index('idx_registration_tenant_community_status', 'tenant_id', 'community_id', 'status'),
        Index('idx_registration_email', 'email'),
        Index('idx_registration_status_created', 'status', 'created_at'),
        {'schema': SCHEMA}
    )

    # Relationships
    tenant = relationship(
        "Tenant",
        foreign_keys=[tenant_id],
        back_populates=None,
        lazy="noload"
    )
    community = relationship(
        "Community",
        back_populates="registration_requests",
        lazy="noload"
    )
    decided_by_user = relationship(
        "User",
        foreign_keys=[decided_by],
        back_populates=None,
        lazy="noload"
    )
    attachments = relationship(
        "RegistrationRequestAttachment",
        back_populates="registration_request",
        cascade="all, delete-orphan",
        lazy="noload"
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
    bucket: Mapped[str] = Column(
        Text,
        nullable=False,
        comment="Bucket donde se almacena el archivo"
    )
    storage_key: Mapped[str] = Column(
        Text,
        nullable=False,
        comment="Clave de almacenamiento del archivo"
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
        back_populates="attachments",
        lazy="noload"
    )

    @property
    def url(self) -> str:
        """
        Propiedad computada para generar URL del archivo.
        Mantiene compatibilidad con código existente.
        Retorna solo el storage_key porque el router ya tiene el prefijo /files.
        """
        return self.storage_key

    def __repr__(self) -> str:
        return f"RegistrationRequestAttachment(id={self.id}, registration_request_id={self.registration_request_id}, kind={self.kind})"

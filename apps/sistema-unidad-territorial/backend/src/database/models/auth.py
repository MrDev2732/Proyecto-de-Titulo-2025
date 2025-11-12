from datetime import datetime
from typing import List, Optional
from uuid import UUID as PyUUID

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
    CheckConstraint,
    Index,
    LargeBinary,
)
from sqlalchemy.dialects.postgresql import CITEXT, UUID
from sqlalchemy.orm import relationship, Mapped

from src.database import SCHEMA
from src.database.enums import (
    AuthProvider,
    AuthMethod, 
    AuthResult,
    AuthFailureReason,
    RoleScope,
    UserStatus,
)
from src.database.utils import now_chile
from src.database.models.base import BaseModel, TenantBaseModel, SoftDeleteBaseModel


class User(SoftDeleteBaseModel):
    """
    User model for the system.

    AUTHENTICATION STRATEGY:
    - Primary: OIDC/OAuth (Google, etc.) - no password needed
    - Fallback: Local password for users who prefer it
    - Institutional: OIDC + verified institutional email for municipal roles

    EMAIL MANAGEMENT:
    - All emails centralized in user_emails table
    - primary_email_id points to the main email
    - Supports multiple emails per user (personal + institutional)
    - Email verification handled in user_emails.verified_at
    """

    __tablename__ = 'users'

    # Primary email reference (centralized in user_emails table)
    primary_email_id: Mapped[Optional[PyUUID]] = Column(
        UUID(as_uuid=True), 
        ForeignKey(f'{SCHEMA}.user_emails.id', ondelete='SET NULL'), 
        nullable=True,
        comment="Primary email ID (references user_emails table)"
    )
    password_hash: Mapped[Optional[str]] = Column(
        Text, 
        nullable=True,
        comment="Password hash using Argon2id (NULL for OAuth-only users - preferred)"
    )
    status: Mapped[UserStatus] = Column(
        Enum(UserStatus, name='user_status_enum', values_callable=lambda obj: [e.name for e in obj]),
        nullable=False,
        default=UserStatus.ACTIVE,
        server_default='ACTIVE',
        comment="User account status"
    )

    # Personal information
    full_name: Mapped[Optional[str]] = Column(
        Text, 
        nullable=True,
        comment="User's full name"
    )
    rut: Mapped[Optional[str]] = Column(
        Text,
        nullable=True,
        comment="Chilean RUT normalizado (formato: 12345678-9)"
    )
    address: Mapped[Optional[str]] = Column(
        Text, 
        nullable=True,
        comment="User's residential address"
    )

    # Constraints and schema
    __table_args__ = (
        CheckConstraint(
            "rut IS NULL OR rut ~ '^[0-9]{7,8}-[0-9Kk]$'",
            name='ck_user_rut_format'
        ),
        Index('idx_user_primary_email', 'primary_email_id'),
        Index('idx_user_rut', 'rut', postgresql_where='deleted_at IS NULL'),
        Index('idx_user_full_name', 'full_name'),
        {'schema': SCHEMA}
    )

    # Role assignments - unified polymorphic table
    role_assignments: Mapped[List["RoleAssignment"]] = relationship(
        "RoleAssignment",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="noload"
    )
    oauth_identities: Mapped[List["UserOauthIdentity"]] = relationship(
        "UserOauthIdentity",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="noload"
    )
    sessions: Mapped[List["UserSession"]] = relationship(
        "UserSession",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="noload"
    )
    # Email relationships
    primary_email: Mapped[Optional["UserEmail"]] = relationship(
        "UserEmail",
        foreign_keys=[primary_email_id],
        post_update=True,
        lazy="noload"
    )
    emails: Mapped[List["UserEmail"]] = relationship(
        "UserEmail",
        foreign_keys="UserEmail.user_id",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="noload"
    )
    # Community memberships
    memberships: Mapped[List["ResidentMembership"]] = relationship(
        "ResidentMembership",
        foreign_keys="ResidentMembership.user_id",
        back_populates="user",
        viewonly=True,
        lazy="noload"
    )

    @property
    def email(self) -> Optional[str]:
        """Get primary email address."""
        return self.primary_email.email if self.primary_email else None

    @property
    def is_email_verified(self) -> bool:
        """Check if primary email is verified."""
        return self.primary_email.is_verified if self.primary_email else False

    @property
    def tenant_id(self) -> Optional[PyUUID]:
        """
        Get tenant ID from community memberships.
        Obtiene el tenant_id desde: User -> ResidentMembership -> Community -> Tenant

        Retorna el tenant_id de la primera membresía activa/aprobada.
        Útil para logging y operaciones multi-tenant.
        """
        if hasattr(self, 'memberships') and self.memberships:
            from src.database.enums import MembershipStatus
            for membership in self.memberships:
                # Buscar membresía activa/aprobada con comunidad cargada
                if (membership.status == MembershipStatus.APPROVED and 
                    hasattr(membership, 'community') and 
                    membership.community and
                    not membership.is_deleted):
                    return membership.community.tenant_id

        # Fallback: intentar desde role_assignments
        if self.role_assignments:
            for assignment in self.role_assignments:
                if assignment.tenant_id and not assignment.is_deleted:
                    return assignment.tenant_id

        return None

    def get_verified_emails(self) -> List["UserEmail"]:
        """Get all verified emails for this user."""
        return [email for email in self.emails if email.is_verified]

    def get_institutional_emails(self) -> List["UserEmail"]:
        """Get all institutional emails for this user."""
        return [email for email in self.emails if email.is_institutional]

    def has_verified_institutional_email(self, domain: str) -> bool:
        """Check if user has a verified institutional email for the given domain."""
        return any(
            email.is_verified and email.get_domain() == domain.lower()
            for email in self.get_institutional_emails()
        )

    @property
    def is_oauth_only(self) -> bool:
        """Check if user uses only OAuth authentication (no local password)."""
        return self.password_hash is None

    @property
    def has_local_password(self) -> bool:
        """Check if user has a local password set."""
        return self.password_hash is not None

    @property
    def auth_methods(self) -> List[str]:
        """Get available authentication methods for this user."""
        methods = []
        if self.has_local_password:
            methods.append("password")
        if self.oauth_identities:
            methods.extend([identity.provider for identity in self.oauth_identities])
        return methods

    @property
    def display_name(self) -> str:
        """Get display name for the user (full name or email)."""
        if self.full_name:
            return self.full_name
        return self.email or "Usuario sin nombre"

    @property
    def has_complete_profile(self) -> bool:
        """Check if user has complete personal information."""
        return all([
            self.full_name,
            self.rut,
            self.address,
            self.email
        ])

    def format_rut(self) -> Optional[str]:
        """Format RUT with standard Chilean format (XX.XXX.XXX-X)."""
        if not self.rut:
            return None

        # Remove any existing formatting
        clean_rut = ''.join(filter(str.isalnum, self.rut.upper()))

        if len(clean_rut) < 8:
            return self.rut  # Return as-is if too short

        # Split into number and verification digit
        rut_number = clean_rut[:-1]
        verification_digit = clean_rut[-1]

        # Add dots every 3 digits from right to left
        formatted_number = ""
        for i, digit in enumerate(reversed(rut_number)):
            if i > 0 and i % 3 == 0:
                formatted_number = "." + formatted_number
            formatted_number = digit + formatted_number

        return f"{formatted_number}-{verification_digit}"

    def __repr__(self) -> str:
        email_display = self.email or "no-email"
        name_display = f" ({self.full_name})" if self.full_name else ""
        return f"User(id={self.id}, email={email_display}{name_display}, status={self.status})"


class UserEmail(BaseModel):
    """
    User email model - centralized email management.

    This is the single source of truth for all user emails:
    - Personal emails (from registration/OAuth)
    - Institutional emails (for municipal roles)
    - Multiple emails per user supported
    - Only one primary email per user
    """

    __tablename__ = 'user_emails'

    user_id: Mapped[PyUUID] = Column(
        UUID(as_uuid=True), 
        ForeignKey(f'{SCHEMA}.users.id', ondelete='CASCADE'), 
        nullable=False,
        comment="User ID for the email"
    )
    email: Mapped[str] = Column(
        CITEXT, 
        nullable=False,
        unique=True,  # Global email uniqueness
        comment="Email address"
    )
    verified_at: Mapped[Optional[datetime]] = Column(
        DateTime(timezone=True), 
        nullable=True,
        comment="Email verification timestamp"
    )
    is_primary: Mapped[bool] = Column(
        Boolean, 
        nullable=False, 
        default=False,
        server_default='false',
        comment="Whether this is the user's primary email"
    )
    email_type: Mapped[str] = Column(
        String(20), 
        nullable=False, 
        default='personal',
        server_default='personal',
        comment="Email type: personal, institutional, recovery"
    )

    # Constraints and schema
    __table_args__ = (
        UniqueConstraint('user_id', 'email', name='uq_user_email'),
        CheckConstraint(
            "email_type IN ('personal', 'institutional', 'recovery')",
            name='ck_user_email_type'
        ),
        # Partial unique index to ensure only one primary email per user
        Index('idx_user_primary_email_unique', 'user_id', unique=True,
              postgresql_where="is_primary = true"),
        Index('idx_user_email_user', 'user_id'),
        Index('idx_user_email_verified', 'email', 'verified_at'),
        Index('idx_user_email_primary', 'user_id', 'is_primary'),
        {'schema': SCHEMA}
    )

    # Relationships
    user: Mapped[User] = relationship(
        "User", 
        foreign_keys=[user_id],
        back_populates="emails",
        lazy="noload"
    )

    @property
    def is_verified(self) -> bool:
        """Check if the email is verified."""
        return self.verified_at is not None

    @property
    def is_institutional(self) -> bool:
        """Check if this is an institutional email."""
        return self.email_type == 'institutional'

    def verify(self) -> None:
        """Mark the email as verified."""
        self.verified_at = now_chile()

    def set_as_primary(self) -> None:
        """Mark this email as primary (will need to unset others in the same transaction)."""
        self.is_primary = True

    def get_domain(self) -> str:
        """Extract domain from email address."""
        return self.email.split('@')[1].lower() if '@' in self.email else ''

    def __repr__(self) -> str:
        primary_flag = " (PRIMARY)" if self.is_primary else ""
        verified_flag = " ✓" if self.is_verified else ""
        return f"UserEmail(id={self.id}, email={self.email}, type={self.email_type}{primary_flag}{verified_flag})"


class Role(BaseModel):
    """Role model for the system with scope support."""

    __tablename__ = 'roles'
    __table_args__ = {'schema': SCHEMA}

    name: Mapped[str] = Column(
        String(50), 
        nullable=False,
        comment="Role name"
    )
    scope: Mapped[RoleScope] = Column(
        Enum(RoleScope, name='role_scope_enum', values_callable=lambda obj: [e.value for e in obj]),
        nullable=False,
        default=RoleScope.SYSTEM,
        server_default='SYSTEM',
        comment="Role scope (SYSTEM, TENANT, COMMUNITY)"
    )

    # Constraints
    __table_args__ = (
        UniqueConstraint('name', 'scope', name='uq_role_name_scope'),
        {'schema': SCHEMA}
    )

    # Role assignments - unified polymorphic table
    assignments: Mapped[List["RoleAssignment"]] = relationship(
        "RoleAssignment",
        back_populates="role",
        cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"Role(id={self.id}, name={self.name}, scope={self.scope})"



class UserOauthIdentity(TenantBaseModel):
    """OAuth identity model for users."""

    __tablename__ = 'user_oauth_identities'

    user_id: Mapped[PyUUID] = Column(
        UUID(as_uuid=True), 
        ForeignKey(f'{SCHEMA}.users.id', ondelete='CASCADE'), 
        nullable=False,
        comment="User ID for the OAuth identity"
    )
    provider: Mapped[str] = Column(
        String(20), 
        nullable=False, 
        comment="OAuth provider (google, etc.)"
    )
    provider_user_id: Mapped[str] = Column(
        Text, 
        nullable=False, 
        comment="User ID in the OAuth provider"
    )
    provider_email: Mapped[Optional[str]] = Column(
        CITEXT, 
        nullable=True, 
        comment="Email reported by the OAuth provider"
    )

    # OAuth tokens cifrados (seguridad mejorada)
    encrypted_access_token: Mapped[Optional[bytes]] = Column(
        LargeBinary,
        nullable=True,
        comment="OAuth access token cifrado"
    )
    encrypted_refresh_token: Mapped[Optional[bytes]] = Column(
        LargeBinary,
        nullable=True,
        comment="OAuth refresh token cifrado"
    )
    token_scope: Mapped[Optional[str]] = Column(
        Text, 
        nullable=True,
        comment="OAuth token scope"
    )
    token_expires_at: Mapped[Optional[datetime]] = Column(
        DateTime(timezone=True), 
        nullable=True,
        comment="OAuth token expiration timestamp"
    )
    token_last_rotated_at: Mapped[Optional[datetime]] = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="Última rotación de tokens"
    )

    # Constraints and schema
    __table_args__ = (
        CheckConstraint(
            "provider IN ('google')",
            name='ck_oauth_provider'
        ),
        UniqueConstraint('provider', 'provider_user_id', name='uq_provider_identity'),
        Index('idx_oauth_user', 'user_id'),
        Index('idx_oauth_provider_email', 'provider', 'provider_email'),
        {'schema': SCHEMA}
    )

    # Relationships
    user: Mapped[User] = relationship("User", back_populates="oauth_identities", lazy="noload")

    @property
    def access_token(self) -> Optional[str]:
        """Descifrar y obtener el access token."""
        if self.encrypted_access_token is None:
            return None

        from src.core.encryption import get_encryption_service
        encryption_service = get_encryption_service()
        return encryption_service.decrypt_token(self.encrypted_access_token)

    @property
    def refresh_token(self) -> Optional[str]:
        """Descifrar y obtener el refresh token."""
        if self.encrypted_refresh_token is None:
            return None

        from src.core.encryption import get_encryption_service
        encryption_service = get_encryption_service()
        return encryption_service.decrypt_token(self.encrypted_refresh_token)

    def __repr__(self) -> str:
        return f"UserOauthIdentity(id={self.id}, provider={self.provider}, provider_user_id={self.provider_user_id})"


class UserSession(TenantBaseModel):
    """User session model for token management and security."""

    __tablename__ = 'user_sessions'

    # Constraints y schema mejorados
    __table_args__ = (
        # Índice único para el hash del access token (crítico para lookup)
        Index('idx_user_session_access_token', 'access_token_hash', unique=True),
        # Índice compuesto para sesiones activas por usuario
        Index('idx_user_session_user_active', 'user_id', 'is_active'),
        # Índice para tenant y sesiones activas
        Index('idx_user_session_tenant_active', 'tenant_id', 'is_active'),
        # Índice para cleanup de sesiones expiradas
        Index('idx_user_session_expires', 'expires_at'),
        {'schema': SCHEMA}
    )

    user_id: Mapped[PyUUID] = Column(
        UUID(as_uuid=True), 
        ForeignKey(f'{SCHEMA}.users.id', ondelete='CASCADE'), 
        nullable=False,
        comment="User ID for the session"
    )
    access_token_hash: Mapped[str] = Column(
        Text, 
        nullable=False, 
        comment="SHA256 hash of the access token"
    )
    refresh_token_hash: Mapped[Optional[str]] = Column(
        Text, 
        nullable=True, 
        comment="SHA256 hash of the refresh token"
    )
    expires_at: Mapped[datetime] = Column(
        DateTime(timezone=True), 
        nullable=False,
        comment="Session expiration timestamp"
    )
    user_agent: Mapped[Optional[str]] = Column(
        Text, 
        nullable=True,
        comment="Client user agent string"
    )
    is_active: Mapped[bool] = Column(
        Boolean, 
        nullable=False, 
        default=True,
        server_default='true',
        comment="Whether the session is active"
    )
    revoked_at: Mapped[Optional[datetime]] = Column(
        DateTime(timezone=True), 
        nullable=True,
        comment="Timestamp when session was revoked"
    )
    last_used_at: Mapped[Optional[datetime]] = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="Timestamp of last session usage"
    )
    device_id: Mapped[Optional[str]] = Column(
        Text,
        nullable=True,
        comment="Device identifier"
    )

    # Relationships
    user: Mapped[User] = relationship("User", back_populates="sessions", lazy="noload")

    def is_expired(self) -> bool:
        """Check if the session has expired."""
        return now_chile() > self.expires_at

    def is_valid(self) -> bool:
        """Check if the session is valid (active and not expired)."""
        return self.is_active and not self.is_expired()

    def revoke(self) -> None:
        """Revoke the session."""
        self.is_active = False
        self.revoked_at = now_chile()

    def __repr__(self) -> str:
        return f"UserSession(id={self.id}, user_id={self.user_id}, is_active={self.is_active})"


class AuthenticationLog(TenantBaseModel):
    """Tabla robusta para logging de autenticaciones con contexto de seguridad."""

    __tablename__ = 'authentication_log'

    # Referencias principales
    user_id: Mapped[Optional[PyUUID]] = Column(
        UUID(as_uuid=True), 
        ForeignKey(f'{SCHEMA}.users.id', ondelete='SET NULL'), 
        nullable=True,
        comment="ID del usuario (NULL si no se pudo identificar)"
    )
    user_session_id: Mapped[Optional[PyUUID]] = Column(
        UUID(as_uuid=True), 
        ForeignKey(f'{SCHEMA}.user_sessions.id', ondelete='SET NULL'), 
        nullable=True,
        comment="ID de sesión creada en caso de éxito"
    )

    # Datos de autenticación
    email: Mapped[Optional[str]] = Column(
        CITEXT, 
        nullable=True,
        comment="Email utilizado en el intento (puede no existir como usuario)"
    )
    provider: Mapped[AuthProvider] = Column(
        Enum(AuthProvider, name='auth_provider_enum', values_callable=lambda obj: [e.value for e in obj]),
        nullable=False,
        comment="Proveedor de autenticación (local, google, magic_link)"
    )
    method: Mapped[AuthMethod] = Column(
        Enum(AuthMethod, name='auth_method_enum', values_callable=lambda obj: [e.value for e in obj]),
        nullable=False,
        comment="Método de autenticación (password, oauth, magic_link)"
    )
    result: Mapped[AuthResult] = Column(
        Enum(AuthResult, name='auth_result_enum', values_callable=lambda obj: [e.value for e in obj]),
        nullable=False,
        comment="Resultado del intento (SUCCESS, FAIL)"
    )

    # Contexto de fallo
    failure_reason: Mapped[Optional[AuthFailureReason]] = Column(
        Enum(AuthFailureReason, name='auth_failure_reason_enum', values_callable=lambda obj: [e.value for e in obj]),
        nullable=True,
        comment="Razón específica del fallo"
    )
    error_code: Mapped[Optional[str]] = Column(
        Text, 
        nullable=True,
        comment="Código de error interno del sistema"
    )

    # Contexto de seguridad
    mfa_used: Mapped[bool] = Column(
        Boolean, 
        nullable=False, 
        default=False,
        server_default='false',
        comment="Si se utilizó autenticación multifactor"
    )

    # Contexto técnico
    user_agent: Mapped[Optional[str]] = Column(
        Text, 
        nullable=True,
        comment="User Agent del navegador/cliente"
    )

    # Correlación
    request_id: Mapped[Optional[PyUUID]] = Column(
        UUID(as_uuid=True), 
        nullable=True,
        comment="ID de correlación con logs de aplicación"
    )

    # Constraints y schema
    __table_args__ = (
        CheckConstraint(
            "(result = 'SUCCESS' AND failure_reason IS NULL) OR (result = 'FAIL')",
            name='ck_auth_log_success_no_failure_reason'
        ),
        # Índices para consultas reales y performance
        Index('idx_authlog_user_ts', 'user_id', 'created_at'),
        Index('idx_authlog_email_ts', 'email', 'created_at'), 
        Index('idx_authlog_tenant_ts', 'tenant_id', 'created_at'),
        # Índice parcial para fallos (crítico para rate limiting)
        Index(
            'idx_authlog_fail_ts', 
            'created_at',
            postgresql_where="result = 'FAIL'"
        ),
        # Índice para búsquedas por request_id
        Index('idx_authlog_request', 'request_id'),
        {'schema': SCHEMA}
    )

    # Relationships
    user: Mapped[Optional["User"]] = relationship(
        "User", 
        foreign_keys=[user_id],
        back_populates=None,
        lazy="noload"
    )
    user_session: Mapped[Optional["UserSession"]] = relationship(
        "UserSession",
        foreign_keys=[user_session_id], 
        back_populates=None,
        lazy="noload"
    )

    def __repr__(self) -> str:
        return (f"AuthenticationLog(id={self.id}, result={self.result}, "
                f"provider={self.provider}, email={self.email})")

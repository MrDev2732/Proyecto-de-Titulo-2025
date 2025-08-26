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
    Table,
    Text,
    UniqueConstraint,
    CheckConstraint,
    Index,
    SmallInteger,
)
from sqlalchemy.dialects.postgresql import CITEXT, UUID, INET
from sqlalchemy.orm import relationship, Mapped

from src.database import SCHEMA
from src.database.models.base import BaseModel, TenantBaseModel
from src.database.enums import (
    UserStatus,
    AuthProvider,
    AuthMethod, 
    AuthResult,
    AuthFailureReason,
    RoleScope,
)
from src.database.timezone_utils import now_chile


class User(BaseModel):
    """User model for the system."""

    __tablename__ = 'users'

    # Basic fields
    email: Mapped[Optional[str]] = Column(
        CITEXT, 
        nullable=True, 
        unique=True,
        comment="User email (can be NULL for OAuth-only users)"
    )
    email_verified_at: Mapped[Optional[datetime]] = Column(
        DateTime(timezone=True), 
        nullable=True,
        comment="Email verification timestamp"
    )
    password_hash: Mapped[Optional[str]] = Column(
        Text, 
        nullable=True, 
        comment="Password hash (NULL for OAuth-only users)"
    )
    status: Mapped[UserStatus] = Column(
        Enum(UserStatus, name='user_status_enum', values_callable=lambda obj: [e.name for e in obj]),
        nullable=False,
        default=UserStatus.ACTIVE,
        server_default='ACTIVE',
        comment="User account status"
    )

    # Constraints and schema
    __table_args__ = (
        UniqueConstraint('email', name='uq_user_email'),
        {'schema': SCHEMA}
    )

    # Relationships - Solo sistema unificado
    role_assignments: Mapped[List["RoleAssignment"]] = relationship(
        "RoleAssignment",
        foreign_keys="RoleAssignment.user_id",
        back_populates="user"
    )
    oauth_identities: Mapped[List["UserOauthIdentity"]] = relationship(
        "UserOauthIdentity",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    magic_links: Mapped[List["AuthMagicLink"]] = relationship(
        "AuthMagicLink",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    # Resident relationship - using string to avoid circular import
    resident = relationship(
        "Resident",
        back_populates="user",
        uselist=False
    )
    sessions: Mapped[List["UserSession"]] = relationship(
        "UserSession",
        back_populates="user",
        cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"User(id={self.id}, email={self.email}, status={self.status})"


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
        default=RoleScope.GLOBAL,
        server_default='GLOBAL',
        comment="Role scope (GLOBAL, TENANT, COMMUNITY)"
    )

    # Constraints
    __table_args__ = (
        UniqueConstraint('name', 'scope', name='uq_role_name_scope'),
        {'schema': SCHEMA}
    )

    # Relationships - Solo sistema unificado
    role_assignments: Mapped[List["RoleAssignment"]] = relationship(
        "RoleAssignment",
        back_populates="role",
        cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"Role(id={self.id}, name={self.name}, scope={self.scope})"


class AuthMagicLink(BaseModel):
    """Magic link model for passwordless authentication."""

    __tablename__ = 'auth_magic_links'
    __table_args__ = {'schema': SCHEMA}

    user_id: Mapped[UUID] = Column(
        UUID(as_uuid=True), 
        ForeignKey(f'{SCHEMA}.users.id', ondelete='CASCADE'), 
        nullable=False,
        comment="User ID for the magic link"
    )
    token_hash: Mapped[str] = Column(
        Text, 
        nullable=False, 
        comment="Hashed authentication token"
    )
    expires_at: Mapped[datetime] = Column(
        DateTime(timezone=True), 
        nullable=False,
        comment="Magic link expiration timestamp"
    )
    used_at: Mapped[Optional[datetime]] = Column(
        DateTime(timezone=True), 
        nullable=True,
        comment="Timestamp when the link was used"
    )

    # Relationships
    user: Mapped[User] = relationship("User", back_populates="magic_links")

    def is_expired(self) -> bool:
        """Check if the magic link has expired."""
        return now_chile() > self.expires_at

    def is_used(self) -> bool:
        """Check if the magic link has been used."""
        return self.used_at is not None

    def is_valid(self) -> bool:
        """Check if the magic link is valid (not expired and not used)."""
        return not self.is_expired() and not self.is_used()

    def __repr__(self) -> str:
        return f"AuthMagicLink(id={self.id}, user_id={self.user_id}, expires_at={self.expires_at})"


class UserOauthIdentity(TenantBaseModel):
    """OAuth identity model for users."""

    __tablename__ = 'user_oauth_identities'

    user_id: Mapped[UUID] = Column(
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

    # OAuth tokens (optional)
    access_token: Mapped[Optional[str]] = Column(
        Text, 
        nullable=True,
        comment="OAuth access token"
    )
    refresh_token: Mapped[Optional[str]] = Column(
        Text, 
        nullable=True,
        comment="OAuth refresh token"
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
    user: Mapped[User] = relationship("User", back_populates="oauth_identities")


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
        # Índice para análisis de IP
        Index('idx_user_session_ip_created', 'ip_address', 'created_at'),
        {'schema': SCHEMA}
    )

    user_id: Mapped[UUID] = Column(
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
    ip_address: Mapped[Optional[str]] = Column(
        String(45), 
        nullable=True,
        comment="Client IP address (IPv4 or IPv6)"
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

    # Relationships
    user: Mapped[User] = relationship("User", back_populates="sessions")

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
    risk_score: Mapped[Optional[int]] = Column(
        SmallInteger,
        nullable=True,
        comment="Puntuación de riesgo calculada (0-100)"
    )

    # Contexto técnico
    ip: Mapped[Optional[str]] = Column(
        INET, 
        nullable=True,
        comment="Dirección IP del cliente"
    )
    user_agent: Mapped[Optional[str]] = Column(
        Text, 
        nullable=True,
        comment="User Agent del navegador/cliente"
    )
    geo_country: Mapped[Optional[str]] = Column(
        String(2), 
        nullable=True,
        comment="Código de país ISO-3166 alpha-2"
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
            "risk_score IS NULL OR (risk_score >= 0 AND risk_score <= 100)",
            name='ck_auth_log_risk_score_range'
        ),
        CheckConstraint(
            "geo_country IS NULL OR length(geo_country) = 2",
            name='ck_auth_log_geo_country_format'
        ),
        CheckConstraint(
            "(result = 'SUCCESS' AND failure_reason IS NULL) OR (result = 'FAIL')",
            name='ck_auth_log_success_no_failure_reason'
        ),
        # Índices para consultas reales y performance
        Index('idx_authlog_user_ts', 'user_id', 'created_at'),
        Index('idx_authlog_email_ts', 'email', 'created_at'), 
        Index('idx_authlog_ip_ts', 'ip', 'created_at'),
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
        back_populates=None  # No necesitamos relación bidireccional
    )
    user_session: Mapped[Optional["UserSession"]] = relationship(
        "UserSession",
        foreign_keys=[user_session_id], 
        back_populates=None  # No necesitamos relación bidireccional
    )

    def __repr__(self) -> str:
        return (f"AuthenticationLog(id={self.id}, result={self.result}, "
                f"provider={self.provider}, email={self.email}, ip={self.ip})")


class RoleAssignment(BaseModel):
    """Unified role assignment model - single source of truth for all role assignments."""

    __tablename__ = 'role_assignments'

    role_id: Mapped[PyUUID] = Column(
        UUID(as_uuid=True), 
        ForeignKey(f'{SCHEMA}.roles.id', ondelete='CASCADE'), 
        nullable=False,
        comment="Role ID"
    )
    user_id: Mapped[PyUUID] = Column(
        UUID(as_uuid=True), 
        ForeignKey(f'{SCHEMA}.users.id', ondelete='CASCADE'), 
        nullable=False,
        comment="User ID"
    )
    tenant_id: Mapped[Optional[PyUUID]] = Column(
        UUID(as_uuid=True), 
        ForeignKey(f'{SCHEMA}.tenants.id', ondelete='CASCADE'), 
        nullable=True,
        comment="Tenant ID (for TENANT scope roles)"
    )
    community_id: Mapped[Optional[PyUUID]] = Column(
        UUID(as_uuid=True), 
        ForeignKey(f'{SCHEMA}.communities.id', ondelete='CASCADE'), 
        nullable=True,
        comment="Community ID (for COMMUNITY scope roles)"
    )

    # Constraints and schema
    __table_args__ = (
        # Unique assignment per role/user/context
        UniqueConstraint('role_id', 'user_id', 'tenant_id', 'community_id', name='uq_role_assignment'),

        # Indexes for performance
        Index('idx_roleass_user', 'user_id'),
        Index('idx_roleass_tenant', 'tenant_id'),
        Index('idx_roleass_community', 'community_id'),
        Index('idx_roleass_role', 'role_id'),
        
        {'schema': SCHEMA}
    )

    # Relationships
    role: Mapped[Role] = relationship("Role", back_populates="role_assignments")
    user: Mapped[User] = relationship("User", back_populates="role_assignments")
    tenant: Mapped[Optional["Tenant"]] = relationship(
        "Tenant", 
        foreign_keys=[tenant_id]
    )
    community: Mapped[Optional["Community"]] = relationship(
        "Community", 
        foreign_keys=[community_id]
    )

    def __repr__(self) -> str:
        context = ""
        if self.tenant_id:
            context += f", tenant_id={self.tenant_id}"
        if self.community_id:
            context += f", community_id={self.community_id}"
        return f"RoleAssignment(id={self.id}, role_id={self.role_id}, user_id={self.user_id}{context})"

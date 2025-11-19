from datetime import datetime, timedelta
from typing import Any, Dict, Optional
from uuid import UUID as PyUUID
import hashlib
import secrets
import string

from sqlalchemy import (
    Column,
    ForeignKey,
    String,
    Text,
    Integer,
    CheckConstraint,
    Index,
    LargeBinary
)
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import UUID, JSONB, TIMESTAMP
from sqlalchemy.orm import relationship, Mapped, foreign

from src.database import SCHEMA
from src.database.models.base import BaseModel, SoftDeleteBaseModel
from src.database.enums import NotificationStatus
from src.database.utils import now_chile


class Tenant(SoftDeleteBaseModel):
    """Tenant model for multi-tenancy support."""

    __tablename__ = 'tenants'
    __table_args__ = {'schema': SCHEMA}

    name: Mapped[str] = Column(
        Text, 
        nullable=False,
        comment="Tenant name"
    )
    domain: Mapped[Optional[str]] = Column(
        Text, 
        nullable=True,
        comment="Email domain for institutional emails (e.g., 'recoleta.cl')"
    )

    # Relationships
    # Role assignments for this tenant (unified table)
    role_assignments = relationship(
        "RoleAssignment",
        primaryjoin="and_(Tenant.id == foreign(RoleAssignment.scope_id), RoleAssignment.scope_type == 'tenant')",
        viewonly=True
    )

    # Only include created_at (inherited from BaseModel),
    # not updated_at as in the original SQL
    def __init__(self, **kwargs):
        # Remove updated_at if passed, as this model doesn't need it
        kwargs.pop('updated_at', None)
        super().__init__(**kwargs)

    def __repr__(self) -> str:
        return f"Tenant(id={self.id}, name={self.name})"


class Outbox(BaseModel):
    """
    Transactional outbox model for notifications.

    IMPORTANT: This table can grow rapidly. Implement cleanup processes:

    1. TTL Cleanup (recommended):
       DELETE FROM outbox 
       WHERE status = 'processed' 
       AND processed_at < now() - interval '30 days';

    2. Archival Strategy:
       Move old processed records to outbox_archive table

    3. Partitioning (for high volume):
       Partition by created_at (monthly/weekly)
    """

    __tablename__ = 'outbox'

    type: Mapped[str] = Column(
        Text, 
        nullable=False, 
        comment="Message type: email, whatsapp, webhook, etc."
    )
    payload: Mapped[Dict[str, Any]] = Column(
        JSONB, 
        nullable=False, 
        comment="Message data"
    )
    status: Mapped[str] = Column(
        Text, 
        nullable=False, 
        default='pending',
        server_default='pending',
        comment="Processing status: pending, processing, processed, failed"
    )
    attempts: Mapped[int] = Column(
        Integer, 
        nullable=False, 
        default=0, 
        server_default='0',
        comment="Number of delivery attempts"
    )
    max_attempts: Mapped[int] = Column(
        Integer, 
        nullable=False, 
        default=3,
        server_default='3',
        comment="Maximum delivery attempts before marking as failed"
    )
    next_attempt_at: Mapped[Optional[datetime]] = Column(
        TIMESTAMP(timezone=True),
        nullable=True,
        comment="Next delivery attempt timestamp"
    )
    processed_at: Mapped[Optional[datetime]] = Column(
        TIMESTAMP(timezone=True),
        nullable=True,
        comment="Timestamp when successfully processed"
    )
    dedupe_key: Mapped[Optional[str]] = Column(
        Text,
        nullable=True,
        comment="Deduplication key for idempotency"
    )
    last_error: Mapped[Optional[str]] = Column(
        Text, 
        nullable=True,
        comment="Last error message"
    )

    # Constraints and schema
    __table_args__ = (
        CheckConstraint("jsonb_typeof(payload) = 'object'", name='ck_outbox_payload_object'),
        CheckConstraint("payload ? 'to'", name='ck_outbox_payload_has_to'),
        CheckConstraint(
            "status IN ('pending', 'processing', 'processed', 'failed')",
            name='ck_outbox_status'
        ),
        CheckConstraint("attempts <= max_attempts", name='ck_outbox_attempts_limit'),
        # Index for worker polling (critical for performance)
        Index('idx_outbox_pending', 'status', 'next_attempt_at', 
              postgresql_where="status IN ('pending', 'failed')"),
        # Index for cleanup operations (TTL)
        Index('idx_outbox_cleanup', 'status', 'processed_at',
              postgresql_where="status = 'processed'"),
        # Index for monitoring and debugging
        Index('idx_outbox_type_status', 'type', 'status', 'created_at'),
        # Index for deduplication
        Index('idx_outbox_dedupe', 'type', 'dedupe_key', unique=True,
              postgresql_where="dedupe_key IS NOT NULL"),
        {'schema': SCHEMA}
    )

    def is_pending(self) -> bool:
        """Check if the message is pending processing."""
        return self.status == 'pending'

    def is_processed(self) -> bool:
        """Check if the message was successfully processed."""
        return self.status == 'processed'

    def is_failed(self) -> bool:
        """Check if the message failed after max attempts."""
        return self.status == 'failed'

    def can_retry(self) -> bool:
        """Check if the message can be retried."""
        return self.attempts < self.max_attempts and self.status in ('pending', 'failed')

    def mark_processed(self) -> None:
        """Mark the message as successfully processed."""
        self.status = 'processed'
        self.processed_at = now_chile()

    def mark_failed(self, error_message: str) -> None:
        """Mark the message as failed with error details."""
        self.status = 'failed'
        self.last_error = error_message
        self.attempts += 1

    def __repr__(self) -> str:
        return f"Outbox(id={self.id}, type={self.type}, status={self.status}, attempts={self.attempts})"


class NotificationLog(BaseModel):
    """Notification delivery log model."""

    __tablename__ = 'notification_logs'

    # Trazabilidad con outbox
    outbox_id: Mapped[Optional[PyUUID]] = Column(
        UUID(as_uuid=True), 
        ForeignKey(f'{SCHEMA}.outbox.id', ondelete='SET NULL'), 
        nullable=True,
        comment="Outbox event that originated this notification"
    )

    type: Mapped[str] = Column(
        Text, 
        nullable=False,
        comment="Notification type"
    )
    destination: Mapped[str] = Column(
        Text, 
        nullable=False, 
        comment="Destination (email, phone, etc.)"
    )
    status: Mapped[str] = Column(
        String(20), 
        nullable=False,
        comment="Delivery status"
    )
    provider_message_id: Mapped[Optional[str]] = Column(
        Text,
        nullable=True,
        comment="Provider's message ID for tracking"
    )
    payload_snapshot: Mapped[Optional[dict]] = Column(
        JSONB,
        nullable=True,
        comment="Snapshot of the payload at delivery time"
    )

    # Constraints and schema
    __table_args__ = (
        CheckConstraint(
            f"status IN ('{NotificationStatus.SENT}', '{NotificationStatus.FAILED}')",
            name='ck_notification_log_status'
        ),
        Index('idx_notification_log_outbox', 'outbox_id'),
        Index('idx_notification_log_destination_created', 'destination', 'created_at'),
        Index('idx_notification_log_provider_msg', 'provider_message_id'),
        {'schema': SCHEMA}
    )

    # Relationships
    outbox: Mapped[Optional["Outbox"]] = relationship("Outbox", foreign_keys=[outbox_id], lazy="noload")

    def __repr__(self) -> str:
        return f"NotificationLog(id={self.id}, type={self.type}, destination={self.destination}, status={self.status})"


class AuditLog(BaseModel):
    """System audit log model."""

    __tablename__ = 'audit_logs'

    # Actor who performed the action
    actor_id: Mapped[Optional[PyUUID]] = Column(
        UUID(as_uuid=True), 
        ForeignKey(f'{SCHEMA}.users.id', ondelete='SET NULL'), 
        nullable=True,
        comment="User ID who performed the action"
    )

    # Action information
    action: Mapped[str] = Column(
        Text, 
        nullable=False, 
        comment="Action performed"
    )
    entity: Mapped[str] = Column(
        Text, 
        nullable=False, 
        comment="Type of entity affected"
    )
    entity_id: Mapped[PyUUID] = Column(
        UUID(as_uuid=True), 
        nullable=False, 
        comment="ID of the affected entity"
    )

    # Contextual information
    occurred_at: Mapped[datetime] = Column(
        TIMESTAMP(timezone=True),
        nullable=False, 
        default=now_chile,
        server_default=func.now(),
        comment="Action timestamp"
    )
    actor_type: Mapped[Optional[str]] = Column(
        String(20),
        nullable=True,
        comment="Type of actor: user, system"
    )
    request_id: Mapped[Optional[PyUUID]] = Column(
        UUID(as_uuid=True),
        nullable=True,
        comment="Request correlation ID"
    )
    extra_data: Mapped[Optional[Dict[str, Any]]] = Column(
        JSONB, 
        nullable=True, 
        comment="Additional action metadata"
    )

    # Indexes and schema
    __table_args__ = (
        CheckConstraint(
            "actor_type IS NULL OR actor_type IN ('user', 'system')",
            name='ck_audit_log_actor_type'
        ),
        Index('idx_audit_entity', 'entity', 'entity_id', 'occurred_at'),
        Index('idx_audit_actor', 'actor_id', 'occurred_at'),
        Index('idx_audit_request', 'request_id'),
        {'schema': SCHEMA}
    )

    # Relationships
    actor: Mapped[Optional["User"]] = relationship("User", foreign_keys=[actor_id], lazy="noload")

    def __repr__(self) -> str:
        return f"AuditLog(id={self.id}, action={self.action}, entity={self.entity}, occurred_at={self.occurred_at})"


class PasswordResetToken(BaseModel):
    __tablename__ = 'password_reset_tokens'

    # Usuario asociado
    user_id: Mapped[PyUUID] = Column(
        UUID(as_uuid=True), 
        ForeignKey(f'{SCHEMA}.users.id', ondelete='CASCADE'), 
        nullable=False,
        comment="Usuario que solicita el reset"
    )

    # Código de 6 dígitos y token hash para seguridad
    code: Mapped[str] = Column(
        Text,
        nullable=False,
        comment="Código de 6 dígitos para validación"
    )
    token: Mapped[str] = Column(
        Text,
        nullable=False,
        comment="Token para URLs de reset"
    )
    token_hash: Mapped[bytes] = Column(
        LargeBinary,
        nullable=False,
        unique=True,
        comment="Hash del token para validación segura"
    )

    # Control de expiración y uso
    expires_at: Mapped[datetime] = Column(
        TIMESTAMP(timezone=True),
        nullable=False,
        comment="Fecha y hora de expiración del token"
    )
    consumed_at: Mapped[Optional[datetime]] = Column(
        TIMESTAMP(timezone=True),
        nullable=True,
        comment="Fecha y hora cuando se consumió el token"
    )

    # Metadatos adicionales
    user_agent: Mapped[Optional[str]] = Column(
        Text, 
        nullable=True,
        comment="User agent del navegador que solicitó el reset"
    )

    # Constraints e índices
    __table_args__ = (
        # Índice para búsquedas por token hash
        Index('idx_password_reset_token_hash', 'token_hash'),
        # Índice para cleanup de tokens expirados
        Index('idx_password_reset_expires', 'expires_at'),
        # Índice para búsquedas por usuario
        Index('idx_password_reset_user', 'user_id', 'created_at'),
        {'schema': SCHEMA}
    )

    # Relationships
    user: Mapped["User"] = relationship("User", foreign_keys=[user_id], lazy="noload")

    @classmethod
    def generate_code(cls) -> str:
        """Generar código de 6 dígitos único."""
        return ''.join(secrets.choice(string.digits) for _ in range(6))

    @classmethod
    def generate_token(cls) -> str:
        """Generar token seguro de 64 caracteres."""
        return secrets.token_urlsafe(48)  # 48 bytes = 64 chars en base64url

    @classmethod
    def create_for_user(
        cls, 
        user_id: PyUUID, 
        expires_in_minutes: int = 15,
        user_agent: Optional[str] = None,
        custom_code: Optional[str] = None
    ) -> "PasswordResetToken":
        """
        Crear nuevo token de reset para un usuario.

        Args:
            user_id: ID del usuario
            expires_in_minutes: Minutos hasta expiración (default: 15)
            user_agent: User agent del navegador
            custom_code: Código personalizado (opcional, para testing/bypass)

        Returns:
            Nueva instancia de PasswordResetToken
        """
        now = now_chile()
        expires_at = now + timedelta(minutes=expires_in_minutes)
        token = cls.generate_token()

        return cls(
            user_id=user_id,
            code=custom_code if custom_code else cls.generate_code(),
            token=token,
            token_hash=hashlib.sha256(token.encode()).digest(),
            expires_at=expires_at,
            user_agent=user_agent
        )

    def is_valid(self) -> bool:
        """Verificar si el token es válido (no consumido y no expirado)."""
        now = now_chile()
        return self.consumed_at is None and self.expires_at > now

    def is_expired(self) -> bool:
        """Verificar si el token ha expirado."""
        return now_chile() > self.expires_at

    def mark_as_consumed(self) -> None:
        """Marcar el token como consumido."""
        self.consumed_at = now_chile()

    def time_until_expiry(self) -> Optional[timedelta]:
        """Obtener tiempo restante hasta expiración."""
        if self.is_expired():
            return None
        return self.expires_at - now_chile()

    def __repr__(self) -> str:
        return f"PasswordResetToken(id={self.id}, user_id={self.user_id}, consumed={self.consumed_at is not None}, expires_at={self.expires_at})"

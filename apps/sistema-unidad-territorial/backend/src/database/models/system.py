from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID as PyUUID

from sqlalchemy import (
    Column,
    ForeignKey,
    String,
    Text,
    Integer,
    DateTime, 
    CheckConstraint,
    Index
)
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import UUID, JSONB, INET
from sqlalchemy.orm import relationship, Mapped

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
        DateTime(timezone=True), 
        nullable=True,
        comment="Next delivery attempt timestamp"
    )
    processed_at: Mapped[Optional[datetime]] = Column(
        DateTime(timezone=True), 
        nullable=True,
        comment="Timestamp when successfully processed"
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

    # Constraints and schema
    __table_args__ = (
        CheckConstraint(
            f"status IN ('{NotificationStatus.SENT}', '{NotificationStatus.FAILED}')",
            name='ck_notification_log_status'
        ),
        Index('idx_notification_log_outbox', 'outbox_id'),
        Index('idx_notification_log_destination_created', 'destination', 'created_at'),
        {'schema': SCHEMA}
    )

    # Relationships
    outbox: Mapped[Optional["Outbox"]] = relationship("Outbox", foreign_keys=[outbox_id])

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
    ip_address: Mapped[Optional[str]] = Column(
        INET, 
        nullable=True, 
        comment="IP address of the actor"
    )
    timestamp: Mapped[datetime] = Column(
        DateTime(timezone=True), 
        nullable=False, 
        default=now_chile,
        server_default=func.now(),
        comment="Action timestamp"
    )
    extra_data: Mapped[Optional[Dict[str, Any]]] = Column(
        JSONB, 
        nullable=True, 
        comment="Additional action metadata"
    )

    # Indexes and schema
    __table_args__ = (
        Index('idx_audit_entity', 'entity', 'entity_id', 'timestamp'),
        Index('idx_audit_actor', 'actor_id', 'timestamp'),
        {'schema': SCHEMA}
    )

    # Relationships
    actor: Mapped[Optional["User"]] = relationship("User", foreign_keys=[actor_id])

    def __repr__(self) -> str:
        return f"AuditLog(id={self.id}, action={self.action}, entity={self.entity}, timestamp={self.timestamp})"

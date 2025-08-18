from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from sqlalchemy import (
    Column, ForeignKey, String, Text, Integer, DateTime, 
    CheckConstraint, Index, text
)
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import UUID, JSONB, INET
from sqlalchemy.orm import relationship, Mapped

from src.database import SCHEMA
from src.database.models.base import BaseModel
from src.database.enums import NotificationStatus, NotificationType
from src.database.timezone_utils import now_chile


class Tenant(BaseModel):
    """Tenant model for multi-tenancy support."""

    __tablename__ = 'tenants'
    __table_args__ = {'schema': SCHEMA}

    name: Mapped[str] = Column(
        Text, 
        nullable=False,
        comment="Tenant name"
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
    """Transactional outbox model for notifications."""

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
    attempts: Mapped[int] = Column(
        Integer, 
        nullable=False, 
        default=0, 
        server_default='0',
        comment="Number of delivery attempts"
    )
    next_attempt_at: Mapped[Optional[datetime]] = Column(
        DateTime(timezone=True), 
        nullable=True,
        comment="Next delivery attempt timestamp"
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
        Index('idx_outbox_pull', 'next_attempt_at', 'type'),
        {'schema': SCHEMA}
    )

    def __repr__(self) -> str:
        return f"Outbox(id={self.id}, type={self.type}, attempts={self.attempts})"


class NotificationLog(BaseModel):
    """Notification delivery log model."""

    __tablename__ = 'notification_logs'

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
        {'schema': SCHEMA}
    )

    def __repr__(self) -> str:
        return f"NotificationLog(id={self.id}, type={self.type}, destination={self.destination}, status={self.status})"


class AuditLog(BaseModel):
    """System audit log model."""

    __tablename__ = 'audit_logs'

    # Actor who performed the action
    actor_id: Mapped[Optional[UUID]] = Column(
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
    entity_id: Mapped[UUID] = Column(
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

from datetime import datetime
from typing import Optional

from sqlalchemy import Column, Text, CheckConstraint, Index
from sqlalchemy.orm import Mapped

from sqlalchemy.dialects.postgresql import TIMESTAMP

from src.database import SCHEMA
from src.database.models.base import TenantSoftDeleteModel
from src.database.utils import now_chile


class News(TenantSoftDeleteModel):
    """News or public announcement model."""

    __tablename__ = 'news'

    # Content
    title: Mapped[str] = Column(
        Text, 
        nullable=False,
        comment="News title"
    )
    body: Mapped[str] = Column(
        Text, 
        nullable=False,
        comment="News content"
    )

    # Temporal visibility control
    visible_from: Mapped[datetime] = Column(
        TIMESTAMP(timezone=True), 
        nullable=False,
        comment="Start of visibility period"
    )
    visible_until: Mapped[Optional[datetime]] = Column(
        TIMESTAMP(timezone=True), 
        nullable=True,
        comment="End of visibility period (optional)"
    )

    # Constraints and schema
    __table_args__ = (
        CheckConstraint(
            'visible_until IS NULL OR visible_until > visible_from',
            name='ck_news_valid_dates'
        ),
        # Composite index for visibility queries - optimizes range queries
        Index('idx_news_visibility', 'visible_from', 'visible_until'),
        # Index for tenant-specific active news queries
        Index('idx_news_tenant_active', 'tenant_id', 'visible_from', 'visible_until'),
        # Index for ordering by creation date
        Index('idx_news_created', 'created_at'),
        {'schema': SCHEMA}
    )

    def is_active(self, check_date: Optional[datetime] = None) -> bool:
        """
        Check if the news is active at a specific date.

        Args:
            check_date: Date to check. If None, uses current Chile time.

        Returns:
            True if the news is active, False otherwise
        """
        if check_date is None:
            check_date = now_chile()

        # Check if the date is within the visibility range
        if check_date < self.visible_from:
            return False

        if self.visible_until is not None and check_date > self.visible_until:
            return False

        return True

    def __repr__(self) -> str:
        status = "active" if self.is_active() else "inactive"
        title_preview = self.title[:50] + "..." if len(self.title) > 50 else self.title
        return f"News(id={self.id}, title={title_preview}, status={status})"

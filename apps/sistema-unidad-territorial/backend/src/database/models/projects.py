from typing import List, Optional
from uuid import UUID as PyUUID

from sqlalchemy import (
    Column,
    ForeignKey,
    String,
    Text,
    CheckConstraint,
    Index
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, Mapped

from src.database import SCHEMA
from src.database.models.base import BaseModel
from src.database.enums import ProjectStatus


class Project(BaseModel):
    """Community project model."""

    __tablename__ = 'projects'

    # Relationships
    community_id: Mapped[PyUUID] = Column(
        UUID(as_uuid=True), 
        ForeignKey(f'{SCHEMA}.communities.id', ondelete='CASCADE'), 
        nullable=False,
        comment="Community ID where the project is proposed"
    )
    requesting_user_id: Mapped[PyUUID] = Column(
        UUID(as_uuid=True), 
        ForeignKey(f'{SCHEMA}.users.id', ondelete='RESTRICT'), 
        nullable=False,
        comment="User ID who requested the project"
    )

    # Project information
    title: Mapped[str] = Column(
        Text, 
        nullable=False,
        comment="Project title"
    )
    description: Mapped[str] = Column(
        Text, 
        nullable=False,
        comment="Project description"
    )
    status: Mapped[str] = Column(
        String(20), 
        nullable=False,
        comment="Project status"
    )
    observations: Mapped[Optional[str]] = Column(
        Text, 
        nullable=True,
        comment="Project observations or notes"
    )

    # Constraints and schema
    __table_args__ = (
        CheckConstraint(
            f"status IN ('{ProjectStatus.PENDING}', "
            f"'{ProjectStatus.IN_PROGRESS}', "
            f"'{ProjectStatus.COMPLETED}', "
            f"'{ProjectStatus.REJECTED}')",
            name='ck_project_status'
        ),
        Index('idx_project_status_created', 'status', 'created_at'),
        Index('idx_project_community', 'community_id'),
        Index('idx_project_user', 'requesting_user_id'),
        {'schema': SCHEMA}
    )

    # Relationships
    community: Mapped["Community"] = relationship("Community", foreign_keys=[community_id])
    requesting_user: Mapped["User"] = relationship("User", foreign_keys=[requesting_user_id])
    attachments: Mapped[List["ProjectAttachment"]] = relationship(
        "ProjectAttachment",
        back_populates="project",
        cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        title_preview = self.title[:50] + "..." if len(self.title) > 50 else self.title
        return f"Project(id={self.id}, title={title_preview}, status={self.status})"


class ProjectAttachment(BaseModel):
    """Project attachment model."""

    __tablename__ = 'project_attachments'

    # Relationships
    project_id: Mapped[PyUUID] = Column(
        UUID(as_uuid=True), 
        ForeignKey(f'{SCHEMA}.projects.id', ondelete='CASCADE'), 
        nullable=False,
        comment="Project ID for the attachment"
    )

    # Attachment information
    url: Mapped[str] = Column(
        Text, 
        nullable=False, 
        comment="URL of the attachment file"
    )
    type: Mapped[str] = Column(
        Text, 
        nullable=False, 
        comment="Type of the attachment file"
    )

    # Constraints and schema
    __table_args__ = {'schema': SCHEMA}

    # Relationships
    project: Mapped[Project] = relationship("Project", back_populates="attachments")

    def __repr__(self) -> str:
        return f"ProjectAttachment(id={self.id}, project_id={self.project_id}, type={self.type})"

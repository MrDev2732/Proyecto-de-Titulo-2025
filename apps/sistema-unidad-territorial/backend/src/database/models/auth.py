from datetime import datetime
from typing import List, Optional

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    String,
    Table,
    Text,
    UniqueConstraint,
    CheckConstraint,
    Index,
)
from sqlalchemy.dialects.postgresql import CITEXT, UUID
from sqlalchemy.orm import relationship, Mapped

from src.database import SCHEMA
from src.database.models.base import BaseModel
from src.database.enums import UserStatus, OAuthProvider
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
    status: Mapped[str] = Column(
        String(20),
        nullable=False,
        default=UserStatus.ACTIVE,
        server_default=f"'{UserStatus.ACTIVE}'",
        comment="User account status"
    )

    # Constraints and schema
    __table_args__ = (
        CheckConstraint(
            f"status IN ('{UserStatus.ACTIVE}', '{UserStatus.INACTIVE}', '{UserStatus.BLOCKED}')",
            name='ck_user_status'
        ),
        UniqueConstraint('email', name='uq_user_email'),
        {'schema': SCHEMA}
    )

    # Relationships
    roles: Mapped[List["Role"]] = relationship(
        "Role", 
        secondary="user_roles", 
        back_populates="users",
        lazy="selectin"
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

    def __repr__(self) -> str:
        return f"User(id={self.id}, email={self.email}, status={self.status})"


class Role(BaseModel):
    """Role model for the system."""

    __tablename__ = 'roles'
    __table_args__ = {'schema': SCHEMA}

    name: Mapped[str] = Column(
        String(50), 
        nullable=False, 
        unique=True,
        comment="Role name"
    )

    # Relationships
    users: Mapped[List[User]] = relationship(
        User,
        secondary="user_roles",
        back_populates="roles",
        lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"Role(id={self.id}, name={self.name})"


# Many-to-many association table for User and Role
user_roles_table = Table(
    'user_roles',
    BaseModel.metadata,
    Column('user_id', UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), primary_key=True),
    Column('role_id', UUID(as_uuid=True), ForeignKey('roles.id', ondelete='CASCADE'), primary_key=True),
    schema=SCHEMA
)


class AuthMagicLink(BaseModel):
    """Magic link model for passwordless authentication."""

    __tablename__ = 'auth_magic_links'
    __table_args__ = {'schema': SCHEMA}

    user_id: Mapped[UUID] = Column(
        UUID(as_uuid=True), 
        ForeignKey('users.id', ondelete='CASCADE'), 
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


class UserOauthIdentity(BaseModel):
    """OAuth identity model for users."""

    __tablename__ = 'user_oauth_identities'

    user_id: Mapped[UUID] = Column(
        UUID(as_uuid=True), 
        ForeignKey('users.id', ondelete='CASCADE'), 
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
            f"provider IN ('{OAuthProvider.GOOGLE}')",
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

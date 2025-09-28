from typing import Any, Dict, Optional
from uuid import UUID as PyUUID, uuid4
from datetime import datetime

from sqlalchemy import Column, DateTime, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.orm import Mapped
from sqlalchemy.sql import func

from src.database import Base
from src.database.utils import now_chile


class UUIDMixin:
    """Mixin that provides a UUID primary key."""

    @declared_attr
    def id(cls) -> Mapped[PyUUID]:
        return Column(
            UUID(as_uuid=True),
            primary_key=True,
            default=uuid4,
            server_default=text("uuid_generate_v4()"),
            comment="Primary key UUID"
        )


class TimestampMixin:
    """Mixin that provides creation and update timestamps using Chile timezone."""

    @declared_attr
    def created_at(cls) -> Mapped[datetime]:
        return Column(
            DateTime(timezone=True),
            nullable=False,
            default=now_chile,
            server_default=func.now(),
            comment="Creation timestamp in Chile timezone"
        )

    @declared_attr
    def updated_at(cls) -> Mapped[datetime]:
        return Column(
            DateTime(timezone=True),
            nullable=False,
            default=now_chile,
            onupdate=now_chile,
            server_default=func.now(),
            comment="Last update timestamp in Chile timezone"
        )


class TenantMixin:
    """Mixin that provides multi-tenant support."""

    @declared_attr
    def tenant_id(cls) -> Mapped[Optional[PyUUID]]:
        return Column(
            UUID(as_uuid=True),
            nullable=True,
            index=True,
            comment="Tenant ID for multi-tenancy support"
        )


class SoftDeleteMixin:
    """Mixin that provides soft delete functionality."""

    @declared_attr
    def deleted_at(cls) -> Mapped[Optional[datetime]]:
        return Column(
            DateTime(timezone=True),
            nullable=True,
            index=True,
            comment="Soft delete timestamp - NULL means active"
        )

    @property
    def is_deleted(self) -> bool:
        """Check if the record is soft deleted."""
        return self.deleted_at is not None

    @property
    def is_active(self) -> bool:
        """Check if the record is active (not soft deleted)."""
        return self.deleted_at is None

    def soft_delete(self) -> None:
        """Mark the record as soft deleted."""
        self.deleted_at = now_chile()

    def restore(self) -> None:
        """Restore a soft deleted record."""
        self.deleted_at = None


class BaseModel(Base, UUIDMixin, TimestampMixin):
    """Base model that includes UUID primary key and timestamps."""

    __abstract__ = True

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the model to a dictionary.

        Returns:
            Dictionary representation of the model
        """
        return {
            column.name: getattr(self, column.name)
            for column in self.__table__.columns
        }

    async def refresh_async(self, session) -> None:
        """
        Refresh the model instance asynchronously.

        Args:
            session: Async database session
        """
        await session.refresh(self)

    def __repr__(self) -> str:
        attrs = ', '.join([
            f"{key}={value!r}"
            for key, value in self.to_dict().items()
            if not key.startswith('_')
        ])
        return f"{self.__class__.__name__}({attrs})"


class SoftDeleteBaseModel(BaseModel, SoftDeleteMixin):
    """Base model with soft delete support."""

    __abstract__ = True


class TenantBaseModel(BaseModel, TenantMixin):
    """Base model with multi-tenant support."""

    __abstract__ = True

    async def get_tenant_data_async(self, session, include_tenant_info: bool = False) -> Dict[str, Any]:
        """
        Get model data with optional tenant information.

        Args:
            session: Async database session
            include_tenant_info: Whether to include tenant information

        Returns:
            Dictionary with model data and optionally tenant info
        """
        data = self.to_dict()

        if include_tenant_info and self.tenant_id:
            from sqlalchemy import select
            from src.database.models.system import Tenant

            result = await session.execute(
                select(Tenant).where(Tenant.id == self.tenant_id)
            )
            tenant = result.scalar_one_or_none()

            if tenant:
                data['tenant_info'] = {
                    'id': tenant.id,
                    'name': tenant.name
                }

        return data


class TenantSoftDeleteModel(BaseModel, TenantMixin, SoftDeleteMixin):
    """Base model with multi-tenant and soft delete support."""

    __abstract__ = True

    async def get_tenant_data_async(self, session, include_tenant_info: bool = False) -> Dict[str, Any]:
        """
        Get model data with optional tenant information.

        Args:
            session: Async database session
            include_tenant_info: Whether to include tenant information

        Returns:
            Dictionary with model data and optionally tenant info
        """
        data = self.to_dict()

        if include_tenant_info and self.tenant_id:
            from sqlalchemy import select
            from src.database.models.system import Tenant

            result = await session.execute(
                select(Tenant).where(Tenant.id == self.tenant_id)
            )
            tenant = result.scalar_one_or_none()

            if tenant:
                data['tenant_info'] = {
                    'id': tenant.id,
                    'name': tenant.name
                }

        return data

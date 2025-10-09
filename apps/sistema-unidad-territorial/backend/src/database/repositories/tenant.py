"""
Repository para manejo de tenants (municipalidades).

Contiene todas las operaciones relacionadas con tenants.
"""

from typing import List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import Tenant
from src.core.logging import get_logger


logger = get_logger(__name__)


class TenantRepository:
    """Repository para operaciones de tenants."""

    @staticmethod
    async def get_all_active_tenants(session: AsyncSession) -> List[Tenant]:
        """
        Obtener todos los tenants activos del sistema.

        Args:
            session: Sesión de base de datos

        Returns:
            List[Tenant]: Lista de tenants activos
        """
        result = await session.execute(
            select(Tenant).order_by(Tenant.name)
        )
        return list(result.scalars().all())

    @staticmethod
    async def get_tenant_by_id(
        session: AsyncSession,
        tenant_id: UUID
    ) -> Optional[Tenant]:
        """
        Obtener un tenant por su ID.

        Args:
            session: Sesión de base de datos
            tenant_id: ID del tenant

        Returns:
            Tenant: Tenant encontrado o None
        """
        result = await session.execute(
            select(Tenant).where(Tenant.id == tenant_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_first_available_tenant(session: AsyncSession) -> Optional[Tenant]:
        """
        Obtener el primer tenant disponible (para compatibilidad temporal).

        Args:
            session: Sesión de base de datos

        Returns:
            Tenant: Primer tenant disponible o None
        """
        result = await session.execute(
            select(Tenant).limit(1)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def create_tenant(
        session: AsyncSession,
        name: str
    ) -> Tenant:
        """
        Crear un nuevo tenant.

        Args:
            session: Sesión de base de datos
            name: Nombre del tenant

        Returns:
            Tenant: Tenant creado
        """
        tenant = Tenant(name=name)
        session.add(tenant)
        await session.flush()
        return tenant

    @staticmethod
    async def find_tenant_by_name(
        session: AsyncSession,
        name: str
    ) -> Optional[Tenant]:
        """
        Buscar tenant por nombre.

        Args:
            session: Sesión de base de datos
            name: Nombre del tenant

        Returns:
            Tenant: Tenant encontrado o None
        """
        result = await session.execute(
            select(Tenant).where(Tenant.name == name)
        )
        return result.scalar_one_or_none()

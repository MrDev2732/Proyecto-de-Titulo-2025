"""
Repository para manejo de comunidades, membresías y solicitudes de registro.

Contiene todas las operaciones relacionadas con el sistema de comunidades.
"""

from typing import List, Optional
from uuid import UUID

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import (
    Community,
)
from src.core.logging import get_logger


logger = get_logger(__name__)


class CommunityRepository:
    """Repository para operaciones de comunidades."""

    @staticmethod
    async def create_community(
        session: AsyncSession,
        tenant_id: UUID,
        name: str,
        description: Optional[str] = None
    ) -> Community:
        """
        Crear una nueva comunidad.

        Args:
            session: Sesión de base de datos
            tenant_id: ID del tenant (municipalidad)
            name: Nombre de la comunidad
            description: Descripción opcional

        Returns:
            Community: Comunidad creada
        """
        community = Community(
            tenant_id=tenant_id,
            name=name,
            description=description
        )
        session.add(community)
        await session.flush()
        return community

    @staticmethod
    async def find_community_by_name(
        session: AsyncSession,
        tenant_id: UUID,
        name: str
    ) -> Optional[Community]:
        """
        Buscar comunidad por nombre dentro de un tenant.

        Args:
            session: Sesión de base de datos
            tenant_id: ID del tenant
            name: Nombre de la comunidad

        Returns:
            Community: Comunidad encontrada o None
        """
        result = await session.execute(
            select(Community).where(
                and_(Community.tenant_id == tenant_id, Community.name == name)
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_community_by_id(
        session: AsyncSession,
        community_id: UUID
    ) -> Optional[Community]:
        """
        Obtener una comunidad por su ID.

        Args:
            session: Sesión de base de datos
            community_id: ID de la comunidad

        Returns:
            Community: Comunidad encontrada o None
        """
        result = await session.execute(
            select(Community).where(Community.id == community_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def validate_community_belongs_to_tenant(
        session: AsyncSession,
        community_id: UUID,
        tenant_id: UUID
    ) -> bool:
        """
        Validar que una comunidad pertenezca a un tenant específico.

        Args:
            session: Sesión de base de datos
            community_id: ID de la comunidad
            tenant_id: ID del tenant

        Returns:
            bool: True si la comunidad pertenece al tenant
        """
        result = await session.execute(
            select(Community).where(
                and_(Community.id == community_id, Community.tenant_id == tenant_id)
            )
        )
        return result.scalar_one_or_none() is not None

    @staticmethod
    async def get_tenant_communities(
        session: AsyncSession,
        tenant_id: UUID
    ) -> List[Community]:
        """
        Obtener todas las comunidades de un tenant.

        Args:
            session: Sesión de base de datos
            tenant_id: ID del tenant

        Returns:
            List[Community]: Lista de comunidades
        """
        result = await session.execute(
            select(Community).where(Community.tenant_id == tenant_id)
            .order_by(Community.name)
        )
        return list(result.scalars().all())

    @staticmethod
    async def get_active_communities_by_tenant(
        session: AsyncSession,
        tenant_id: UUID
    ) -> List[Community]:
        """
        Obtener todas las comunidades activas de un tenant.

        Por ahora retorna todas las comunidades, pero en el futuro
        se puede agregar un campo 'active' o 'status' al modelo.

        Args:
            session: Sesión de base de datos
            tenant_id: ID del tenant

        Returns:
            List[Community]: Lista de comunidades activas
        """
        result = await session.execute(
            select(Community)
            .where(Community.tenant_id == tenant_id)
            # TODO: Agregar filtro por estado activo cuando se implemente
            # .where(Community.active == True)
            .order_by(Community.name)
        )
        return list(result.scalars().all())

    @staticmethod
    async def get_all_active_communities(session: AsyncSession) -> List[Community]:
        """
        Obtener todas las comunidades activas del sistema.

        Returns:
            List[Community]: Lista de todas las comunidades activas
        """
        result = await session.execute(
            select(Community)
            # TODO: Agregar filtro por estado activo cuando se implemente
            # .where(Community.active == True)
            .order_by(Community.name)
        )
        return list(result.scalars().all())

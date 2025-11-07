"""
Repository para manejo de espacios y reservas.

Contiene todas las operaciones relacionadas con los modelos Space y Reservation.
"""

from typing import List, Optional
from uuid import UUID

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.database.models.spaces import Space
from src.database.utils import now_chile
from src.core.logging import get_logger


logger = get_logger(__name__)


class SpaceRepository:
    """Repository para operaciones con espacios comunitarios."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, space: Space) -> Space:
        """
        Crear un nuevo espacio.

        Args:
            space: Instancia del espacio a crear

        Returns:
            Space: Espacio creado
        """
        self.db.add(space)
        await self.db.flush()
        await self.db.commit()
        await self.db.refresh(space)
        logger.info(f"✅ Created space {space.id} in community {space.community_id}")
        return space

    async def get(self, space_id: UUID) -> Optional[Space]:
        """
        Obtener un espacio por su ID.

        Args:
            space_id: ID del espacio

        Returns:
            Space: Espacio encontrado o None
        """
        result = await self.db.execute(
            select(Space)
            .options(selectinload(Space.community))
            .where(
                and_(
                    Space.id == space_id,
                    Space.deleted_at.is_(None)
                )
            )
        )
        return result.scalar_one_or_none()

    async def list_by_community(self, community_id: UUID) -> List[Space]:
        """
        Listar todos los espacios de una comunidad.

        Args:
            community_id: ID de la comunidad

        Returns:
            List[Space]: Lista de espacios
        """
        result = await self.db.execute(
            select(Space)
            .where(
                and_(
                    Space.community_id == community_id,
                    Space.deleted_at.is_(None)
                )
            )
            .order_by(Space.name)
        )
        return list(result.scalars().all())

    async def list_by_tenant(self, tenant_id: UUID) -> List[Space]:
        """
        Listar todos los espacios de un tenant.

        Args:
            tenant_id: ID del tenant

        Returns:
            List[Space]: Lista de espacios
        """
        result = await self.db.execute(
            select(Space)
            .where(
                and_(
                    Space.tenant_id == tenant_id,
                    Space.deleted_at.is_(None)
                )
            )
            .order_by(Space.name)
        )
        return list(result.scalars().all())

    async def update(
        self,
        space_id: UUID,
        name: Optional[str] = None,
        description: Optional[str] = None,
        capacity: Optional[int] = None,
        requires_approval: Optional[bool] = None,
        rules_json: Optional[dict] = None
    ) -> Optional[Space]:
        """
        Actualizar un espacio.

        Args:
            space_id: ID del espacio
            name: Nuevo nombre (opcional)
            description: Nueva descripción (opcional)
            capacity: Nueva capacidad (opcional)
            requires_approval: Nueva configuración de aprobación (opcional)
            rules_json: Nuevas reglas (opcional)

        Returns:
            Space: Espacio actualizado o None si no se encontró
        """
        space = await self.get(space_id)
        if not space:
            return None

        if name is not None:
            space.name = name
        if description is not None:
            space.description = description
        if capacity is not None:
            space.capacity = capacity
        if requires_approval is not None:
            space.requires_approval = requires_approval
        if rules_json is not None:
            space.rules_json = rules_json

        await self.db.flush()
        await self.db.commit()
        await self.db.refresh(space)

        logger.info(f"✅ Updated space {space_id}")
        return space

    async def disable(self, space_id: UUID) -> Optional[Space]:
        """
        Deshabilitar un espacio (soft delete).

        Args:
            space_id: ID del espacio

        Returns:
            Space: Espacio deshabilitado o None si no se encontró
        """
        space = await self.get(space_id)
        if space:
            space.deleted_at = now_chile()
            await self.db.flush()
            await self.db.commit()
            await self.db.refresh(space)
            logger.info(f"✅ Disabled space {space_id}")
        return space

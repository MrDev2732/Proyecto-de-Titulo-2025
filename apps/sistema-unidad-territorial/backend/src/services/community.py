"""
Servicio para lógica de negocio relacionada con comunidades y tenants.
"""

from typing import List, Tuple
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import Community, Tenant
from src.database.repositories import CommunityRepository, TenantRepository


class CommunityService:
    """Servicio para manejar la lógica de negocio de comunidades y tenants."""

    @staticmethod
    async def get_available_tenants_and_communities(session: AsyncSession) -> List[Tuple[Tenant, List[Community]]]:
        """
        Obtener todos los tenants activos con sus comunidades activas.

        Útil para mostrar la estructura completa de municipalidades y juntas de vecinos
        en el frontend.

        Args:
            session: Sesión de base de datos

        Returns:
            List[Tuple[Tenant, List[Community]]]: Lista de tuplas (tenant, comunidades)
        """
        # Obtener todos los tenants activos
        tenants = await TenantRepository.get_all_active_tenants(session)

        result = []
        for tenant in tenants:
            # Obtener comunidades activas para cada tenant
            communities = await CommunityRepository.get_active_communities_by_tenant(session, tenant.id)
            result.append((tenant, communities))

        return result

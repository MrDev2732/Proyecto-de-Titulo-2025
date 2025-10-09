"""
Endpoints de tenants (municipalidades) y listado de comunidades para la API.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.session import get_db_session
from src.schemas import (
    CommunityResponse,
    TenantResponse,
    TenantWithCommunitiesResponse,
    TenantsAndCommunitiesResponse,
    TenantListResponse,
    CommunitiesByTenantResponse,
)
from src.database.repositories import CommunityRepository, TenantRepository
from src.services.community_service import CommunityService
from src.core.logging import get_logger


logger = get_logger(__name__)

# Router para endpoints de tenants
router = APIRouter(prefix="/tenants", tags=["Tenants"])


@router.get(
    "/tenants-and-communities",
    response_model=TenantsAndCommunitiesResponse,
    summary="Obtener estructura completa de tenants y comunidades",
    description="Retorna todos los tenants activos con sus comunidades activas (para frontend)"
)
async def get_tenants_and_communities(
    session: AsyncSession = Depends(get_db_session),
) -> TenantsAndCommunitiesResponse:
    """
    Obtener la estructura completa de tenants y comunidades activas.

    Útil para que el frontend pueda mostrar un selector de municipalidades
    y sus respectivas juntas de vecinos.
    """
    tenants_with_communities = await CommunityService.get_available_tenants_and_communities(session)

    result_tenants = []
    total_communities = 0

    for tenant, communities in tenants_with_communities:
        tenant_response = TenantWithCommunitiesResponse(
            tenant=TenantResponse.model_validate(tenant),
            communities=[CommunityResponse.model_validate(community) for community in communities],
            total_communities=len(communities)
        )
        result_tenants.append(tenant_response)
        total_communities += len(communities)

    return TenantsAndCommunitiesResponse(
        tenants=result_tenants,
        total_tenants=len(result_tenants),
        total_communities=total_communities
    )


@router.get(
    "/",
    response_model=TenantListResponse,
    summary="Listar todos los tenants",
    description="Obtiene todos los tenants (municipalidades) activos del sistema"
)
async def list_tenants(
    session: AsyncSession = Depends(get_db_session),
) -> TenantListResponse:
    """
    Listar todos los tenants activos del sistema.

    Retorna todas las municipalidades disponibles para que el usuario
    pueda seleccionar en qué municipalidad quiere registrarse.
    """
    tenants = await TenantRepository.get_all_active_tenants(session)

    return TenantListResponse(
        tenants=[TenantResponse.model_validate(tenant) for tenant in tenants],
        total=len(tenants)
    )


@router.get(
    "/{tenant_id}/communities",
    response_model=CommunitiesByTenantResponse,
    summary="Listar comunidades de un tenant específico",
    description="Obtiene todas las comunidades activas de una municipalidad específica"
)
async def list_communities_by_tenant(
    tenant_id: UUID,
    session: AsyncSession = Depends(get_db_session),
) -> CommunitiesByTenantResponse:
    """
    Listar todas las comunidades activas de un tenant específico.

    Permite al usuario ver todas las juntas de vecinos disponibles
    en una municipalidad específica para poder elegir dónde registrarse.
    """
    # Verificar que el tenant existe
    tenant = await TenantRepository.get_tenant_by_id(session, tenant_id)
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant no encontrado"
        )

    # Obtener comunidades activas del tenant
    communities = await CommunityRepository.get_active_communities_by_tenant(session, tenant_id)

    return CommunitiesByTenantResponse(
        tenant=TenantResponse.model_validate(tenant),
        communities=[CommunityResponse.model_validate(community) for community in communities],
        total=len(communities)
    )

"""
Endpoints para obtener las comunidades del usuario autenticado.
"""

from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from src.database.session import get_db_session
from src.database.models import ResidentMembership, Community
from src.database.enums import MembershipStatus
from src.schemas import ErrorResponse
from src.core.dependencies import get_current_active_user
from src.database import User
from src.core.logging import get_logger
from pydantic import BaseModel


logger = get_logger(__name__)

# Router para endpoints de comunidades del usuario
router = APIRouter(prefix="/user", tags=["Usuario"])


class UserCommunityResponse(BaseModel):
    """Response schema para comunidades del usuario."""
    id: str
    name: str
    description: str | None
    membership_status: str
    joined_at: str

    class Config:
        from_attributes = True


class UserCommunitiesListResponse(BaseModel):
    """Response schema para lista de comunidades del usuario."""
    communities: List[UserCommunityResponse]
    total: int


@router.get(
    "/communities",
    response_model=UserCommunitiesListResponse,
    summary="Obtener comunidades del usuario autenticado",
    description="Retorna las comunidades donde el usuario tiene membresía aprobada",
    responses={
        401: {"model": ErrorResponse, "description": "Usuario no autenticado"},
        500: {"model": ErrorResponse, "description": "Error interno del servidor"}
    }
)
async def get_user_communities(
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_active_user)
) -> UserCommunitiesListResponse:
    """
    Obtener comunidades del usuario autenticado.

    **Requiere autenticación** - Token JWT válido.
    
    Retorna todas las comunidades donde el usuario tiene una membresía aprobada.
    Útil para mostrar opciones de descarga de certificados y acceso a servicios comunitarios.

    **Respuesta incluye:**
    - Lista de comunidades con membresía aprobada
    - Estado de la membresía
    - Fecha de ingreso a la comunidad
    """
    try:
        # Obtener membresías aprobadas del usuario
        query = select(ResidentMembership).options(
            selectinload(ResidentMembership.community)
        ).where(
            ResidentMembership.user_id == current_user.id,
            ResidentMembership.status == MembershipStatus.APPROVED
        ).order_by(ResidentMembership.created_at.desc())

        result = await session.execute(query)
        memberships = result.scalars().all()

        # Convertir a response
        communities_responses = []
        for membership in memberships:
            community_response = UserCommunityResponse(
                id=str(membership.community.id),
                name=membership.community.name,
                description=membership.community.description,
                membership_status=membership.status.value,
                joined_at=membership.created_at.isoformat()
            )
            communities_responses.append(community_response)

        logger.info(f"✅ Retrieved {len(communities_responses)} communities for user {current_user.email}")

        return UserCommunitiesListResponse(
            communities=communities_responses,
            total=len(communities_responses)
        )

    except Exception as e:
        logger.error(f"❌ Error retrieving user communities: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno del servidor al obtener las comunidades del usuario"
        )

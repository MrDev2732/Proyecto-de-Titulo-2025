"""
Endpoints de membresías de usuarios en comunidades para la API.
"""

from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.session import get_db_session
from src.schemas.community_schemas import ResidentMembershipResponse
from src.core.dependencies import get_current_active_user
from src.database import User
from src.database.repositories.community_repository import ResidentMembershipRepository
from src.core.logging import get_logger


logger = get_logger(__name__)

# Router para endpoints de membresías
router = APIRouter(prefix="/memberships", tags=["Membresías"])


@router.get(
    "/my-memberships",
    response_model=List[ResidentMembershipResponse],
    summary="Obtener mis membresías de comunidades",
    description="Retorna todas las membresías aprobadas del usuario actual"
)
async def get_my_memberships(
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_active_user)
) -> List[ResidentMembershipResponse]:
    """
    Obtener las membresías de comunidades del usuario actual.

    Retorna solo las membresías en estado APPROVED.
    """
    memberships = await ResidentMembershipRepository.get_user_approved_memberships(
        session, current_user.id
    )

    return [ResidentMembershipResponse.model_validate(membership) for membership in memberships]

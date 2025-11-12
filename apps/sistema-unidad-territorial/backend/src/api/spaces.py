"""
Endpoints de espacios comunitarios para la API.

Gestiona la creación y administración de espacios reservables.
"""
from uuid import UUID
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, Path
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from src.database.session import get_db_session
from src.database.models import User, ResidentMembership, Space
from src.database.enums import MembershipStatus
from src.schemas import ErrorResponse
from src.schemas.spaces import (
    SpaceCreate,
    SpaceUpdate,
    SpaceResponse,
    SpaceListResponse
)
from src.core.logging import get_logger
from src.core.dependencies import get_current_active_user, require_admin_permissions
from src.database.repositories import SpaceRepository


logger = get_logger(__name__)
router = APIRouter(prefix="/spaces", tags=["Espacios"])


async def get_user_community_id(user_id: UUID, session: AsyncSession) -> Optional[UUID]:
    """
    Obtener el community_id del usuario desde su membresía aprobada.

    Args:
        user_id: ID del usuario
        session: Sesión de base de datos

    Returns:
        UUID de la comunidad o None si no tiene membresía
    """
    result = await session.execute(
        select(ResidentMembership)
        .where(
            and_(
                ResidentMembership.user_id == user_id,
                ResidentMembership.status == MembershipStatus.APPROVED
            )
        )
        .limit(1)
    )
    membership = result.scalar_one_or_none()
    return membership.community_id if membership else None


@router.post(
    "/",
    response_model=SpaceResponse,
    summary="Crear nuevo espacio",
    description="Permite a un administrador crear un espacio reservable en su comunidad",
    status_code=status.HTTP_201_CREATED,
    responses={
        201: {"description": "Espacio creado exitosamente"},
        403: {"model": ErrorResponse, "description": "Usuario no tiene permisos"},
        404: {"model": ErrorResponse, "description": "Comunidad no encontrada"}
    }
)
async def create_space(
    space_data: SpaceCreate = ...,
    current_user: User = Depends(require_admin_permissions),
    session: AsyncSession = Depends(get_db_session)
) -> SpaceResponse:
    """
    Crear un espacio reservable en la comunidad del usuario.

    **Requisitos:**
    - El usuario debe tener permisos administrativos
    - El usuario debe pertenecer a una comunidad
    - El espacio se crea en la comunidad del usuario

    **Ejemplos de espacios:**
    - Canchas deportivas
    - Salones de eventos
    - Quincho
    - Sala de reuniones
    - Plazas o áreas comunes
    
    **Reglas de tiempo (opcionales en rules_json):**
    - max_hours_daily: Máximo de horas por día (ej: 2)
    - max_hours_weekly: Máximo de horas por semana (ej: 4)
    """
    try:
        # Verificar tenant del usuario
        user_tenant_id = current_user.tenant_id
        if not user_tenant_id:
            logger.warning(f"⚠️ User {current_user.email} has no tenant_id")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Usuario no tiene un tenant asignado"
            )

        # Obtener community_id del usuario
        community_id = await get_user_community_id(current_user.id, session)
        if not community_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Debe pertenecer a una comunidad para crear espacios"
            )

        # Crear el espacio
        space_repo = SpaceRepository(session)
        space = Space(
            community_id=community_id,
            tenant_id=user_tenant_id,
            name=space_data.name,
            description=space_data.description,
            capacity=space_data.capacity,
            requires_approval=space_data.requires_approval,
            rules_json=space_data.rules_json or {}
        )

        space = await space_repo.create(space)

        logger.info(f"✅ Space {space.id} created by {current_user.email} in community {community_id}")
        return SpaceResponse.model_validate(space)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error creating space: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al crear el espacio: {str(e)}"
        )


@router.get(
    "/my-community",
    response_model=SpaceListResponse,
    summary="Listar espacios de mi comunidad",
    description="Obtiene todos los espacios disponibles de la comunidad del usuario"
)
async def list_my_community_spaces(
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db_session)
) -> SpaceListResponse:
    """
    Listar todos los espacios de la comunidad del usuario.

    **Acceso:**
    - Usuario debe pertenecer a una comunidad
    """
    try:
        # Obtener community_id del usuario
        community_id = await get_user_community_id(current_user.id, session)
        if not community_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Debe pertenecer a una comunidad para ver espacios"
            )

        space_repo = SpaceRepository(session)
        spaces = await space_repo.list_by_community(community_id)

        return SpaceListResponse(
            spaces=[SpaceResponse.model_validate(space) for space in spaces],
            total=len(spaces)
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error listing spaces: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al listar espacios: {str(e)}"
        )


@router.get(
    "/community/{community_id}",
    response_model=SpaceListResponse,
    summary="Listar espacios de una comunidad",
    description="Obtiene todos los espacios disponibles de una comunidad específica"
)
async def list_community_spaces(
    community_id: UUID = Path(..., description="ID de la comunidad"),
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db_session)
) -> SpaceListResponse:
    """
    Listar todos los espacios de una comunidad específica.

    **Acceso:**
    - Cualquier usuario autenticado puede ver los espacios
    """
    try:
        space_repo = SpaceRepository(session)
        spaces = await space_repo.list_by_community(community_id)

        return SpaceListResponse(
            spaces=[SpaceResponse.model_validate(space) for space in spaces],
            total=len(spaces)
        )

    except Exception as e:
        logger.error(f"❌ Error listing spaces: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al listar espacios: {str(e)}"
        )


@router.get(
    "/{space_id}",
    response_model=SpaceResponse,
    summary="Obtener detalles de un espacio",
    description="Obtiene la información detallada de un espacio específico"
)
async def get_space(
    space_id: UUID = Path(..., description="ID del espacio"),
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db_session)
) -> SpaceResponse:
    """Obtener información de un espacio."""
    try:
        space_repo = SpaceRepository(session)
        space = await space_repo.get(space_id)

        if not space:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Espacio no encontrado"
            )

        return SpaceResponse.model_validate(space)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error getting space: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener el espacio: {str(e)}"
        )


@router.patch(
    "/{space_id}",
    response_model=SpaceResponse,
    summary="Actualizar espacio",
    description="Permite actualizar la información de un espacio"
)
async def update_space(
    space_id: UUID = Path(..., description="ID del espacio"),
    space_data: SpaceUpdate = ...,
    current_user: User = Depends(require_admin_permissions),
    session: AsyncSession = Depends(get_db_session)
) -> SpaceResponse:
    """Actualizar información de un espacio."""
    try:
        space_repo = SpaceRepository(session)

        # Verificar que el espacio existe
        space = await space_repo.get(space_id)
        if not space:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Espacio no encontrado"
            )

        # Verificar permisos del tenant
        if space.tenant_id != current_user.tenant_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tiene permisos para actualizar este espacio"
            )

        # Actualizar el espacio
        updated_space = await space_repo.update(
            space_id=space_id,
            name=space_data.name,
            description=space_data.description,
            capacity=space_data.capacity,
            requires_approval=space_data.requires_approval,
            rules_json=space_data.rules_json
        )

        logger.info(f"✅ Space {space_id} updated by {current_user.email}")
        return SpaceResponse.model_validate(updated_space)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error updating space: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al actualizar el espacio: {str(e)}"
        )


@router.delete(
    "/{space_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar espacio",
    description="Deshabilita un espacio (soft delete)"
)
async def delete_space(
    space_id: UUID = Path(..., description="ID del espacio"),
    current_user: User = Depends(require_admin_permissions),
    session: AsyncSession = Depends(get_db_session)
):
    """Deshabilitar un espacio."""
    try:
        space_repo = SpaceRepository(session)

        # Verificar que el espacio existe
        space = await space_repo.get(space_id)
        if not space:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Espacio no encontrado"
            )

        # Verificar permisos del tenant
        if space.tenant_id != current_user.tenant_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tiene permisos para eliminar este espacio"
            )

        await space_repo.disable(space_id)
        logger.info(f"✅ Space {space_id} disabled by {current_user.email}")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error deleting space: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al eliminar el espacio: {str(e)}"
        )

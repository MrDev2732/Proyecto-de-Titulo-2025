"""
Endpoints de reservas de espacios para la API.

Gestiona las reservas de espacios comunitarios con calendario.
"""
from uuid import UUID
from typing import Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status, Query, Path
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from src.database.session import get_db_session
from src.database.models import User, ResidentMembership
from src.database.models.spaces import Reservation
from src.database.enums import ReservationStatus, MembershipStatus
from src.schemas import ErrorResponse
from src.schemas.spaces import (
    ReservationCreate,
    ReservationUpdate,
    ReservationResponse,
    ReservationListResponse,
    ReservationApprovalRequest,
    AvailabilityCheckRequest,
    AvailabilityCheckResponse,
    ReservationCalendarResponse
)
from src.core.logging import get_logger
from src.core.dependencies import get_current_active_user, require_admin_permissions
from src.database.repositories import SpaceRepository, ReservationRepository


logger = get_logger(__name__)
router = APIRouter(prefix="/reservations", tags=["Reservas"])


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
                ResidentMembership.status == MembershipStatus.APPROVED,
                ResidentMembership.deleted_at.is_(None)
            )
        )
        .limit(1)
    )
    membership = result.scalar_one_or_none()

    if membership:
        logger.debug(f"✅ Found membership for user {user_id}: community_id={membership.community_id}")
        return membership.community_id
    else:
        logger.warning(f"⚠️ No approved membership found for user {user_id}")
        return None


# ==================== Reservation Endpoints ====================
@router.post(
    "/availability",
    response_model=AvailabilityCheckResponse,
    summary="Verificar disponibilidad",
    description="Verifica si un espacio está disponible en un rango de tiempo"
)
async def check_availability(
    availability_data: AvailabilityCheckRequest = ...,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db_session)
) -> AvailabilityCheckResponse:
    """
    Verificar disponibilidad de un espacio.

    **Uso:**
    - Consulta antes de crear una reserva
    - Verifica conflictos con reservas existentes
    """
    try:
        reservation_repo = ReservationRepository(session)

        is_available, conflicts = await reservation_repo.check_availability(
            space_id=availability_data.space_id,
            start_time=availability_data.start_time,
            end_time=availability_data.end_time
        )

        message = "El espacio está disponible" if is_available else "El espacio no está disponible en ese horario"

        return AvailabilityCheckResponse(
            is_available=is_available,
            conflicting_reservations=[
                ReservationResponse.model_validate(r) for r in conflicts
            ],
            message=message
        )

    except Exception as e:
        logger.error(f"❌ Error checking availability: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al verificar disponibilidad: {str(e)}"
        )


@router.post(
    "/",
    response_model=ReservationResponse,
    summary="Crear solicitud de reserva",
    description="Permite a un usuario solicitar la reserva de un espacio",
    status_code=status.HTTP_201_CREATED,
    responses={
        201: {"description": "Reserva creada exitosamente"},
        404: {"model": ErrorResponse, "description": "Espacio no encontrado"},
        409: {"model": ErrorResponse, "description": "Conflicto de horario"},
        403: {"model": ErrorResponse, "description": "Usuario no pertenece a ninguna comunidad"}
    }
)
async def create_reservation(
    reservation_data: ReservationCreate = ...,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db_session)
) -> ReservationResponse:
    """
    Crear una solicitud de reserva.

    **Proceso:**
    1. Verifica que el usuario pertenece a una comunidad
    2. Verifica que el espacio existe y pertenece a la misma comunidad
    3. Verifica disponibilidad en el horario solicitado
    4. Verifica límites de tiempo (si están configurados en el espacio)
    5. Crea la reserva con estado PENDING o CONFIRMED según configuración del espacio

    **Estados:**
    - PENDING: Requiere aprobación del administrador
    - CONFIRMED: Aprobación automática (si el espacio lo permite)
    """
    try:
        logger.info(f"🎫 Creating reservation for user {current_user.id} ({current_user.email})")
        logger.info(f"📍 Space ID: {reservation_data.space_id}")
        logger.info(f"⏰ Time: {reservation_data.start_time} to {reservation_data.end_time}")

        space_repo = SpaceRepository(session)
        reservation_repo = ReservationRepository(session)

        # Obtener community_id del usuario
        user_community_id = await get_user_community_id(current_user.id, session)
        logger.info(f"🏘️ User community_id: {user_community_id}")
        if not user_community_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Debe pertenecer a una comunidad para hacer reservas"
            )

        # Verificar que el espacio existe
        space = await space_repo.get(reservation_data.space_id)
        if not space:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Espacio no encontrado"
            )

        # Verificar que el espacio pertenece a la comunidad del usuario
        if space.community_id != user_community_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Solo puede reservar espacios de su comunidad"
            )

        # Verificar disponibilidad
        is_available, conflicts = await reservation_repo.check_availability(
            space_id=reservation_data.space_id,
            start_time=reservation_data.start_time,
            end_time=reservation_data.end_time
        )

        if not is_available:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="El espacio no está disponible en ese horario"
            )

        # Verificar límites de tiempo si están configurados en rules_json
        if space.rules_json:
            max_hours_daily = space.rules_json.get('max_hours_daily')
            max_hours_weekly = space.rules_json.get('max_hours_weekly')

            if max_hours_daily or max_hours_weekly:
                complies, error_message = await reservation_repo.check_user_time_limits(
                    user_id=current_user.id,
                    space_id=reservation_data.space_id,
                    start_time=reservation_data.start_time,
                    end_time=reservation_data.end_time,
                    max_hours_daily=max_hours_daily,
                    max_hours_weekly=max_hours_weekly
                )

                if not complies:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=error_message
                    )

        # Determinar estado inicial según configuración del espacio
        initial_status = (
            ReservationStatus.PENDING.value if space.requires_approval 
            else ReservationStatus.CONFIRMED.value
        )

        # Crear la reserva
        reservation = Reservation(
            space_id=reservation_data.space_id,
            requesting_user_id=current_user.id,
            start_time=reservation_data.start_time,
            end_time=reservation_data.end_time,
            status=initial_status
        )

        reservation = await reservation_repo.create(reservation)

        logger.info(
            f"✅ Reservation {reservation.id} created by {current_user.email} "
            f"with status {initial_status}"
        )

        # Cargar relaciones para respuesta
        reservation = await reservation_repo.get(reservation.id)
        response = ReservationResponse.model_validate(reservation)

        # Agregar información adicional
        response.space_name = space.name
        response.user_email = current_user.email

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error creating reservation: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al crear la reserva: {str(e)}"
        )


@router.get(
    "/my-reservations",
    response_model=ReservationListResponse,
    summary="Mis reservas",
    description="Obtiene todas las reservas del usuario actual"
)
async def get_my_reservations(
    include_past: bool = Query(False, description="Incluir reservas pasadas"),
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db_session)
) -> ReservationListResponse:
    """
    Listar las reservas del usuario actual.

    **Filtros:**
    - Por defecto solo muestra reservas futuras y activas
    - Puede incluir reservas pasadas con el parámetro include_past
    """
    try:
        reservation_repo = ReservationRepository(session)
        reservations = await reservation_repo.list_by_user(
            user_id=current_user.id,
            include_past=include_past
        )

        # Enriquecer con información adicional
        responses = []
        for reservation in reservations:
            response = ReservationResponse.model_validate(reservation)
            response.space_name = reservation.space.name if reservation.space else None
            response.user_email = current_user.email
            responses.append(response)

        return ReservationListResponse(
            reservations=responses,
            total=len(responses),
            page=1,
            per_page=len(responses),
            total_pages=1
        )

    except Exception as e:
        logger.error(f"❌ Error listing user reservations: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al listar reservas: {str(e)}"
        )


@router.get(
    "/community",
    response_model=ReservationListResponse,
    summary="Listar reservas de comunidad",
    description="Lista todas las reservas de la comunidad del usuario actual con paginación"
)
async def list_community_reservations(
    page: int = Query(1, ge=1, description="Número de página"),
    per_page: int = Query(20, ge=1, le=100, description="Elementos por página"),
    status_filter: Optional[str] = Query(None, description="Filtrar por estado"),
    space_id: Optional[UUID] = Query(None, description="Filtrar por espacio"),
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db_session)
) -> ReservationListResponse:
    """
    Listar reservas de la comunidad del usuario actual.

    **Comportamiento:**
    - Obtiene automáticamente el community_id de la membresía del usuario
    - Solo muestra reservas de la comunidad a la que pertenece el usuario

    **Filtros disponibles:**
    - Estado (PENDING, CONFIRMED, CANCELLED)
    - Espacio específico
    - Paginación
    """
    try:
        logger.info(f"🔍 Listing community reservations for user {current_user.email}")

        # Obtener community_id del usuario autenticado
        user_community_id = await get_user_community_id(current_user.id, session)
        logger.info(f"📍 User community_id: {user_community_id}")

        if not user_community_id:
            logger.warning(f"⚠️ User {current_user.email} has no approved community membership")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Debe pertenecer a una comunidad para ver sus reservas"
            )

        reservation_repo = ReservationRepository(session)

        reservations, total, total_pages = await reservation_repo.list_by_community_paginated(
            community_id=user_community_id,
            page=page,
            per_page=per_page,
            status_filter=status_filter,
            space_id_filter=space_id
        )

        logger.info(f"📊 Found {total} total reservations, {len(reservations)} on current page, {total_pages} total pages")

        # Enriquecer con información adicional
        responses = []
        for reservation in reservations:
            response = ReservationResponse.model_validate(reservation)
            response.space_name = reservation.space.name if reservation.space else None
            response.user_email = reservation.requesting_user.email if reservation.requesting_user else None
            responses.append(response)

        logger.info(f"✅ Successfully enriched {len(responses)} reservations")

        return ReservationListResponse(
            reservations=responses,
            total=total,
            page=page,
            per_page=per_page,
            total_pages=total_pages
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error listing community reservations: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al listar reservas: {str(e)}"
        )


@router.get(
    "/calendar/{space_id}",
    response_model=ReservationCalendarResponse,
    summary="Calendario de reservas",
    description="Obtiene las reservas de un espacio en un rango de fechas para visualización de calendario"
)
async def get_space_calendar(
    space_id: UUID = Path(..., description="ID del espacio"),
    start_date: datetime = Query(..., description="Fecha de inicio"),
    end_date: datetime = Query(..., description="Fecha de fin"),
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db_session)
) -> ReservationCalendarResponse:
    """
    Obtener calendario de reservas de un espacio.

    **Uso:**
    - Visualización de calendario
    - Ver disponibilidad en un rango de fechas
    - Planificación de reservas
    """
    try:
        space_repo = SpaceRepository(session)
        reservation_repo = ReservationRepository(session)

        # Verificar que el espacio existe
        space = await space_repo.get(space_id)
        if not space:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Espacio no encontrado"
            )

        # Obtener reservas en el rango de fechas
        reservations = await reservation_repo.list_by_space_and_date_range(
            space_id=space_id,
            start_date=start_date,
            end_date=end_date
        )

        # Enriquecer con información adicional
        responses = []
        for reservation in reservations:
            response = ReservationResponse.model_validate(reservation)
            response.space_name = space.name
            response.user_email = reservation.requesting_user.email if reservation.requesting_user else None
            responses.append(response)

        return ReservationCalendarResponse(
            space_id=str(space_id),
            space_name=space.name,
            reservations=responses
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error getting calendar: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener calendario: {str(e)}"
        )


@router.patch(
    "/{reservation_id}/approve",
    response_model=ReservationResponse,
    summary="Aprobar o rechazar reserva",
    description="Permite a un administrador aprobar o rechazar una reserva pendiente"
)
async def approve_reservation(
    reservation_id: UUID = Path(..., description="ID de la reserva"),
    approval_data: ReservationApprovalRequest = ...,
    current_user: User = Depends(require_admin_permissions),
    session: AsyncSession = Depends(get_db_session)
) -> ReservationResponse:
    """
    Aprobar o rechazar una reserva.

    **Requisitos:**
    - Usuario debe tener permisos administrativos
    - La reserva debe estar en estado PENDING

    **Acciones:**
    - CONFIRMED: Aprobar la reserva
    - CANCELLED: Rechazar la reserva
    """
    try:
        reservation_repo = ReservationRepository(session)

        # Obtener la reserva
        reservation = await reservation_repo.get(reservation_id)
        if not reservation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Reserva no encontrada"
            )

        # Verificar que el usuario tiene permisos (mismo tenant)
        space = reservation.space
        if space.tenant_id != current_user.tenant_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tiene permisos para aprobar esta reserva"
            )

        # Verificar que la reserva está pendiente
        if reservation.status != ReservationStatus.PENDING.value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"La reserva no está en estado pendiente (estado actual: {reservation.status})"
            )

        # Actualizar el estado
        updated_reservation = await reservation_repo.update_status(
            reservation_id=reservation_id,
            status=approval_data.status,
            cancel_reason=approval_data.cancel_reason
        )

        logger.info(
            f"✅ Reservation {reservation_id} {approval_data.status} by {current_user.email}"
        )

        response = ReservationResponse.model_validate(updated_reservation)
        response.space_name = space.name
        response.user_email = updated_reservation.requesting_user.email if updated_reservation.requesting_user else None

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error approving reservation: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al aprobar/rechazar reserva: {str(e)}"
        )


@router.patch(
    "/{reservation_id}/cancel",
    response_model=ReservationResponse,
    summary="Cancelar reserva",
    description="Permite al usuario cancelar su propia reserva"
)
async def cancel_reservation(
    reservation_id: UUID = Path(..., description="ID de la reserva"),
    cancel_data: ReservationUpdate = ...,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db_session)
) -> ReservationResponse:
    """
    Cancelar una reserva propia.

    **Requisitos:**
    - El usuario debe ser el dueño de la reserva
    - La reserva no debe estar ya cancelada
    """
    try:
        reservation_repo = ReservationRepository(session)

        # Obtener la reserva
        reservation = await reservation_repo.get(reservation_id)
        if not reservation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Reserva no encontrada"
            )

        # Verificar que el usuario es el dueño de la reserva
        if reservation.requesting_user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Solo puede cancelar sus propias reservas"
            )

        # Verificar que no esté ya cancelada
        if reservation.status == ReservationStatus.CANCELLED.value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="La reserva ya está cancelada"
            )

        # Cancelar la reserva
        updated_reservation = await reservation_repo.cancel(
            reservation_id=reservation_id,
            cancel_reason=cancel_data.cancel_reason
        )

        logger.info(f"✅ Reservation {reservation_id} cancelled by user {current_user.email}")

        response = ReservationResponse.model_validate(updated_reservation)
        response.space_name = reservation.space.name if reservation.space else None
        response.user_email = current_user.email

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error cancelling reservation: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al cancelar reserva: {str(e)}"
        )


@router.get(
    "/{reservation_id}",
    response_model=ReservationResponse,
    summary="Obtener detalles de reserva",
    description="Obtiene la información detallada de una reserva específica"
)
async def get_reservation(
    reservation_id: UUID = Path(..., description="ID de la reserva"),
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db_session)
) -> ReservationResponse:
    """Obtener información de una reserva."""
    try:
        reservation_repo = ReservationRepository(session)
        reservation = await reservation_repo.get(reservation_id)

        if not reservation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Reserva no encontrada"
            )

        response = ReservationResponse.model_validate(reservation)
        response.space_name = reservation.space.name if reservation.space else None
        response.user_email = reservation.requesting_user.email if reservation.requesting_user else None

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error getting reservation: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener la reserva: {str(e)}"
        )

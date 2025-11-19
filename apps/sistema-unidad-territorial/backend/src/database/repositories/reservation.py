from typing import List, Optional, Tuple
from uuid import UUID
from datetime import datetime, timedelta

from sqlalchemy import select, and_, or_, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.database.models.spaces import Space, Reservation
from src.database.enums import ReservationStatus
from src.database.utils import now_chile
from src.core.logging import get_logger


logger = get_logger(__name__)


class ReservationRepository:
    """Repository para operaciones con reservas de espacios."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, reservation: Reservation) -> Reservation:
        """
        Crear una nueva reserva.

        Args:
            reservation: Instancia de la reserva a crear

        Returns:
            Reservation: Reserva creada
        """
        self.db.add(reservation)
        await self.db.flush()
        await self.db.commit()
        await self.db.refresh(reservation)
        logger.info(
            f"✅ Created reservation {reservation.id} for space {reservation.space_id} "
            f"by user {reservation.requesting_user_id}"
        )
        return reservation

    async def check_user_time_limits(
        self,
        user_id: UUID,
        space_id: UUID,
        start_time: datetime,
        end_time: datetime,
        max_hours_daily: Optional[float] = None,
        max_hours_weekly: Optional[float] = None
    ) -> Tuple[bool, Optional[str]]:
        """
        Verificar si el usuario excede los límites de tiempo configurados para el espacio.

        Args:
            user_id: ID del usuario
            space_id: ID del espacio
            start_time: Hora de inicio de la nueva reserva
            end_time: Hora de fin de la nueva reserva
            max_hours_daily: Máximo de horas permitidas por día
            max_hours_weekly: Máximo de horas permitidas por semana

        Returns:
            Tupla de (cumple_limites, mensaje_error)
        """
        # Si no hay límites configurados, permitir
        if not max_hours_daily and not max_hours_weekly:
            return True, None

        # Calcular duración de la nueva reserva en horas
        duration_hours = (end_time - start_time).total_seconds() / 3600

        # Verificar límite diario
        if max_hours_daily:
            # Obtener inicio y fin del día de la nueva reserva
            day_start = start_time.replace(hour=0, minute=0, second=0, microsecond=0)
            day_end = start_time.replace(hour=23, minute=59, second=59, microsecond=999999)

            # Contar horas ya reservadas ese día
            daily_query = select(func.sum(
                func.extract('epoch', Reservation.end_time - Reservation.start_time) / 3600
            )).where(
                and_(
                    Reservation.requesting_user_id == user_id,
                    Reservation.space_id == space_id,
                    Reservation.status.in_([ReservationStatus.PENDING.value, ReservationStatus.CONFIRMED.value]),
                    Reservation.deleted_at.is_(None),
                    Reservation.start_time >= day_start,
                    Reservation.end_time <= day_end
                )
            )
            result = await self.db.execute(daily_query)
            daily_hours = result.scalar() or 0

            if daily_hours + duration_hours > max_hours_daily:
                return False, f"Esta reserva de {duration_hours:.1f} hora(s) excede el límite diario de {max_hours_daily} hora(s). Ya tienes {daily_hours:.1f} hora(s) reservadas hoy."

        # Verificar límite semanal
        if max_hours_weekly:
            # Obtener inicio y fin de la semana de la nueva reserva
            week_start = start_time - timedelta(days=start_time.weekday())
            week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)
            week_end = week_start + timedelta(days=7)

            # Contar horas ya reservadas esa semana
            weekly_query = select(func.sum(
                func.extract('epoch', Reservation.end_time - Reservation.start_time) / 3600
            )).where(
                and_(
                    Reservation.requesting_user_id == user_id,
                    Reservation.space_id == space_id,
                    Reservation.status.in_([ReservationStatus.PENDING.value, ReservationStatus.CONFIRMED.value]),
                    Reservation.deleted_at.is_(None),
                    Reservation.start_time >= week_start,
                    Reservation.end_time < week_end
                )
            )
            result = await self.db.execute(weekly_query)
            weekly_hours = result.scalar() or 0

            if weekly_hours + duration_hours > max_hours_weekly:
                return False, f"Esta reserva de {duration_hours:.1f} hora(s) excede el límite semanal de {max_hours_weekly} hora(s). Ya tienes {weekly_hours:.1f} hora(s) reservadas esta semana."

        return True, None

    async def get(self, reservation_id: UUID) -> Optional[Reservation]:
        """
        Obtener una reserva por su ID con sus relaciones.

        Args:
            reservation_id: ID de la reserva

        Returns:
            Reservation: Reserva encontrada o None
        """
        result = await self.db.execute(
            select(Reservation)
            .options(
                selectinload(Reservation.space),
                selectinload(Reservation.requesting_user)
            )
            .where(
                and_(
                    Reservation.id == reservation_id,
                    Reservation.deleted_at.is_(None)
                )
            )
        )
        return result.scalar_one_or_none()

    async def check_availability(
        self,
        space_id: UUID,
        start_time: datetime,
        end_time: datetime,
        exclude_reservation_id: Optional[UUID] = None
    ) -> Tuple[bool, List[Reservation]]:
        """
        Verificar disponibilidad de un espacio en un rango de tiempo.

        Solo considera reservas confirmadas o pendientes (no canceladas).

        Args:
            space_id: ID del espacio
            start_time: Hora de inicio
            end_time: Hora de fin
            exclude_reservation_id: ID de reserva a excluir (para actualizaciones)

        Returns:
            Tupla de (disponible, lista de reservas conflictivas)
        """
        filters = [
            Reservation.space_id == space_id,
            Reservation.deleted_at.is_(None),
            Reservation.status.in_([ReservationStatus.PENDING.value, ReservationStatus.CONFIRMED.value]),
            # Verificar solapamiento de rangos de tiempo
            or_(
                # La nueva reserva inicia durante una reserva existente
                and_(
                    Reservation.start_time <= start_time,
                    Reservation.end_time > start_time
                ),
                # La nueva reserva termina durante una reserva existente
                and_(
                    Reservation.start_time < end_time,
                    Reservation.end_time >= end_time
                ),
                # La nueva reserva envuelve completamente una reserva existente
                and_(
                    Reservation.start_time >= start_time,
                    Reservation.end_time <= end_time
                )
            )
        ]

        # Excluir una reserva específica si se proporciona (útil para actualizaciones)
        if exclude_reservation_id:
            filters.append(Reservation.id != exclude_reservation_id)

        result = await self.db.execute(
            select(Reservation)
            .options(
                selectinload(Reservation.space),
                selectinload(Reservation.requesting_user)
            )
            .where(and_(*filters))
        )
        conflicting_reservations = list(result.scalars().all())

        is_available = len(conflicting_reservations) == 0
        return is_available, conflicting_reservations

    async def list_by_space_and_date_range(
        self,
        space_id: UUID,
        start_date: datetime,
        end_date: datetime
    ) -> List[Reservation]:
        """
        Listar todas las reservas de un espacio en un rango de fechas.

        Args:
            space_id: ID del espacio
            start_date: Fecha de inicio
            end_date: Fecha de fin

        Returns:
            List[Reservation]: Lista de reservas
        """
        result = await self.db.execute(
            select(Reservation)
            .options(
                selectinload(Reservation.space),
                selectinload(Reservation.requesting_user)
            )
            .where(
                and_(
                    Reservation.space_id == space_id,
                    Reservation.deleted_at.is_(None),
                    Reservation.start_time >= start_date,
                    Reservation.end_time <= end_date
                )
            )
            .order_by(Reservation.start_time)
        )
        return list(result.scalars().all())

    async def list_by_community_paginated(
        self,
        community_id: UUID,
        page: int = 1,
        per_page: int = 20,
        status_filter: Optional[str] = None,
        space_id_filter: Optional[UUID] = None
    ) -> Tuple[List[Reservation], int, int]:
        """
        Listar reservas de una comunidad con paginación.

        Args:
            community_id: ID de la comunidad
            page: Número de página
            per_page: Elementos por página
            status_filter: Filtro opcional por estado
            space_id_filter: Filtro opcional por espacio

        Returns:
            Tupla de (lista de reservas, total de elementos, total de páginas)
        """
        # Construir filtros base
        filters = [
            Reservation.deleted_at.is_(None)
        ]

        # Agregar filtros opcionales
        if status_filter:
            filters.append(Reservation.status == status_filter)
        if space_id_filter:
            filters.append(Reservation.space_id == space_id_filter)

        # Query base con carga de relaciones y filtro por comunidad
        base_query = (
            select(Reservation)
            .join(Space, Reservation.space_id == Space.id)
            .options(
                selectinload(Reservation.space),
                selectinload(Reservation.requesting_user)
            )
            .where(
                and_(
                    Space.community_id == community_id,
                    Space.deleted_at.is_(None),
                    *filters
                )
            )
            .order_by(Reservation.start_time.desc())
        )

        # Contar total
        count_query = (
            select(func.count())
            .select_from(Reservation)
            .join(Space, Reservation.space_id == Space.id)
            .where(
                and_(
                    Space.community_id == community_id,
                    Space.deleted_at.is_(None),
                    *filters
                )
            )
        )
        count_result = await self.db.execute(count_query)
        total = count_result.scalar()

        # Calcular paginación
        total_pages = (total + per_page - 1) // per_page if total > 0 else 1
        offset = (page - 1) * per_page

        # Ejecutar query con paginación
        paginated_query = base_query.offset(offset).limit(per_page)
        result = await self.db.execute(paginated_query)
        reservations = result.scalars().all()

        return list(reservations), total, total_pages

    async def list_by_user(
        self,
        user_id: UUID,
        include_past: bool = False
    ) -> List[Reservation]:
        """
        Listar todas las reservas de un usuario.

        Args:
            user_id: ID del usuario
            include_past: Si incluir reservas pasadas

        Returns:
            List[Reservation]: Lista de reservas
        """
        filters = [
            Reservation.requesting_user_id == user_id,
            Reservation.deleted_at.is_(None)
        ]

        if not include_past:
            filters.append(Reservation.end_time >= now_chile())

        result = await self.db.execute(
            select(Reservation)
            .options(
                selectinload(Reservation.space),
                selectinload(Reservation.requesting_user)
            )
            .where(and_(*filters))
            .order_by(Reservation.start_time.desc())
        )
        return list(result.scalars().all())

    async def update_status(
        self,
        reservation_id: UUID,
        status: str,
        cancel_reason: Optional[str] = None
    ) -> Optional[Reservation]:
        """
        Actualizar el estado de una reserva.

        Args:
            reservation_id: ID de la reserva
            status: Nuevo estado
            cancel_reason: Razón de cancelación (si aplica)

        Returns:
            Reservation: Reserva actualizada o None si no se encontró
        """
        reservation = await self.get(reservation_id)
        if not reservation:
            return None

        reservation.status = status
        if status == ReservationStatus.CANCELLED.value:
            reservation.canceled_at = now_chile()
            if cancel_reason:
                reservation.cancel_reason = cancel_reason

        await self.db.flush()
        await self.db.commit()
        await self.db.refresh(reservation)

        logger.info(f"✅ Updated reservation {reservation_id} status to {status}")
        return reservation

    async def cancel(
        self,
        reservation_id: UUID,
        cancel_reason: Optional[str] = None
    ) -> Optional[Reservation]:
        """
        Cancelar una reserva.

        Args:
            reservation_id: ID de la reserva
            cancel_reason: Razón de cancelación

        Returns:
            Reservation: Reserva cancelada o None si no se encontró
        """
        return await self.update_status(
            reservation_id,
            ReservationStatus.CANCELLED.value,
            cancel_reason
        )

    async def get_space_from_reservation(self, reservation_id: UUID) -> Optional[Space]:
        """
        Obtener el espacio asociado a una reserva.

        Args:
            reservation_id: ID de la reserva

        Returns:
            Space: Espacio asociado o None
        """
        reservation = await self.get(reservation_id)
        if not reservation:
            return None

        return reservation.space

    async def update_expired_reservations(self) -> int:
        """
        Actualizar automáticamente el estado de reservas expiradas.

        Encuentra todas las reservas con estado PENDING cuyo end_time ya pasó
        y las marca como EXPIRED.

        NOTA: Las reservas CONFIRMED no se marcan como EXPIRED porque representan
        reservas que fueron utilizadas exitosamente. Solo las PENDING que expiraron
        sin ser confirmadas se marcan como EXPIRED.

        Returns:
            int: Número de reservas actualizadas
        """
        current_time = now_chile()

        # Buscar solo reservas PENDING expiradas
        result = await self.db.execute(
            select(Reservation)
            .where(
                and_(
                    Reservation.deleted_at.is_(None),
                    Reservation.status == ReservationStatus.PENDING.value,
                    Reservation.end_time < current_time
                )
            )
        )
        expired_reservations = list(result.scalars().all())

        if not expired_reservations:
            return 0

        # Actualizar estado a EXPIRED
        count = 0
        for reservation in expired_reservations:
            reservation.status = ReservationStatus.EXPIRED.value
            count += 1

        await self.db.flush()
        await self.db.commit()

        logger.info(f"✅ Updated {count} pending reservations to EXPIRED status")
        return count

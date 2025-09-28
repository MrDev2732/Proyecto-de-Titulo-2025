"""
Repository para manejo de comunidades, membresías y solicitudes de registro.

Contiene todas las operaciones relacionadas con el sistema de comunidades.
"""

from typing import List, Optional
from uuid import UUID

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.database import (
    now_chile,
    Community,
    ResidentMembership,
    RegistrationRequest,
    RegistrationRequestAttachment,
    MembershipStatus,
    RegistrationStatus,
    RegistrationProvider,
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


class ResidentMembershipRepository:
    """Repository para operaciones de membresías de residentes."""

    @staticmethod
    async def create_membership(
        session: AsyncSession,
        user_id: UUID,
        community_id: UUID,
        status: MembershipStatus = MembershipStatus.PENDING,
        verified: bool = False
    ) -> ResidentMembership:
        """
        Crear una nueva membresía de residente.

        Args:
            session: Sesión de base de datos
            user_id: ID del usuario
            community_id: ID de la comunidad
            status: Estado de la membresía
            verified: Si está verificada

        Returns:
            ResidentMembership: Membresía creada
        """
        membership = ResidentMembership(
            user_id=user_id,
            community_id=community_id,
            status=status,
            verified=verified
        )
        session.add(membership)
        await session.flush()
        return membership

    @staticmethod
    async def find_user_membership_in_community(
        session: AsyncSession,
        user_id: UUID,
        community_id: UUID
    ) -> Optional[ResidentMembership]:
        """
        Buscar la membresía de un usuario en una comunidad específica.

        Args:
            session: Sesión de base de datos
            user_id: ID del usuario
            community_id: ID de la comunidad

        Returns:
            ResidentMembership: Membresía encontrada o None
        """
        result = await session.execute(
            select(ResidentMembership).where(
                and_(
                    ResidentMembership.user_id == user_id,
                    ResidentMembership.community_id == community_id
                )
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_user_approved_memberships(
        session: AsyncSession,
        user_id: UUID
    ) -> List[ResidentMembership]:
        """
        Obtener todas las membresías aprobadas de un usuario.

        Args:
            session: Sesión de base de datos
            user_id: ID del usuario

        Returns:
            List[ResidentMembership]: Lista de membresías aprobadas
        """
        result = await session.execute(
            select(ResidentMembership)
            .options(selectinload(ResidentMembership.community))
            .where(
                and_(
                    ResidentMembership.user_id == user_id,
                    ResidentMembership.status == MembershipStatus.APPROVED
                )
            )
        )
        return list(result.scalars().all())

    @staticmethod
    async def user_has_approved_membership(
        session: AsyncSession,
        user_id: UUID
    ) -> bool:
        """
        Verificar si un usuario tiene al menos una membresía aprobada.

        Args:
            session: Sesión de base de datos
            user_id: ID del usuario

        Returns:
            bool: True si tiene membresía aprobada, False si no
        """
        result = await session.execute(
            select(ResidentMembership).where(
                and_(
                    ResidentMembership.user_id == user_id,
                    ResidentMembership.status == MembershipStatus.APPROVED
                )
            )
        )
        return result.scalar_one_or_none() is not None

    @staticmethod
    async def approve_membership(
        session: AsyncSession,
        membership_id: UUID,
        verified: bool = True
    ) -> Optional[ResidentMembership]:
        """
        Aprobar una membresía y opcionalmente verificarla.

        Args:
            session: Sesión de base de datos
            membership_id: ID de la membresía
            verified: Si marcar como verificada

        Returns:
            ResidentMembership: Membresía actualizada o None si no se encontró
        """
        result = await session.execute(
            select(ResidentMembership).where(ResidentMembership.id == membership_id)
        )
        membership = result.scalar_one_or_none()

        if membership:
            membership.status = MembershipStatus.APPROVED
            membership.verified = verified
            if verified:
                membership.verified_at = now_chile()
            await session.flush()

        return membership


class RegistrationRequestRepository:
    """Repository para operaciones de solicitudes de registro."""

    @staticmethod
    async def create_registration_request(
        session: AsyncSession,
        tenant_id: UUID,
        community_id: UUID,
        email: str,
        provider: RegistrationProvider,
        full_name: str,
        rut: str,
        address: str
    ) -> RegistrationRequest:
        """
        Crear una nueva solicitud de registro.

        Args:
            session: Sesión de base de datos
            tenant_id: ID del tenant
            community_id: ID de la comunidad
            email: Email del solicitante
            provider: Proveedor de autenticación
            full_name: Nombre completo
            rut: RUT
            address: Dirección

        Returns:
            RegistrationRequest: Solicitud creada
        """
        request = RegistrationRequest(
            tenant_id=tenant_id,
            community_id=community_id,
            email=email.lower(),
            provider=provider,
            full_name=full_name,
            rut=rut,
            address=address
        )
        session.add(request)
        await session.flush()
        return request

    @staticmethod
    async def find_pending_request_by_email(
        session: AsyncSession,
        email: str
    ) -> Optional[RegistrationRequest]:
        """
        Buscar solicitud pendiente por email.

        Args:
            session: Sesión de base de datos
            email: Email del solicitante

        Returns:
            RegistrationRequest: Solicitud encontrada o None
        """
        result = await session.execute(
            select(RegistrationRequest)
            .options(selectinload(RegistrationRequest.attachments))
            .where(
                and_(
                    RegistrationRequest.email == email.lower(),
                    RegistrationRequest.status == RegistrationStatus.PENDING
                )
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_pending_requests_for_community(
        session: AsyncSession,
        community_id: UUID
    ) -> List[RegistrationRequest]:
        """
        Obtener solicitudes pendientes para una comunidad.

        Args:
            session: Sesión de base de datos
            community_id: ID de la comunidad

        Returns:
            List[RegistrationRequest]: Lista de solicitudes pendientes
        """
        result = await session.execute(
            select(RegistrationRequest)
            .options(selectinload(RegistrationRequest.attachments))
            .where(
                and_(
                    RegistrationRequest.community_id == community_id,
                    RegistrationRequest.status == RegistrationStatus.PENDING
                )
            )
            .order_by(RegistrationRequest.created_at.desc())
        )
        return list(result.scalars().all())

    @staticmethod
    async def approve_registration_request(
        session: AsyncSession,
        request_id: UUID,
        decided_by: UUID,
        decision_notes: Optional[str] = None
    ) -> Optional[RegistrationRequest]:
        """
        Aprobar una solicitud de registro.

        Args:
            session: Sesión de base de datos
            request_id: ID de la solicitud
            decided_by: ID del moderador que decide
            decision_notes: Notas de la decisión

        Returns:
            RegistrationRequest: Solicitud actualizada o None si no se encontró
        """
        result = await session.execute(
            select(RegistrationRequest)
            .options(selectinload(RegistrationRequest.attachments))
            .where(RegistrationRequest.id == request_id)
        )
        request = result.scalar_one_or_none()

        if request:
            request.status = RegistrationStatus.APPROVED
            request.decided_by = decided_by
            request.decided_at = now_chile()
            request.decision_notes = decision_notes
            await session.flush()

        return request

    @staticmethod
    async def reject_registration_request(
        session: AsyncSession,
        request_id: UUID,
        decided_by: UUID,
        decision_notes: Optional[str] = None
    ) -> Optional[RegistrationRequest]:
        """
        Rechazar una solicitud de registro.

        Args:
            session: Sesión de base de datos
            request_id: ID de la solicitud
            decided_by: ID del moderador que decide
            decision_notes: Notas de la decisión

        Returns:
            RegistrationRequest: Solicitud actualizada o None si no se encontró
        """
        result = await session.execute(
            select(RegistrationRequest)
            .options(selectinload(RegistrationRequest.attachments))
            .where(RegistrationRequest.id == request_id)
        )
        request = result.scalar_one_or_none()

        if request:
            request.status = RegistrationStatus.REJECTED
            request.decided_by = decided_by
            request.decided_at = now_chile()
            request.decision_notes = decision_notes
            await session.flush()

        return request

    @staticmethod
    async def add_attachment_to_request(
        session: AsyncSession,
        request_id: UUID,
        url: str,
        kind: str
    ) -> RegistrationRequestAttachment:
        """
        Agregar un adjunto a una solicitud de registro.

        Args:
            session: Sesión de base de datos
            request_id: ID de la solicitud
            url: URL del archivo
            kind: Tipo de adjunto

        Returns:
            RegistrationRequestAttachment: Adjunto creado
        """
        attachment = RegistrationRequestAttachment(
            registration_request_id=request_id,
            url=url,
            kind=kind
        )
        session.add(attachment)
        await session.flush()
        return attachment

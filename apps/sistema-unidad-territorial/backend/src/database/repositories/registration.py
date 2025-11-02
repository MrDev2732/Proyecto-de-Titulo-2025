from typing import List, Optional
from uuid import UUID

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.database import (
    Community,
    RegistrationRequest,
    RegistrationRequestAttachment,
    RegistrationStatus,
    RegistrationProvider,
    User,
    RoleAssignment,
)
from src.database.utils import now_chile
from src.core.logging import get_logger


logger = get_logger(__name__)


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
    async def get_by_id_with_attachments(
        session: AsyncSession,
        request_id: UUID
    ) -> Optional[RegistrationRequest]:
        """
        Obtener una solicitud de registro por ID con todos sus archivos adjuntos.

        Args:
            session: Sesión de base de datos
            request_id: ID de la solicitud

        Returns:
            Optional[RegistrationRequest]: La solicitud con archivos adjuntos o None si no existe
        """
        result = await session.execute(
            select(RegistrationRequest)
            .options(
                selectinload(RegistrationRequest.attachments),
                selectinload(RegistrationRequest.community)
            )
            .where(RegistrationRequest.id == request_id)
        )
        return result.scalar_one_or_none()

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

    @staticmethod
    async def get_requests_for_user(
        session: AsyncSession,
        user_id: UUID,
        status: Optional[str] = None,
        search: Optional[str] = None,
        page: int = 1,
        per_page: int = 20
    ) -> List[RegistrationRequest]:
        """
        Obtener solicitudes de registro según los permisos del usuario.

        Determina automáticamente qué solicitudes puede ver el usuario basado en sus roles:
        - SUPERADMIN: Ve todas las solicitudes del sistema
        - ADMIN del tenant: Ve solicitudes de todas las comunidades de su municipalidad
        - MODERATOR de comunidad: Ve solo solicitudes de sus comunidades específicas

        Args:
            session: Sesión de base de datos
            user_id: ID del usuario actual
            status: Filtrar por estado (opcional)
            search: Buscar por email, nombre o RUT (opcional)
            page: Número de página
            per_page: Elementos por página

        Returns:
            List[RegistrationRequest]: Lista de solicitudes accesibles
        """
        # Obtener roles del usuario para determinar permisos
        user_roles_result = await session.execute(
            select(User)
            .options(
                selectinload(User.role_assignments).selectinload(RoleAssignment.role)
            )
            .where(User.id == user_id)
        )
        user = user_roles_result.scalar_one_or_none()
        
        if not user:
            return []

        # Construir query base
        query = select(RegistrationRequest).options(
            selectinload(RegistrationRequest.attachments),
            selectinload(RegistrationRequest.community)
        )

        # Verificar si es SUPERADMIN (acceso a todo)
        is_superadmin = any(
            assignment.role.name == "SUPERADMIN" and assignment.scope_type == 'system'
            for assignment in user.role_assignments
        )

        if not is_superadmin:
            # Obtener IDs de comunidades accesibles basado en roles
            accessible_community_ids = set()

            # ADMIN del tenant: acceso a todas las comunidades del tenant
            tenant_admin_tenant_ids = [
                assignment.scope_id 
                for assignment in user.role_assignments
                if assignment.role.name == "ADMIN" and assignment.scope_type == 'tenant'
            ]

            if tenant_admin_tenant_ids:
                # Obtener todas las comunidades de los tenants donde es admin
                tenant_communities_result = await session.execute(
                    select(Community.id)
                    .where(Community.tenant_id.in_(tenant_admin_tenant_ids))
                )
                accessible_community_ids.update(
                    community_id for community_id, in tenant_communities_result.fetchall()
                )

            # MODERATOR de comunidad: acceso solo a comunidades específicas
            community_moderator_ids = [
                assignment.scope_id
                for assignment in user.role_assignments
                if assignment.role.name == "MODERATOR" and assignment.scope_type == 'community'
            ]
            accessible_community_ids.update(community_moderator_ids)

            # Si no tiene acceso a ninguna comunidad, retornar lista vacía
            if not accessible_community_ids:
                return []

            # Filtrar por comunidades accesibles
            query = query.where(RegistrationRequest.community_id.in_(accessible_community_ids))

        # Aplicar filtros adicionales
        if status:
            try:
                status_enum = RegistrationStatus(status)
                query = query.where(RegistrationRequest.status == status_enum)
            except ValueError:
                # Status inválido, retornar lista vacía
                return []

        if search and search.strip():
            search_term = f"%{search.strip().lower()}%"
            query = query.where(
                and_(
                    RegistrationRequest.email.ilike(search_term) |
                    RegistrationRequest.full_name.ilike(search_term) |
                    RegistrationRequest.rut.ilike(search_term)
                )
            )

        # Ordenar por fecha de creación (más recientes primero)
        query = query.order_by(RegistrationRequest.created_at.desc())

        # Aplicar paginación
        offset = (page - 1) * per_page
        query = query.offset(offset).limit(per_page)

        # Ejecutar query
        result = await session.execute(query)
        return list(result.scalars().all())

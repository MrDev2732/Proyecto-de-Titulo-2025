"""
Repository para manejo de proyectos vecinales.

Contiene todas las operaciones relacionadas con el modelo Project.
"""

from typing import List, Optional, Tuple
from uuid import UUID

from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.database.models.projects import Project, ProjectAttachment
from src.database.models.role_assignment import RoleAssignment
from src.database.models.auth import Role
from src.core.logging import get_logger


logger = get_logger(__name__)


class ProjectRepository:
    """Repository para operaciones con proyectos vecinales."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, project: Project) -> Project:
        """
        Crear un nuevo proyecto.

        Args:
            project: Instancia del proyecto a crear

        Returns:
            Project: Proyecto creado
        """
        self.db.add(project)
        await self.db.flush()
        await self.db.commit()
        await self.db.refresh(project)
        logger.info(f"✅ Created project {project.id} in community {project.community_id}")
        return project

    async def get(self, project_id: UUID) -> Optional[Project]:
        """
        Obtener un proyecto por su ID con sus adjuntos.

        Args:
            project_id: ID del proyecto

        Returns:
            Project: Proyecto encontrado o None
        """
        result = await self.db.execute(
            select(Project)
            .options(
                selectinload(Project.community),
                selectinload(Project.requesting_user),
                selectinload(Project.attachments)
            )
            .where(
                and_(
                    Project.id == project_id,
                    Project.deleted_at.is_(None)
                )
            )
        )
        return result.scalar_one_or_none()

    async def list_all_paginated(
        self,
        tenant_id: UUID,
        page: int = 1,
        per_page: int = 10,
        status_filter: Optional[str] = None,
        community_id_filter: Optional[UUID] = None
    ) -> Tuple[List[Project], int, int]:
        """
        Listar todos los proyectos con paginación (para administradores).

        Args:
            tenant_id: ID del tenant para filtrar
            page: Número de página
            per_page: Elementos por página
            status_filter: Filtro opcional por estado
            community_id_filter: Filtro opcional por comunidad

        Returns:
            Tupla de (lista de proyectos, total de elementos, total de páginas)
        """
        # Construir filtros base
        filters = [
            Project.tenant_id == tenant_id,
            Project.deleted_at.is_(None)
        ]

        # Agregar filtros opcionales
        if status_filter:
            filters.append(Project.status == status_filter)
        if community_id_filter:
            filters.append(Project.community_id == community_id_filter)

        # Query base con carga de relaciones
        base_query = select(Project).options(
            selectinload(Project.community),
            selectinload(Project.requesting_user),
            selectinload(Project.attachments)
        ).where(
            and_(*filters)
        ).order_by(Project.created_at.desc())

        # Contar total
        count_query = select(func.count()).select_from(Project).where(
            and_(*filters)
        )
        count_result = await self.db.execute(count_query)
        total = count_result.scalar()

        # Calcular paginación
        total_pages = (total + per_page - 1) // per_page if total > 0 else 0
        offset = (page - 1) * per_page

        # Ejecutar query con paginación
        paginated_query = base_query.offset(offset).limit(per_page)
        result = await self.db.execute(paginated_query)
        projects = result.scalars().all()

        return list(projects), total, total_pages

    async def update_status(
        self,
        project_id: UUID,
        status: str,
        observations: Optional[str] = None
    ) -> Optional[Project]:
        """
        Actualizar el estado de un proyecto.

        Args:
            project_id: ID del proyecto
            status: Nuevo estado
            observations: Observaciones opcionales

        Returns:
            Project: Proyecto actualizado o None si no se encontró
        """
        project = await self.get(project_id)
        if not project:
            return None

        project.status = status
        if observations is not None:
            project.observations = observations

        await self.db.flush()
        await self.db.commit()
        await self.db.refresh(project)

        logger.info(f"✅ Updated project {project_id} status to {status}")
        return project

    async def disable(self, project_id: UUID) -> Optional[Project]:
        """
        Deshabilitar un proyecto (soft delete).

        Args:
            project_id: ID del proyecto

        Returns:
            Project: Proyecto deshabilitado o None si no se encontró
        """
        from src.database.utils import now_chile
        project = await self.get(project_id)
        if project:
            project.deleted_at = now_chile()
            await self.db.flush()
            await self.db.commit()
            await self.db.refresh(project)
            logger.info(f"✅ Disabled project {project_id}")
        return project

    async def get_user_community_role(
        self,
        user_id: UUID
    ) -> Optional[RoleAssignment]:
        """
        Obtener el rol de comunidad de un usuario (MODERATOR).

        Verifica si el usuario tiene un rol MODERATOR asignado a nivel de comunidad,
        lo cual le permite proponer proyectos en esa comunidad.

        Args:
            user_id: ID del usuario

        Returns:
            RoleAssignment: Asignación de rol encontrada o None
        """
        result = await self.db.execute(
            select(RoleAssignment)
            .join(Role, RoleAssignment.role_id == Role.id)
            .where(
                and_(
                    RoleAssignment.user_id == user_id,
                    Role.name == "MODERATOR",
                    RoleAssignment.scope_type == 'community',
                    RoleAssignment.deleted_at.is_(None)
                )
            )
        )
        return result.scalar_one_or_none()

    async def add_attachment(
        self,
        project_id: UUID,
        bucket: str,
        storage_key: str,
        sha256: str,
        mime_type: str,
        original_filename: Optional[str],
        tenant_id: UUID
    ) -> ProjectAttachment:
        """
        Agregar un adjunto a un proyecto.

        Args:
            project_id: ID del proyecto
            bucket: Bucket de almacenamiento
            storage_key: Clave de almacenamiento
            sha256: Hash SHA256 del archivo
            mime_type: Tipo MIME del archivo
            original_filename: Nombre original del archivo
            tenant_id: ID del tenant

        Returns:
            ProjectAttachment: Adjunto creado
        """
        attachment = ProjectAttachment(
            project_id=project_id,
            bucket=bucket,
            storage_key=storage_key,
            sha256=sha256,
            mime_type=mime_type,
            original_filename=original_filename,
            tenant_id=tenant_id
        )
        self.db.add(attachment)
        await self.db.flush()
        logger.info(f"✅ Added attachment {attachment.id} to project {project_id}")
        return attachment

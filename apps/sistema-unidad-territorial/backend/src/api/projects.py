"""
Endpoints de proyectos vecinales para la API.

Solo los miembros de la junta de vecinos (con board_role) pueden proponer proyectos.
Los administradores pueden listar y aprobar/rechazar proyectos.
"""
from uuid import UUID
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query, Path, File, UploadFile, Form
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.session import get_db_session
from src.database.models import User
from src.database.models.projects import Project
from src.database.enums import ProjectStatus
from src.schemas import ErrorResponse
from src.core.logging import get_logger
from src.core.dependencies import get_current_active_user
from src.database.repositories.projects import ProjectRepository
from src.schemas.projects import (
    ProjectResponse,
    ProjectListResponse,
    ProjectApprovalRequest,
    ProjectAttachmentResponse
)
from src.services.project_file import ProjectFileService


logger = get_logger(__name__)
router = APIRouter(prefix="/projects", tags=["Proyectos Vecinales"])


@router.post(
    "/",
    response_model=ProjectResponse,
    summary="Proponer proyecto vecinal con archivos adjuntos",
    description="Permite a cualquier usuario con membresía aprobada proponer un proyecto en su comunidad con archivos adjuntos opcionales",
    status_code=status.HTTP_201_CREATED,
    responses={
        201: {"description": "Proyecto creado exitosamente"},
        403: {"model": ErrorResponse, "description": "Usuario no tiene membresía aprobada en una comunidad"},
        400: {"model": ErrorResponse, "description": "Usuario tiene múltiples membresías"},
        413: {"model": ErrorResponse, "description": "Archivo muy grande"},
        500: {"model": ErrorResponse, "description": "Error interno del servidor"}
    }
)
async def create_project(
    title: str = Form(..., description="Título del proyecto", min_length=5, max_length=200),
    description: str = Form(..., description="Descripción detallada del proyecto", min_length=20),
    attachments: Optional[List[UploadFile]] = File(default=None, description="Archivos adjuntos opcionales (imágenes, PDFs, documentos)"),
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db_session)
) -> ProjectResponse:
    """
    Proponer un proyecto en una comunidad.

    **Requisitos:**
    - El usuario debe tener una membresía aprobada en una comunidad
    - Cualquier residente puede proponer proyectos en su comunidad

    **Restricciones:**
    - Solo pueden proponer proyectos los usuarios con membresía aprobada
    - El usuario puede proponer proyectos solo en su comunidad asignada

    **Estado inicial:**
    - El proyecto se crea con estado PENDING
    - Requiere aprobación de un administrador (rol ADMIN) para cambiar de estado
    """
    try:
        # Validar que el usuario tiene tenant
        user_tenant_id = current_user.tenant_id
        if not user_tenant_id:
            logger.warning(f"⚠️ User {current_user.email} has no tenant_id")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Usuario no tiene un tenant asignado"
            )

        # Verificar que el usuario tiene una membresía aprobada en una comunidad
        repo = ProjectRepository(session)
        membership = await repo.get_user_community_membership(user_id=current_user.id)

        if not membership:
            logger.warning(
                f"⚠️ User {current_user.email} attempted to create project without approved membership"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Debes tener una membresía aprobada en una comunidad para proponer proyectos"
            )

        # El community_id viene de la membresía del usuario
        community_id = membership.community_id

        # Crear el proyecto
        project = Project(
            title=title,
            description=description,
            status=ProjectStatus.PENDING.value,
            community_id=community_id,
            requesting_user_id=current_user.id,
            tenant_id=user_tenant_id
        )
        project = await repo.create(project)

        logger.info(
            f"✅ User {current_user.email} (community: {community_id}) "
            f"created project {project.id}"
        )

        # Procesar archivos adjuntos si existen
        attachment_responses = []
        if attachments:
            logger.info(f"📎 Processing {len(attachments)} attachments for project {project.id}")

            for file in attachments:
                try:
                    # Guardar archivo usando el servicio
                    file_info = await ProjectFileService.save_project_file(
                        project_id=project.id,
                        file=file
                    )

                    # Crear registro en la base de datos
                    attachment = await repo.add_attachment(
                        project_id=project.id,
                        bucket=file_info["bucket"],
                        storage_key=file_info["storage_key"],
                        sha256=file_info["sha256"],
                        mime_type=file_info["mime_type"],
                        original_filename=file_info["original_filename"],
                        tenant_id=user_tenant_id
                    )

                    # Preparar respuesta del attachment
                    attachment_responses.append(
                        ProjectAttachmentResponse(
                            id=str(attachment.id),
                            original_filename=attachment.original_filename,
                            mime_type=attachment.mime_type,
                            file_url=f"/files/{file_info['storage_key']}",
                            created_at=attachment.created_at
                        )
                    )

                    logger.info(f"✅ Attachment {attachment.id} added to project {project.id}")

                except HTTPException:
                    # Si es un error de validación de archivo, propagarlo
                    raise
                except Exception as e:
                    logger.error(f"❌ Error processing attachment {file.filename}: {e}")
                    # Continuar con los demás archivos
                    continue

        return ProjectResponse(
            id=str(project.id),
            title=project.title,
            description=project.description,
            status=project.status,
            observations=project.observations,
            community_id=str(project.community_id),
            requesting_user_id=str(project.requesting_user_id),
            created_at=project.created_at,
            updated_at=project.updated_at,
            attachments=attachment_responses
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error creating project: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno del servidor al crear el proyecto"
        )


@router.get(
    "/",
    response_model=ProjectListResponse,
    summary="Listar proyectos",
    description="Permite listar proyectos según el rol del usuario (ADMIN ve todo el tenant, MODERATOR solo su comunidad)",
    responses={
        200: {"description": "Lista de proyectos obtenida exitosamente"},
        403: {"model": ErrorResponse, "description": "Usuario no tiene permisos"},
        500: {"model": ErrorResponse, "description": "Error interno del servidor"}
    }
)
async def list_all_projects(
    page: int = Query(1, ge=1, description="Número de página"),
    per_page: int = Query(10, ge=1, le=100, description="Elementos por página"),
    status_filter: str = Query(None, description="Filtrar por estado (PENDING, IN_PROGRESS, COMPLETED, REJECTED)"),
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db_session)
) -> ProjectListResponse:
    """
    Listar proyectos según el rol del usuario.

    **Roles permitidos:**
    - **ADMIN**: Ve todos los proyectos del tenant
    - **MODERATOR**: Ve solo los proyectos de su comunidad

    **Parámetros:**
    - **page**: Número de página (por defecto 1)
    - **per_page**: Elementos por página (por defecto 10, máximo 100)
    - **status_filter**: Filtrar por estado específico (opcional)

    **Filtros aplicados:**
    - ADMIN: Proyectos de todo el tenant
    - MODERATOR: Solo proyectos de su comunidad asignada
    - Ordenados por fecha de creación descendente (más recientes primero)
    """
    try:
        # Validar tenant
        user_tenant_id = current_user.tenant_id
        if not user_tenant_id:
            logger.warning(f"⚠️ User {current_user.email} has no tenant_id")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Usuario no tiene un tenant asignado"
            )

        # Validar status_filter si se proporciona
        if status_filter and status_filter not in [s.value for s in ProjectStatus]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Estado inválido. Valores permitidos: {', '.join([s.value for s in ProjectStatus])}"
            )

        # Obtener roles del usuario
        user_roles = [assignment.role.name for assignment in current_user.role_assignments]

        # Determinar el filtro de comunidad según el rol
        community_filter = None
        role_type = "UNKNOWN"

        if "ADMIN" in user_roles or "SUPERADMIN" in user_roles:
            # Admin ve todos los proyectos del tenant
            role_type = "ADMIN"
            community_filter = None
        else:
            # Verificar si es MODERATOR de alguna comunidad
            repo = ProjectRepository(session)
            role_assignment = await repo.get_user_community_role(user_id=current_user.id)

            if not role_assignment:
                logger.warning(
                    f"⚠️ User {current_user.email} attempted to list projects without ADMIN or MODERATOR role"
                )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="No tienes permisos para ver proyectos. Se requiere rol ADMIN o MODERATOR"
                )

            # Moderator solo ve proyectos de su comunidad
            role_type = "MODERATOR"
            community_filter = role_assignment.scope_id

        # Obtener proyectos paginados
        repo = ProjectRepository(session)
        projects_list, total, total_pages = await repo.list_all_paginated(
            tenant_id=user_tenant_id,
            page=page,
            per_page=per_page,
            status_filter=status_filter,
            community_id_filter=community_filter
        )

        # Convertir a response con attachments
        projects_responses = []
        for project in projects_list:
            attachment_responses = [
                ProjectAttachmentResponse(
                    id=str(attachment.id),
                    original_filename=attachment.original_filename,
                    mime_type=attachment.mime_type,
                    file_url=f"/files/{attachment.storage_key}",
                    created_at=attachment.created_at
                )
                for attachment in project.attachments
            ]

            projects_responses.append(
                ProjectResponse(
                    id=str(project.id),
                    title=project.title,
                    description=project.description,
                    status=project.status,
                    observations=project.observations,
                    community_id=str(project.community_id),
                    requesting_user_id=str(project.requesting_user_id),
                    created_at=project.created_at,
                    updated_at=project.updated_at,
                    attachments=attachment_responses
                )
            )

        filter_msg = ""
        if status_filter:
            filter_msg += f" with status={status_filter}"
        if community_filter:
            filter_msg += f" from community {community_filter}"

        logger.info(
            f"✅ {role_type} {current_user.email} retrieved {len(projects_responses)} projects "
            f"(page {page}/{total_pages}, total {total}){filter_msg}"
        )

        return ProjectListResponse(
            projects=projects_responses,
            total=total,
            page=page,
            per_page=per_page,
            total_pages=total_pages
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error listing projects: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno del servidor al obtener los proyectos"
        )


@router.get(
    "/my-proposals",
    response_model=ProjectListResponse,
    summary="Listar mis propuestas de proyectos",
    description="Permite a un usuario ver todas las propuestas de proyectos que ha creado",
    responses={
        200: {"description": "Lista de propuestas obtenida exitosamente"},
        403: {"model": ErrorResponse, "description": "Usuario no tiene tenant asignado"},
        500: {"model": ErrorResponse, "description": "Error interno del servidor"}
    }
)
async def list_my_proposals(
    page: int = Query(1, ge=1, description="Número de página"),
    per_page: int = Query(10, ge=1, le=100, description="Elementos por página"),
    status_filter: str = Query(None, description="Filtrar por estado (PENDING, IN_PROGRESS, COMPLETED, REJECTED)"),
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db_session)
) -> ProjectListResponse:
    """
    Listar las propuestas de proyectos creadas por el usuario actual.

    **Funcionalidad:**
    - Muestra solo los proyectos propuestos por el usuario autenticado
    - Soporta paginación y filtro por estado
    - Ordenados por fecha de creación descendente (más recientes primero)

    **Parámetros:**
    - **page**: Número de página (por defecto 1)
    - **per_page**: Elementos por página (por defecto 10, máximo 100)
    - **status_filter**: Filtrar por estado específico (opcional)
    """
    try:
        # Validar tenant
        user_tenant_id = current_user.tenant_id
        if not user_tenant_id:
            logger.warning(f"⚠️ User {current_user.email} has no tenant_id")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Usuario no tiene un tenant asignado"
            )

        # Validar status_filter si se proporciona
        if status_filter and status_filter not in [s.value for s in ProjectStatus]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Estado inválido. Valores permitidos: {', '.join([s.value for s in ProjectStatus])}"
            )

        # Obtener proyectos del usuario
        repo = ProjectRepository(session)
        projects_list, total, total_pages = await repo.list_by_user_paginated(
            user_id=current_user.id,
            tenant_id=user_tenant_id,
            page=page,
            per_page=per_page,
            status_filter=status_filter
        )

        # Convertir a response con attachments
        projects_responses = []
        for project in projects_list:
            attachment_responses = [
                ProjectAttachmentResponse(
                    id=str(attachment.id),
                    original_filename=attachment.original_filename,
                    mime_type=attachment.mime_type,
                    file_url=f"/files/{attachment.storage_key}",
                    created_at=attachment.created_at
                )
                for attachment in project.attachments
            ]

            projects_responses.append(
                ProjectResponse(
                    id=str(project.id),
                    title=project.title,
                    description=project.description,
                    status=project.status,
                    observations=project.observations,
                    community_id=str(project.community_id),
                    requesting_user_id=str(project.requesting_user_id),
                    created_at=project.created_at,
                    updated_at=project.updated_at,
                    attachments=attachment_responses
                )
            )

        filter_msg = f" with status={status_filter}" if status_filter else ""

        logger.info(
            f"✅ User {current_user.email} retrieved their {len(projects_responses)} proposals "
            f"(page {page}/{total_pages}, total {total}){filter_msg}"
        )

        return ProjectListResponse(
            projects=projects_responses,
            total=total,
            page=page,
            per_page=per_page,
            total_pages=total_pages
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error listing user proposals: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno del servidor al obtener tus propuestas"
        )


@router.get(
    "/{project_id}",
    response_model=ProjectResponse,
    summary="Obtener detalle de un proyecto",
    description="Obtiene el detalle completo de un proyecto incluyendo sus archivos adjuntos",
    responses={
        200: {"description": "Proyecto obtenido exitosamente"},
        403: {"model": ErrorResponse, "description": "Usuario no tiene permisos"},
        404: {"model": ErrorResponse, "description": "Proyecto no encontrado"},
        500: {"model": ErrorResponse, "description": "Error interno del servidor"}
    }
)
async def get_project(
    project_id: UUID = Path(..., description="ID del proyecto"),
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db_session)
) -> ProjectResponse:
    """
    Obtener el detalle completo de un proyecto.

    **Roles permitidos:**
    - **ADMIN/SUPERADMIN**: Puede ver cualquier proyecto del tenant
    - **MODERATOR**: Puede ver solo proyectos de su comunidad

    **Respuesta incluye:**
    - Información básica del proyecto
    - Lista de archivos adjuntos con sus URLs de descarga
    """
    try:
        # Validar tenant
        user_tenant_id = current_user.tenant_id
        if not user_tenant_id:
            logger.warning(f"⚠️ User {current_user.email} has no tenant_id")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Usuario no tiene un tenant asignado"
            )

        # Obtener el proyecto
        repo = ProjectRepository(session)
        project = await repo.get(project_id)

        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Proyecto no encontrado"
            )

        # Validar que pertenece al tenant del usuario
        if project.tenant_id != user_tenant_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Proyecto no encontrado"
            )

        # Verificar permisos según rol
        user_roles = [assignment.role.name for assignment in current_user.role_assignments]

        # Si es ADMIN o SUPERADMIN, puede ver cualquier proyecto
        if "ADMIN" not in user_roles and "SUPERADMIN" not in user_roles:
            # Si no es admin, verificar que sea MODERATOR de la comunidad del proyecto
            role_assignment = await repo.get_user_community_role(user_id=current_user.id)

            if not role_assignment or role_assignment.scope_id != project.community_id:
                logger.warning(
                    f"⚠️ User {current_user.email} attempted to access project {project_id} "
                    f"from unauthorized community"
                )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="No tienes permisos para ver este proyecto"
                )

        # Preparar respuesta con attachments
        attachment_responses = [
            ProjectAttachmentResponse(
                id=str(attachment.id),
                original_filename=attachment.original_filename,
                mime_type=attachment.mime_type,
                file_url=f"/files/{attachment.storage_key}",
                created_at=attachment.created_at
            )
            for attachment in project.attachments
        ]

        logger.info(
            f"✅ User {current_user.email} retrieved project {project_id} "
            f"with {len(attachment_responses)} attachments"
        )

        return ProjectResponse(
            id=str(project.id),
            title=project.title,
            description=project.description,
            status=project.status,
            observations=project.observations,
            community_id=str(project.community_id),
            requesting_user_id=str(project.requesting_user_id),
            created_at=project.created_at,
            updated_at=project.updated_at,
            attachments=attachment_responses
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error getting project: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno del servidor al obtener el proyecto"
        )


@router.patch(
    "/{project_id}/status",
    response_model=ProjectResponse,
    summary="Aprobar o rechazar proyecto (Admin)",
    description="Permite a los administradores del tenant aprobar o rechazar un proyecto vecinal",
    responses={
        200: {"description": "Estado del proyecto actualizado exitosamente"},
        400: {"model": ErrorResponse, "description": "Estado inválido"},
        403: {"model": ErrorResponse, "description": "Usuario no tiene permisos de administrador"},
        404: {"model": ErrorResponse, "description": "Proyecto no encontrado"},
        500: {"model": ErrorResponse, "description": "Error interno del servidor"}
    }
)
async def update_project_status(
    project_id: UUID = Path(..., description="ID del proyecto"),
    approval_data: ProjectApprovalRequest = ...,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db_session)
) -> ProjectResponse:
    """
    Actualizar el estado de un proyecto (aprobar o rechazar).

    **Requiere:** Rol ADMIN a nivel de tenant

    **Estados válidos:**
    - **IN_PROGRESS**: Aprobar el proyecto (pasa de PENDING a IN_PROGRESS)
    - **COMPLETED**: Marcar proyecto como completado
    - **REJECTED**: Rechazar el proyecto

    **Notas:**
    - Se pueden agregar observaciones al cambiar el estado
    - El proyecto debe pertenecer al mismo tenant del administrador
    - Solo usuarios con rol ADMIN pueden cambiar el estado de proyectos
    """
    try:
        # Validar tenant
        user_tenant_id = current_user.tenant_id
        if not user_tenant_id:
            logger.warning(f"⚠️ User {current_user.email} has no tenant_id")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Usuario no tiene un tenant asignado"
            )

        # Verificar que el usuario tiene rol ADMIN
        user_roles = [assignment.role.name for assignment in current_user.role_assignments]

        if "ADMIN" not in user_roles and "SUPERADMIN" not in user_roles:
            logger.warning(
                f"⚠️ User {current_user.email} attempted to update project status without ADMIN role"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Solo los administradores pueden aprobar o rechazar proyectos"
            )

        # Validar estado
        if approval_data.status not in [s.value for s in ProjectStatus]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Estado inválido. Valores permitidos: {', '.join([s.value for s in ProjectStatus])}"
            )

        # Obtener el proyecto
        repo = ProjectRepository(session)
        project = await repo.get(project_id)

        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Proyecto no encontrado"
            )

        # Validar que el proyecto pertenece al tenant del admin
        if project.tenant_id != user_tenant_id:
            logger.warning(
                f"⚠️ Admin {current_user.email} attempted to update project {project_id} "
                f"from different tenant"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tienes permisos para modificar este proyecto"
            )

        # Actualizar el estado
        old_status = project.status
        project = await repo.update_status(
            project_id=project_id,
            status=approval_data.status,
            observations=approval_data.observations
        )

        action = "aprobó" if approval_data.status == ProjectStatus.IN_PROGRESS.value else \
                 "completó" if approval_data.status == ProjectStatus.COMPLETED.value else \
                 "rechazó"
        
        logger.info(
            f"✅ Admin {current_user.email} {action} project {project_id} "
            f"(status: {old_status} → {approval_data.status})"
        )

        # Preparar respuesta con attachments
        attachment_responses = [
            ProjectAttachmentResponse(
                id=str(attachment.id),
                original_filename=attachment.original_filename,
                mime_type=attachment.mime_type,
                file_url=f"/files/{attachment.storage_key}",
                created_at=attachment.created_at
            )
            for attachment in project.attachments
        ]

        return ProjectResponse(
            id=str(project.id),
            title=project.title,
            description=project.description,
            status=project.status,
            observations=project.observations,
            community_id=str(project.community_id),
            requesting_user_id=str(project.requesting_user_id),
            created_at=project.created_at,
            updated_at=project.updated_at,
            attachments=attachment_responses
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error updating project status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno del servidor al actualizar el proyecto"
        )

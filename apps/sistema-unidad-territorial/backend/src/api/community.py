"""
Endpoints de comunidades y solicitudes de registro para la API.
"""

from typing import List, Optional, Union
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.session import get_db_session
from src.schemas.community_schemas import (
    CommunityResponse,
    RegistrationRequestResponse,
    RegistrationRequestListResponse,
    RegistrationRequestDecision,
    ResidentMembershipResponse,
    TenantResponse,
    TenantWithCommunitiesResponse,
    TenantsAndCommunitiesResponse,
    TenantListResponse,
    CommunitiesByTenantResponse,
)
from src.schemas.auth_schemas import ErrorResponse
from src.core.dependencies import get_current_active_user, require_community_access, require_registration_request_access
from src.database import User
from src.database.repositories.community_repository import (
    CommunityRepository,
    RegistrationRequestRepository,
    ResidentMembershipRepository,
)
from src.database.repositories.tenant_repository import TenantRepository
from src.database.utils import ValidationUtils, RutChile
from src.services.community_service import CommunityService
from src.services.file_service import FileService
from src.services.registration_approval_service import RegistrationApprovalService
from src.services.google_maps_service import GoogleMapsService
from src.core.logging import get_logger


logger = get_logger(__name__)

# Router para endpoints de comunidades
router = APIRouter(prefix="/communities", tags=["Comunidades"])


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
    "/tenants",
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
    "/tenants/{tenant_id}/communities",
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


@router.post(
    "/registration-requests",
    response_model=RegistrationRequestResponse,
    summary="Crear solicitud de registro a comunidad con documentos",
    description="Crea una nueva solicitud de registro para unirse a una comunidad específica con documentos adjuntos",
    responses={
        400: {"model": ErrorResponse, "description": "Solicitud ya existe o datos inválidos"},
        404: {"model": ErrorResponse, "description": "Comunidad no encontrada"},
        413: {"model": ErrorResponse, "description": "Archivo muy grande"},
        422: {"model": ErrorResponse, "description": "Datos de entrada inválidos"}
    }
)
async def create_registration_request(
    # Datos básicos como form data
    tenant_id: UUID = Form(..., description="ID del tenant (municipalidad)"),
    community_id: UUID = Form(..., description="ID de la comunidad donde registrarse"),
    email: str = Form(..., description="Email del solicitante"),
    full_name: str = Form(..., description="Nombre completo del solicitante"),
    rut: str = Form(..., description="RUT del solicitante"),
    address: str = Form(..., description="Dirección del solicitante"),
    provider: str = Form(default="google", description="Proveedor de autenticación"),

    # Archivos requeridos
    id_card_front: UploadFile = File(..., description="Foto frontal del carnet de identidad"),
    id_card_back: UploadFile = File(..., description="Foto trasera del carnet de identidad"),
    utility_bill: UploadFile = File(..., description="Foto de cuenta de servicios (luz, agua, etc.)"),

    # Archivos adicionales opcionales
    additional_files: Optional[List[Union[UploadFile, str]]] = File(default=None, description="Documentos adicionales opcionales"),

    session: AsyncSession = Depends(get_db_session)
) -> RegistrationRequestResponse:
    """
    Crear una nueva solicitud de registro a una comunidad con documentos.

    **Datos básicos (Form Data):**
    - **tenant_id**: ID del tenant (municipalidad)
    - **community_id**: ID de la comunidad donde registrarse
    - **email**: Email del solicitante
    - **full_name**: Nombre completo
    - **rut**: RUT chileno
    - **address**: Dirección del solicitante
    - **provider**: Proveedor de autenticación (Google por defecto)

    **Archivos requeridos (multipart/form-data):**
    - **id_card_front**: Foto frontal del carnet de identidad (JPG, PNG)
    - **id_card_back**: Foto trasera del carnet de identidad (JPG, PNG)
    - **utility_bill**: Foto de cuenta de servicios - luz, agua, etc. (JPG, PNG, PDF)

    **Archivos opcionales:**
    - **additional_files**: Lista de documentos adicionales (contratos, etc.)

    Los archivos se guardan localmente en: `uploads/evidence-{request_id}/`
    La solicitud quedará en estado PENDING hasta que un moderador la apruebe.
    """
    # ========================================
    # VALIDACIONES DE DATOS DE ENTRADA
    # ========================================

    # Validar email
    email_valid, email_error = ValidationUtils.validate_email(email)
    if not email_valid:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Email inválido: {email_error}"
        )

    # Validar nombre completo
    name_valid, name_error = ValidationUtils.validate_full_name(full_name)
    if not name_valid:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Nombre inválido: {name_error}"
        )

    # Validar RUT
    rut_valid, formatted_rut, rut_error = RutChile.validate_rut(rut)
    if not rut_valid:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"RUT inválido: {rut_error}"
        )

    # Validar dirección
    address_valid, address_error = ValidationUtils.validate_address(address)
    if not address_valid:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Dirección inválida: {address_error}"
        )

    # Validación adicional con Google Maps (si está habilitada)
    try:
        maps_valid, maps_details = await GoogleMapsService.validate_address_in_chile(address)
        if not maps_valid and maps_details.get("status") not in ["API_KEY_NOT_CONFIGURED", "QUERY_LIMIT_EXCEEDED"]:
            logger.warning(f"Google Maps validation failed for address: {address} - {maps_details.get('message')}")
            # No bloquear el registro, solo logear la advertencia
            # En producción podrías decidir si bloquear o no según el caso
    except Exception as e:
        logger.error(f"Error en validación de Google Maps: {e}")
        # Continuar sin bloquear el registro

    # Normalizar datos validados
    email = email.strip().lower()
    full_name = full_name.strip()
    rut = formatted_rut  # Usar el RUT formateado correctamente
    address = address.strip()

    logger.info(f"📋 Validación exitosa para solicitud de registro: {email}, RUT: {rut}")

    # Filtrar archivos válidos de additional_files
    # Esto maneja el caso cuando vienen strings vacíos en lugar de archivos
    valid_additional_files = None
    if additional_files is not None:
        # Filtrar solo los archivos válidos (UploadFile con nombre)
        valid_files = []
        for file in additional_files:
            if isinstance(file, UploadFile) and file.filename and file.filename.strip():
                valid_files.append(file)
            # Ignorar strings vacíos y archivos sin nombre

        # Si no hay archivos válidos, convertir a None
        valid_additional_files = valid_files if valid_files else None
    # Verificar que el tenant existe
    tenant = await TenantRepository.get_tenant_by_id(session, tenant_id)
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant no encontrado"
        )

    # Verificar que la comunidad existe y pertenece al tenant
    community_belongs_to_tenant = await CommunityRepository.validate_community_belongs_to_tenant(
        session, community_id, tenant_id
    )
    if not community_belongs_to_tenant:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La comunidad no pertenece al tenant especificado"
        )

    # Verificar que no exista una solicitud pendiente para este email
    existing_request = await RegistrationRequestRepository.find_pending_request_by_email(
        session, email
    )

    if existing_request:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ya existe una solicitud de registro pendiente para este email"
        )

    # Generar ID único para la solicitud (para crear carpeta de evidencia)
    request_id = uuid4()

    try:
        # Guardar archivos de evidencia
        saved_files = await FileService.save_multiple_evidence_files(
            request_id=request_id,
            id_card_front=id_card_front,
            id_card_back=id_card_back,
            utility_bill=utility_bill,
            additional_files=valid_additional_files
        )

        # Crear la solicitud de registro
        registration_request = await RegistrationRequestRepository.create_registration_request(
            session=session,
            tenant_id=tenant_id,
            community_id=community_id,
            email=email,
            provider=provider,
            full_name=full_name,
            rut=rut,
            address=address
        )

        # Actualizar el ID de la solicitud para que coincida con el directorio
        registration_request.id = request_id

        # Agregar documentos requeridos con las rutas locales
        required_documents = [
            (saved_files['id_card_front_url'], "id_card_front"),
            (saved_files['id_card_back_url'], "id_card_back"),
            (saved_files['utility_bill_url'], "utility_bill")
        ]

        for file_path, kind in required_documents:
            await RegistrationRequestRepository.add_attachment_to_request(
                session=session,
                request_id=registration_request.id,
                url=file_path,
                kind=kind
            )

        # Agregar archivos adicionales si existen
        for additional_path in saved_files.get('additional_files', []):
            await RegistrationRequestRepository.add_attachment_to_request(
                session=session,
                request_id=registration_request.id,
                url=additional_path,
                kind="other"
            )

        await session.commit()

        # Refrescar el objeto para cargar las relaciones
        await session.refresh(registration_request, ["attachments"])

        total_files = len(required_documents) + len(saved_files.get('additional_files', []))
        logger.info(f"✅ Created registration request for {email} to community {community_id} with {total_files} documents in evidence-{request_id}")

        return RegistrationRequestResponse.model_validate(registration_request)

    except Exception as e:
        # Si hay error, limpiar archivos guardados
        FileService.cleanup_evidence_directory(request_id)
        logger.error(f"❌ Error creating registration request: {e}")
        raise e


@router.get(
    "/{community_id}/registration-requests",
    response_model=RegistrationRequestListResponse,
    summary="Listar solicitudes de registro de una comunidad",
    description="Obtiene todas las solicitudes de registro pendientes para una comunidad (solo usuarios con permisos específicos)",
    responses={
        403: {"model": ErrorResponse, "description": "Sin permisos para ver solicitudes de esta comunidad"},
        404: {"model": ErrorResponse, "description": "Comunidad no encontrada"}
    }
)
async def list_community_registration_requests(
    community_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_community_access)
) -> RegistrationRequestListResponse:
    """
    Listar solicitudes de registro pendientes para una comunidad.

    Solo usuarios con permisos específicos sobre esta comunidad pueden acceder:
    - SUPERADMIN (acceso global)
    - ADMIN del tenant que contiene la comunidad  
    - MODERATOR específicamente de esta comunidad

    Retorna todas las solicitudes en estado PENDING con sus adjuntos.
    """
    requests = await RegistrationRequestRepository.get_pending_requests_for_community(
        session, community_id
    )

    return RegistrationRequestListResponse(
        requests=[RegistrationRequestResponse.model_validate(req) for req in requests],
        total=len(requests)
    )


@router.post(
    "/registration-requests/{request_id}/approve",
    response_model=RegistrationRequestResponse,
    summary="Aprobar solicitud de registro",
    description="Aprueba una solicitud de registro y crea la membresía del usuario",
    responses={
        403: {"model": ErrorResponse, "description": "Sin permisos para aprobar solicitudes"},
        404: {"model": ErrorResponse, "description": "Solicitud no encontrada"},
        400: {"model": ErrorResponse, "description": "Solicitud ya procesada"}
    }
)
async def approve_registration_request(
    request_id: UUID,
    decision_data: RegistrationRequestDecision,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_registration_request_access)
) -> RegistrationRequestResponse:
    """
    Aprobar una solicitud de registro.

    - **decision_notes**: Notas opcionales del moderador

    Al aprobar:
    1. La dependencia valida automáticamente permisos sobre la comunidad
    2. Se actualiza el estado de la solicitud a APPROVED
    3. Se crea el usuario si no existe con contraseña aleatoria
    4. Se crea el registro de residente con los datos de la solicitud
    5. Se asocian las evidencias de la solicitud al residente
    6. Se crea una membresía para el usuario en la comunidad
    7. Se registra quién y cuándo aprobó la solicitud
    """
    # La validación de permisos ya se hizo en la dependencia
    # Usar el servicio para manejar toda la lógica de aprobación
    approved_request = await RegistrationApprovalService.approve_registration_request(
        session=session,
        request_id=request_id,
        decided_by=current_user.id,
        decision_notes=decision_data.decision_notes
    )

    await session.commit()

    logger.info(f"✅ Approved registration request {request_id} by {current_user.email}")

    return RegistrationRequestResponse.model_validate(approved_request)


@router.post(
    "/registration-requests/{request_id}/reject",
    response_model=RegistrationRequestResponse,
    summary="Rechazar solicitud de registro",
    description="Rechaza una solicitud de registro con notas del moderador",
    responses={
        403: {"model": ErrorResponse, "description": "Sin permisos para rechazar solicitudes"},
        404: {"model": ErrorResponse, "description": "Solicitud no encontrada"},
        400: {"model": ErrorResponse, "description": "Solicitud ya procesada"}
    }
)
async def reject_registration_request(
    request_id: UUID,
    decision_data: RegistrationRequestDecision,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_registration_request_access)
) -> RegistrationRequestResponse:
    """
    Rechazar una solicitud de registro.

    - **decision_notes**: Notas del moderador explicando el rechazo

    Al rechazar:
    1. La dependencia valida automáticamente permisos sobre la comunidad
    2. Se actualiza el estado de la solicitud a REJECTED
    3. Se registra quién y cuándo rechazó la solicitud
    4. El usuario no podrá acceder al sistema
    """
    # La validación de permisos ya se hizo en la dependencia
    rejected_request = await RegistrationRequestRepository.reject_registration_request(
        session=session,
        request_id=request_id,
        decided_by=current_user.id,
        decision_notes=decision_data.decision_notes
    )

    await session.commit()

    logger.info(f"❌ Rejected registration request {request_id} by {current_user.email}")

    return RegistrationRequestResponse.model_validate(rejected_request)


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

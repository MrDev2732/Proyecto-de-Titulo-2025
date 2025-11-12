"""
Endpoints de solicitudes de registro para la API.
"""

from typing import List, Optional, Union
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.session import get_db_session
from src.schemas import (
    RegistrationRequestResponse,
    RegistrationRequestListResponse,
    RegistrationRequestDecision,
    ManualRegistrationRequest,
    ManualRegistrationResponse,
    CommunityResponse,
    ErrorResponse
)
from src.core.dependencies import require_community_access, require_registration_request_access, get_current_active_user
from src.database.models import User
from src.database.repositories import (
    CommunityRepository,
    RegistrationRequestRepository,
    TenantRepository
)
from src.database.utils import ValidationUtils, RutChile
from src.services.file import FileService
from src.services.registration_approval import RegistrationApprovalService
from src.services.google_maps import GoogleMapsService
from src.services.email import EmailService
from src.core.logging import get_logger


logger = get_logger(__name__)

# Router para endpoints de solicitudes de registro
router = APIRouter(prefix="/registration", tags=["Solicitudes de Registro"])


@router.post(
    "/requests",
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

        # Agregar documentos requeridos con toda la información del archivo
        required_documents = [
            (saved_files['id_card_front'], "id_card_front"),
            (saved_files['id_card_back'], "id_card_back"),
            (saved_files['utility_bill'], "utility_bill")
        ]

        for file_info, kind in required_documents:
            await RegistrationRequestRepository.add_attachment_to_request(
                session=session,
                request_id=registration_request.id,
                bucket=file_info['bucket'],
                storage_key=file_info['storage_key'],
                sha256=file_info['sha256'],
                mime_type=file_info['mime_type'],
                kind=kind
            )

        # Agregar archivos adicionales si existen
        for additional_file_info in saved_files.get('additional_files', []):
            await RegistrationRequestRepository.add_attachment_to_request(
                session=session,
                request_id=registration_request.id,
                bucket=additional_file_info['bucket'],
                storage_key=additional_file_info['storage_key'],
                sha256=additional_file_info['sha256'],
                mime_type=additional_file_info['mime_type'],
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
    "/requests",
    response_model=RegistrationRequestListResponse,
    summary="Listar todas las solicitudes de registro según permisos del usuario",
    description="Obtiene todas las solicitudes de registro de las comunidades a las que el usuario tiene acceso",
    responses={
        403: {"model": ErrorResponse, "description": "Sin permisos para ver solicitudes"},
    }
)
async def list_all_registration_requests(
    status: Optional[str] = None,
    search: Optional[str] = None,
    page: int = 1,
    per_page: int = 20,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_active_user)
) -> RegistrationRequestListResponse:
    """
    Listar todas las solicitudes de registro según los permisos del usuario actual.

    **Permisos y acceso:**
    - **SUPERADMIN**: Ve todas las solicitudes del sistema
    - **ADMIN del tenant**: Ve solicitudes de todas las comunidades de su municipalidad
    - **MODERATOR de comunidad**: Ve solo solicitudes de sus comunidades específicas

    **Parámetros de filtrado:**
    - **status**: Filtrar por estado (PENDING, APPROVED, REJECTED)
    - **search**: Buscar por email, nombre o RUT
    - **page**: Número de página (default: 1)
    - **per_page**: Elementos por página (default: 20, max: 100)

    Retorna todas las solicitudes accesibles con sus adjuntos, paginadas.
    """
    # Validar parámetros
    if per_page > 100:
        per_page = 100
    if page < 1:
        page = 1

    # Obtener solicitudes con filtros según permisos del usuario
    requests = await RegistrationRequestRepository.get_requests_for_user(
        session=session,
        user_id=current_user.id,
        status=status,
        search=search,
        page=page,
        per_page=per_page
    )

    return RegistrationRequestListResponse(
        requests=[RegistrationRequestResponse.model_validate(req) for req in requests],
        total=len(requests)  # TODO: Implementar conteo total real en el repository
    )


@router.get(
    "/requests/{request_id}",
    response_model=RegistrationRequestResponse,
    summary="Obtener detalles de una solicitud de registro",
    description="Obtiene los detalles completos de una solicitud de registro específica",
    responses={
        403: {"model": ErrorResponse, "description": "Sin permisos para ver esta solicitud"},
        404: {"model": ErrorResponse, "description": "Solicitud no encontrada"}
    }
)
async def get_registration_request_details(
    request_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_registration_request_access)
) -> RegistrationRequestResponse:
    """
    Obtener detalles completos de una solicitud de registro.

    Requiere permisos de acceso a la solicitud específica.
    """
    try:
        logger.info(f"🔍 Getting request details for ID: {request_id} by user: {current_user.email}")

        # Obtener la solicitud con todos sus detalles y archivos adjuntos
        request = await RegistrationRequestRepository.get_by_id_with_attachments(
            session=session, 
            request_id=request_id
        )

        if not request:
            logger.warning(f"❌ Request not found: {request_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Solicitud de registro no encontrada"
            )

        logger.info(f"✅ Request details retrieved for ID: {request_id}, attachments: {len(request.attachments)}")

        # Log de las URLs de los attachments para debugging
        for i, attachment in enumerate(request.attachments):
            logger.info(f"🔍 Attachment {i+1}: kind={attachment.kind}, url={attachment.url}")

        response = RegistrationRequestResponse.model_validate(request)
        logger.info(f"🔍 Response created with {len(response.attachments)} attachments")

        # Log de las URLs en la respuesta
        for i, attachment in enumerate(response.attachments):
            logger.info(f"🔍 Response attachment {i+1}: kind={attachment.kind}, url={attachment.url}")

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error retrieving request details for ID {request_id}: {e}")
        logger.error(f"❌ Exception type: {type(e)}")
        logger.error(f"❌ Exception args: {e.args}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno del servidor al obtener detalles de la solicitud"
        )


@router.get(
    "/communities/{community_id}/requests",
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
    "/requests/{request_id}/approve",
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
    8. Se envía email de notificación de aprobación al solicitante
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

    # Enviar email de notificación de aprobación (para usuarios existentes)
    try:
        community = await CommunityRepository.get_community_by_id(session, approved_request.community_id)
        community_name = community.name if community else "Comunidad"

        email_sent = await EmailService.send_registration_decision_email(
            to_email=approved_request.email,
            full_name=approved_request.full_name or "Usuario",
            community_name=community_name,
            approved=True,
            notes=decision_data.decision_notes
        )

        if email_sent:
            logger.info(f"📧 Approval notification email sent to {approved_request.email}")
        else:
            logger.warning(f"⚠️ Failed to send approval notification email to {approved_request.email}")

    except Exception as e:
        logger.error(f"❌ Error sending approval notification email: {e}")

    logger.info(f"✅ Approved registration request {request_id} by {current_user.email}")

    return RegistrationRequestResponse.model_validate(approved_request)


@router.post(
    "/requests/{request_id}/reject",
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
    4. Se envía email de notificación de rechazo al solicitante
    5. El usuario no podrá acceder al sistema
    """
    # La validación de permisos ya se hizo en la dependencia
    rejected_request = await RegistrationRequestRepository.reject_registration_request(
        session=session,
        request_id=request_id,
        decided_by=current_user.id,
        decision_notes=decision_data.decision_notes
    )

    await session.commit()

    # Enviar email de notificación de rechazo
    try:
        community = await CommunityRepository.get_community_by_id(session, rejected_request.community_id)
        community_name = community.name if community else "Comunidad"

        email_sent = await EmailService.send_registration_decision_email(
            to_email=rejected_request.email,
            full_name=rejected_request.full_name or "Usuario",
            community_name=community_name,
            approved=False,
            notes=decision_data.decision_notes
        )

        if email_sent:
            logger.info(f"📧 Rejection notification email sent to {rejected_request.email}")
        else:
            logger.warning(f"⚠️ Failed to send rejection notification email to {rejected_request.email}")

    except Exception as e:
        logger.error(f"❌ Error sending rejection notification email: {e}")

    logger.info(f"❌ Rejected registration request {request_id} by {current_user.email}")

    return RegistrationRequestResponse.model_validate(rejected_request)


@router.post(
    "/communities/{community_id}/manual-registration",
    response_model=ManualRegistrationResponse,
    summary="Registrar manualmente a un vecino",
    description="Permite a moderadores/admins registrar directamente a un vecino sin pasar por el proceso de solicitud con documentos",
    responses={
        400: {"model": ErrorResponse, "description": "Usuario ya tiene membresía o datos inválidos"},
        403: {"model": ErrorResponse, "description": "Sin permisos para registrar vecinos"},
        404: {"model": ErrorResponse, "description": "Comunidad no encontrada"},
        422: {"model": ErrorResponse, "description": "Datos de entrada inválidos"}
    }
)
async def register_resident_manually(
    community_id: UUID,
    registration_data: ManualRegistrationRequest,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_community_access)
) -> ManualRegistrationResponse:
    """
    Registrar manualmente a un vecino sin pasar por el proceso de solicitud.

    **Solo usuarios con permisos específicos pueden usar este endpoint:**
    - SUPERADMIN (acceso global)
    - ADMIN del tenant que contiene la comunidad  
    - MODERATOR específicamente de esta comunidad

    **Proceso de registro manual:**
    1. Valida los datos del vecino (email, nombre, RUT, dirección)
    2. Verifica que la comunidad existe y el moderador tiene permisos
    3. Busca si el usuario ya existe o crea uno nuevo con contraseña temporal
    4. Verifica que no tenga membresía previa en la comunidad
    5. Crea la membresía directamente en estado APPROVED y verificada
    6. Registra quién realizó el registro manual

    **Datos requeridos:**
    - **community_id** (en URL): ID de la comunidad donde registrar
    - **email**: Email del vecino
    - **full_name**: Nombre completo
    - **rut**: RUT chileno válido
    - **address**: Dirección del vecino
    - **notes**: Notas opcionales del moderador

    **Respuesta incluye:**
    - Información del usuario y membresía creados
    - Contraseña temporal si es usuario nuevo (solo para logging, no en producción)
    - Información de la comunidad
    - ID del moderador que realizó el registro
    """
    # ========================================
    # VALIDACIONES DE DATOS DE ENTRADA
    # ========================================

    # Validar email
    email_valid, email_error = ValidationUtils.validate_email(registration_data.email)
    if not email_valid:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Email inválido: {email_error}"
        )

    # Validar nombre completo
    name_valid, name_error = ValidationUtils.validate_full_name(registration_data.full_name)
    if not name_valid:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Nombre inválido: {name_error}"
        )

    # Validar RUT
    rut_valid, formatted_rut, rut_error = RutChile.validate_rut(registration_data.rut)
    if not rut_valid:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"RUT inválido: {rut_error}"
        )

    # Validar dirección
    address_valid, address_error = ValidationUtils.validate_address(registration_data.address)
    if not address_valid:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Dirección inválida: {address_error}"
        )

    # Validación adicional con Google Maps (si está habilitada)
    try:
        maps_valid, maps_details = await GoogleMapsService.validate_address_in_chile(registration_data.address)
        if not maps_valid and maps_details.get("status") not in ["API_KEY_NOT_CONFIGURED", "QUERY_LIMIT_EXCEEDED"]:
            logger.warning(f"Google Maps validation failed for address: {registration_data.address} - {maps_details.get('message')}")
            # No bloquear el registro, solo logear la advertencia
    except Exception as e:
        logger.error(f"Error en validación de Google Maps: {e}")
        # Continuar sin bloquear el registro

    # Normalizar datos validados
    email = registration_data.email.strip().lower()
    full_name = registration_data.full_name.strip()
    rut = formatted_rut  # Usar el RUT formateado correctamente
    address = registration_data.address.strip()

    logger.info(f"📋 Validación exitosa para registro manual: {email}, RUT: {rut} por {current_user.email}")

    # ========================================
    # VERIFICACIONES DE COMUNIDAD Y PERMISOS
    # ========================================

    # Obtener información de la comunidad
    community = await CommunityRepository.get_community_by_id(session, community_id)
    if not community:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Comunidad no encontrada"
        )

    # Los permisos ya fueron validados por la dependencia require_community_access
    # que verifica que el usuario tenga acceso a esta comunidad específica

    # ========================================
    # REGISTRO MANUAL DEL VECINO
    # ========================================

    try:
        # Usar el servicio para manejar toda la lógica de registro manual
        user, membership_id, temporary_password = await RegistrationApprovalService.register_resident_manually(
            session=session,
            community_id=community_id,
            email=email,
            full_name=full_name,
            rut=rut,
            address=address,
            registered_by=current_user.id,
            notes=registration_data.notes
        )

        await session.commit()

        logger.info(f"✅ Manual registration completed for {email} in community {community_id} by {current_user.email}")

        # Construir respuesta
        response = ManualRegistrationResponse(
            user_id=user.id,
            membership_id=membership_id,
            email=email,
            full_name=full_name,
            rut=rut,
            address=address,
            community=CommunityResponse.model_validate(community),
            registered_by=current_user.id,
            temporary_password=temporary_password,  # Solo para desarrollo/logging
            created_at=user.created_at
        )

        return response

    except HTTPException:
        # Re-lanzar HTTPExceptions del servicio
        raise
    except Exception as e:
        logger.error(f"❌ Error in manual registration: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno del servidor durante el registro manual"
        )

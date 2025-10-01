"""
Endpoints de certificados de residencia para la API.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.session import get_db_session
from src.schemas.community_schemas import (
    CertificateRequest,
    CertificateResponse,
)
from src.schemas.auth_schemas import ErrorResponse
from src.core.dependencies import get_current_active_user
from src.database import User
from src.database.repositories.community_repository import (
    CommunityRepository,
    ResidentMembershipRepository,
)
from src.services.certificate_service import CertificateService
from src.core.logging import get_logger

logger = get_logger(__name__)

# Router para endpoints de certificados
router = APIRouter(prefix="/certificates", tags=["Certificados"])


@router.post(
    "/communities/{community_id}/generate",
    response_model=CertificateResponse,
    summary="Generar certificado de residencia",
    description="Genera un certificado de residencia para el usuario autenticado si es residente de la comunidad",
    responses={
        400: {"model": ErrorResponse, "description": "Usuario no es residente de la comunidad o datos inválidos"},
        401: {"model": ErrorResponse, "description": "Usuario no autenticado"},
        404: {"model": ErrorResponse, "description": "Usuario o comunidad no encontrados"},
        500: {"model": ErrorResponse, "description": "Error interno del servidor"}
    }
)
async def generate_residence_certificate(
    community_id: UUID,
    certificate_request: CertificateRequest,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_active_user)
):
    """
    Generar certificado de residencia para el usuario autenticado.

    **Cualquier usuario autenticado puede usar este endpoint si:**
    - Está registrado en la base de datos
    - Es residente aprobado de la comunidad especificada

    **Proceso de generación:**
    1. Verifica que el usuario esté autenticado (JWT válido)
    2. Verifica que el usuario sea residente aprobado de la comunidad
    3. Obtiene los datos del residente y la comunidad
    4. Genera el certificado PDF personalizado
    5. Opcionalmente guarda el certificado en archivo

    **Datos requeridos:**
    - **community_id** (en URL): ID de la comunidad
    - **save_to_file**: Si guardar el certificado en archivo (opcional)

    **Respuesta incluye:**
    - Número del certificado generado
    - Información del residente y comunidad
    - Tamaño del archivo PDF
    - Ruta del archivo si se guardó
    """
    try:
        # Obtener información de la comunidad
        community = await CommunityRepository.get_community_by_id(session, community_id)
        if not community:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Comunidad no encontrada"
            )

        # Verificar que el usuario autenticado sea residente de la comunidad
        membership = await ResidentMembershipRepository.find_user_membership_in_community(
            session, current_user.id, community_id
        )

        if not membership or membership.status.value != 'APPROVED':
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No eres residente aprobado de esta comunidad"
            )

        # Preparar datos para el certificado (usar datos del usuario autenticado)
        user_data = {
            'full_name': current_user.full_name or "Sin nombre",
            'rut': current_user.rut or "Sin RUT",
            'address': current_user.address or "Sin dirección"
        }

        community_data = {
            'name': community.name
        }

        # Generar certificado
        certificate_info = CertificateService.generate_certificate_for_resident(
            user_data=user_data,
            community_data=community_data,
            save_to_file=certificate_request.save_to_file
        )

        logger.info(f"✅ Certificate generated for {current_user.email} in community {community.name}")

        # Crear respuesta
        response = CertificateResponse(
            certificate_number=certificate_info['certificate_number'],
            issue_date=certificate_info['issue_date'],
            resident_name=certificate_info['resident_name'],
            resident_rut=certificate_info['resident_rut'],
            community_name=certificate_info['community_name'],
            file_size=certificate_info['file_size'],
            file_path=certificate_info.get('file_path')
        )

        return response

    except HTTPException:
        # Re-lanzar HTTPExceptions
        raise
    except Exception as e:
        logger.error(f"❌ Error generating certificate: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno del servidor durante la generación del certificado"
        )


@router.get(
    "/communities/{community_id}/download",
    summary="Descargar certificado de residencia",
    description="Genera y descarga directamente el certificado de residencia en PDF para el usuario autenticado",
    responses={
        200: {"content": {"application/pdf": {}}, "description": "Certificado PDF"},
        400: {"model": ErrorResponse, "description": "Usuario no es residente de la comunidad"},
        401: {"model": ErrorResponse, "description": "Usuario no autenticado"},
        404: {"model": ErrorResponse, "description": "Usuario o comunidad no encontrados"},
        500: {"model": ErrorResponse, "description": "Error interno del servidor"}
    }
)
async def download_residence_certificate(
    community_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_active_user)
):
    """
    Generar y descargar certificado de residencia directamente como PDF para el usuario autenticado.

    **Cualquier usuario autenticado puede usar este endpoint si:**
    - Está registrado en la base de datos
    - Es residente aprobado de la comunidad especificada

    **Parámetros:**
    - **community_id**: ID de la comunidad

    **Respuesta:**
    - Archivo PDF del certificado listo para descarga
    """
    try:
        # Obtener información de la comunidad
        community = await CommunityRepository.get_community_by_id(session, community_id)
        if not community:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Comunidad no encontrada"
            )

        # Verificar que el usuario autenticado sea residente de la comunidad
        membership = await ResidentMembershipRepository.find_user_membership_in_community(
            session, current_user.id, community_id
        )

        if not membership or membership.status.value != 'APPROVED':
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No eres residente aprobado de esta comunidad"
            )

        # Preparar datos para el certificado (usar datos del usuario autenticado)
        user_data = {
            'full_name': current_user.full_name or "Sin nombre",
            'rut': current_user.rut or "Sin RUT",
            'address': current_user.address or "Sin dirección"
        }

        community_data = {
            'name': community.name
        }

        # Generar certificado
        certificate_info = CertificateService.generate_certificate_for_resident(
            user_data=user_data,
            community_data=community_data,
            save_to_file=False  # No guardar archivo, solo generar bytes
        )

        logger.info(f"✅ Certificate downloaded for {current_user.email} in community {community.name}")

        # Crear nombre del archivo
        filename = f"certificado_residencia_{current_user.rut.replace('.', '').replace('-', '') if current_user.rut else 'sin_rut'}.pdf"

        # Retornar PDF como respuesta
        return Response(
            content=certificate_info['certificate_bytes'],
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename={filename}",
                "Content-Length": str(certificate_info['file_size'])
            }
        )

    except HTTPException:
        # Re-lanzar HTTPExceptions
        raise
    except Exception as e:
        logger.error(f"❌ Error downloading certificate: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno del servidor durante la descarga del certificado"
        )

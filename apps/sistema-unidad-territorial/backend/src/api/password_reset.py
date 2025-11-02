"""
Endpoints para recuperación de contraseñas.
"""

from typing import Dict, Any
from fastapi import APIRouter, Depends, Request, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.dependencies import get_db_session, require_admin
from src.core.logging import get_logger
from src.database.models.auth import User
from src.services.password_reset import PasswordResetService
from src.schemas import (
    PasswordResetRequest,
    PasswordResetResponse,
    PasswordResetCodeValidationRequest,
    PasswordResetCodeValidationResponse,
    PasswordResetConfirmationRequest,
    PasswordResetConfirmationResponse,
    ErrorResponse
)

logger = get_logger(__name__)
router = APIRouter(prefix="/password-reset", tags=["Password Reset"])


@router.post(
    "/request",
    response_model=PasswordResetResponse,
    summary="Solicitar recuperación de contraseña",
    description="Envía un código de recuperación al email del usuario",
    responses={
        200: {"model": PasswordResetResponse, "description": "Solicitud procesada (siempre exitosa por seguridad)"},
        422: {"model": ErrorResponse, "description": "Email inválido"}
    }
)
async def request_password_reset(
    request_data: PasswordResetRequest,
    request: Request,
    session: AsyncSession = Depends(get_db_session)
) -> PasswordResetResponse:
    """
    Solicitar recuperación de contraseña.

    - **email**: Email del usuario que solicita el reset

    Envía un código de 6 dígitos al email si existe en el sistema.
    Por seguridad, siempre retorna éxito sin revelar si el email existe.
    """

    # Obtener información del cliente
    user_agent = request.headers.get("user-agent")

    # Crear servicio con sesión asíncrona
    password_service = PasswordResetService(session)

    try:
        result = await password_service.request_password_reset(
            request_data,
            user_agent=user_agent
        )
        return result
    except Exception as e:
        logger.error(f"Error in password reset request: {e}")
        # Por seguridad, siempre retornar éxito
        from uuid import UUID
        fake_token_id = UUID('00000000-0000-0000-0000-000000000000')
        return PasswordResetResponse(
            message="Si el email existe en nuestro sistema, recibirás un código de recuperación.",
            reset_token_id=fake_token_id,
            expires_in_minutes=15
        )


@router.post(
    "/validate",
    response_model=PasswordResetCodeValidationResponse,
    summary="Validar código de recuperación",
    description="Valida que el código de recuperación sea correcto y no haya expirado",
    responses={
        200: {"model": PasswordResetCodeValidationResponse, "description": "Código válido"},
        400: {"model": ErrorResponse, "description": "Código inválido o expirado"},
        422: {"model": ErrorResponse, "description": "Datos inválidos"}
    }
)
async def validate_reset_code(
    request_data: PasswordResetCodeValidationRequest,
    session: AsyncSession = Depends(get_db_session)
) -> PasswordResetCodeValidationResponse:
    """
    Validar código de recuperación de contraseña.

    - **email**: Email del usuario
    - **code**: Código de 6 dígitos recibido por email

    Valida que el código sea correcto y no haya expirado.
    """

    password_service = PasswordResetService(session)

    try:
        result = await password_service.validate_reset_code(request_data)
        return result
    except ValueError as e:
        logger.warning(f"Password reset code validation failed: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error validating reset code: {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")


@router.post(
    "/confirm",
    response_model=PasswordResetConfirmationResponse,
    summary="Confirmar cambio de contraseña",
    description="Cambia la contraseña usando el código de recuperación",
    responses={
        200: {"model": PasswordResetConfirmationResponse, "description": "Contraseña cambiada exitosamente"},
        400: {"model": ErrorResponse, "description": "Código inválido o contraseña no válida"},
        422: {"model": ErrorResponse, "description": "Datos inválidos"}
    }
)
async def confirm_password_reset(
    request_data: PasswordResetConfirmationRequest,
    session: AsyncSession = Depends(get_db_session)
) -> PasswordResetConfirmationResponse:
    """
    Confirmar cambio de contraseña con código de reset.

    - **email**: Email del usuario
    - **code**: Código de 6 dígitos recibido por email
    - **new_password**: Nueva contraseña (mínimo 8 caracteres)

    Cambia la contraseña del usuario y invalida el código de reset.
    """

    password_service = PasswordResetService(session)

    try:
        result = await password_service.confirm_password_reset(request_data)
        return result
    except ValueError as e:
        logger.warning(f"Password reset confirmation failed: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error confirming password reset: {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")


# Endpoint administrativo para limpiar tokens expirados
@router.delete(
    "/cleanup",
    summary="Limpiar tokens expirados (solo administradores)",
    description="Elimina tokens de recuperación expirados de la base de datos",
    dependencies=[Depends(require_admin)],
    responses={
        200: {"description": "Limpieza completada"},
        403: {"model": ErrorResponse, "description": "Sin permisos de administrador"}
    }
)
async def cleanup_expired_reset_tokens(
    session: AsyncSession = Depends(get_db_session),
    older_than_hours: int = Query(24, description="Eliminar tokens más antiguos que estas horas"),
    _: User = Depends(require_admin)
) -> Dict[str, Any]:
    """
    Limpiar tokens de recuperación expirados.

    - **older_than_hours**: Eliminar tokens más antiguos que estas horas (default: 24)

    Solo usuarios con rol de administrador pueden ejecutar esta limpieza.
    """
    password_service = PasswordResetService(session)

    try:
        deleted_count = await password_service.cleanup_expired_tokens(older_than_hours)
        return {
            "message": f"Limpieza completada. {deleted_count} tokens eliminados.",
            "deleted_count": deleted_count,
            "older_than_hours": older_than_hours
        }
    except Exception as e:
        logger.error(f"Error cleaning up expired tokens: {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")

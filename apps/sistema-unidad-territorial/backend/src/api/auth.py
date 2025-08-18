"""
Endpoints de autenticación para la API.
"""

from typing import Dict
from uuid import uuid4, UUID

from fastapi import APIRouter, Depends, HTTPException, status, Query, Header, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.database.session import get_db_session
from src.schemas.auth_schemas import (
    LoginRequest,
    TokenResponse,
    RefreshTokenRequest,
    UserCreateRequest,
    UserResponse,
    ErrorResponse
)
from src.services.auth_service import AuthService, GoogleOAuthService
from src.core.security import create_user_tokens, verify_token
from src.core.dependencies import get_current_active_user, require_admin
from src.database import User


# Router para endpoints de autenticación
router = APIRouter(prefix="/auth", tags=["Autenticación"])


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Iniciar sesión con email y contraseña",
    description="Autentica un usuario con sus credenciales y devuelve tokens JWT",
    responses={
        400: {"model": ErrorResponse, "description": "Credenciales inválidas"},
        422: {"model": ErrorResponse, "description": "Datos de entrada inválidos"}
    }
)
async def login(
    login_data: LoginRequest,
    request: Request,
    session: AsyncSession = Depends(get_db_session)
) -> TokenResponse:
    """
    Iniciar sesión con email y contraseña.

    - **email**: Email del usuario registrado
    - **password**: Contraseña del usuario

    Retorna tokens de acceso y refresh junto con información del usuario.
    """
    # Autenticar usuario
    user = await AuthService.authenticate_user(
        session, 
        login_data.email, 
        login_data.password
    )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email o contraseña incorrectos"
        )

    # Obtener información del cliente
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")

    # Crear sesión y tokens
    tokens = await AuthService.create_session_for_user(
        session,
        user,
        ip_address=ip_address,
        user_agent=user_agent
    )

    # Convertir usuario a response
    user_response = AuthService.user_to_response(user)

    return TokenResponse(
        access_token=tokens["access_token"],
        refresh_token=tokens["refresh_token"],
        token_type=tokens["token_type"],
        expires_in=tokens["expires_in"],
        user=user_response
    )


@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Refrescar token de acceso",
    description="Genera un nuevo token de acceso usando el refresh token",
    responses={
        400: {"model": ErrorResponse, "description": "Refresh token inválido"},
        422: {"model": ErrorResponse, "description": "Datos de entrada inválidos"}
    }
)
async def refresh_token(
    refresh_data: RefreshTokenRequest,
    request: Request,
    session: AsyncSession = Depends(get_db_session)
) -> TokenResponse:
    """
    Refrescar token de acceso.

    - **refresh_token**: Token de refresh válido

    Retorna nuevos tokens de acceso y refresh.
    """
    # Obtener información del cliente
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")

    # Refrescar sesión
    tokens = await AuthService.refresh_user_session(
        session, 
        refresh_data.refresh_token,
        ip_address=ip_address,
        user_agent=user_agent
    )

    if not tokens:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Refresh token inválido o expirado"
        )

    # Obtener usuario para response
    token_data = verify_token(refresh_data.refresh_token, expected_type="refresh")
    user = await AuthService.get_user_by_id(session, UUID(token_data.user_id))
    user_response = AuthService.user_to_response(user)

    return TokenResponse(
        access_token=tokens["access_token"],
        refresh_token=tokens["refresh_token"],
        token_type=tokens["token_type"],
        expires_in=tokens["expires_in"],
        user=user_response
    )


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Obtener información del usuario actual",
    description="Retorna la información del usuario autenticado"
)
async def get_current_user_info(
    current_user: User = Depends(get_current_active_user)
) -> UserResponse:
    """
    Obtener información del usuario actual.

    Requiere token de acceso válido en el header Authorization.
    """
    return AuthService.user_to_response(current_user)


@router.post(
    "/register",
    response_model=UserResponse,
    summary="Crear nuevo usuario (solo administradores)",
    description="Crear un nuevo usuario con email y contraseña",
    dependencies=[Depends(require_admin)],
    responses={
        400: {"model": ErrorResponse, "description": "Usuario ya existe"},
        403: {"model": ErrorResponse, "description": "Sin permisos de administrador"},
        422: {"model": ErrorResponse, "description": "Datos de entrada inválidos"}
    }
)
async def register_user(
    user_data: UserCreateRequest,
    session: AsyncSession = Depends(get_db_session),
    _: User = Depends(require_admin)  # Verificar que el usuario actual sea admin
) -> UserResponse:
    """
    Crear nuevo usuario (solo administradores).

    - **email**: Email único del nuevo usuario
    - **password**: Contraseña (mínimo 8 caracteres)
    - **roles**: Lista opcional de roles a asignar

    Solo usuarios con rol de administrador pueden crear nuevos usuarios.
    """
    # Verificar que el usuario no exista
    existing_user = await session.execute(
        select(User).where(User.email == user_data.email.lower())
    )
    if existing_user.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ya existe un usuario con este email"
        )

    # Crear usuario
    user = await AuthService.create_user_with_password(
        session,
        user_data.email,
        user_data.password,
        user_data.roles
    )

    return AuthService.user_to_response(user)


# OAuth con Google
@router.get(
    "/google/login",
    summary="Iniciar OAuth con Google",
    description="Redirige al usuario a Google para autenticación OAuth"
)
async def google_oauth_login():
    """
    Iniciar proceso de OAuth con Google.

    Redirige al usuario a la página de autorización de Google.
    """
    # Generar estado para validación CSRF
    state = str(uuid4())

    # Obtener URL de autorización
    auth_url = GoogleOAuthService.get_authorization_url(state)

    return RedirectResponse(url=auth_url, status_code=302)


@router.get(
    "/google/callback",
    response_model=TokenResponse,
    summary="Callback de OAuth con Google",
    description="Maneja la respuesta de Google OAuth y autentica al usuario",
    responses={
        400: {"model": ErrorResponse, "description": "Error en OAuth o código inválido"},
        422: {"model": ErrorResponse, "description": "Parámetros de callback inválidos"}
    }
)
async def google_oauth_callback(
    code: str = Query(..., description="Código de autorización de Google"),
    state: str = Query(None, description="Estado para validación CSRF"),
    session: AsyncSession = Depends(get_db_session)
) -> TokenResponse:
    """
    Callback de OAuth con Google.

    - **code**: Código de autorización devuelto por Google
    - **state**: Estado para validación CSRF

    Completa el proceso de OAuth y devuelve tokens de autenticación.
    """
    # Intercambiar código por información del usuario
    oauth_info = await GoogleOAuthService.exchange_code_for_user_info(code)

    if not oauth_info:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Error al obtener información del usuario de Google"
        )

    # Autenticar o crear usuario
    user = await GoogleOAuthService.authenticate_or_create_oauth_user(
        session, 
        oauth_info
    )

    # Crear sesión y tokens
    tokens = await AuthService.create_session_for_user(
        session,
        user
    )

    # Convertir usuario a response
    user_response = AuthService.user_to_response(user)

    return TokenResponse(
        access_token=tokens["access_token"],
        refresh_token=tokens["refresh_token"],
        token_type=tokens["token_type"],
        expires_in=tokens["expires_in"],
        user=user_response
    )


@router.post(
    "/logout",
    summary="Cerrar sesión",
    description="Revoca la sesión actual del usuario",
    responses={
        200: {"description": "Sesión cerrada exitosamente"},
        401: {"description": "Token de acceso inválido o faltante"}
    }
)
async def logout(
    db_session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_active_user),
    authorization: str = Header(None)
) -> Dict[str, str]:
    """
    Cerrar sesión del usuario actual.

    Revoca la sesión activa del usuario, invalidando inmediatamente el token.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de acceso requerido"
        )

    # Extraer token del header
    access_token = authorization.split(" ")[1]

    # Revocar sesión
    success = await AuthService.logout_user(db_session, access_token)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se pudo cerrar la sesión"
        )

    return {"message": f"Sesión cerrada exitosamente para {current_user.email}"}


# Endpoint para debug de sesiones
@router.get(
    "/debug/sessions",
    summary="Debug de sesiones",
    description="Endpoint para debug - verificar sesiones activas",
    include_in_schema=False  # No mostrar en docs de producción
)
async def debug_sessions(
    db_session: AsyncSession = Depends(get_db_session),
    authorization: str = Header(None)
) -> Dict:
    """
    Debug endpoint para verificar sesiones.
    """
    if not authorization or not authorization.startswith("Bearer "):
        return {"error": "No authorization header"}
    
    access_token = authorization.split(" ")[1]
    
    # Verificar JWT
    token_data = verify_token(access_token)
    
    # Crear hash del token
    from src.core.security import hash_token
    token_hash = hash_token(access_token)
    
    # Buscar sesión en BD
    from src.database.repositories.auth_repository import SessionRepository
    user_session = await SessionRepository.find_session_by_access_token(db_session, token_hash)
    
    return {
        "token_valid": token_data is not None,
        "token_data": token_data.__dict__ if token_data else None,
        "token_hash": token_hash[:16] + "...",  # Solo mostrar parte del hash
        "session_found": user_session is not None,
        "session_active": user_session.is_active if user_session else None,
        "session_valid": user_session.is_valid() if user_session else None,
        "session_expires_at": user_session.expires_at.isoformat() if user_session else None
    }


# Endpoint para validar token (útil para otros servicios)
@router.get(
    "/validate",
    response_model=UserResponse,
    summary="Validar token actual",
    description="Verifica si el token actual es válido y retorna información del usuario"
)
async def validate_token(
    current_user: User = Depends(get_current_active_user)
) -> UserResponse:
    """
    Validar token actual.

    Útil para que otros servicios verifiquen la validez de un token.
    """
    return AuthService.user_to_response(current_user)


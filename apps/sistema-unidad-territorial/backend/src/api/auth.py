"""
Endpoints de autenticación para la API.
"""

from typing import Dict, Optional
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
from src.core.security import verify_token
from src.core.dependencies import get_current_active_user, require_admin
from src.database import User
from src.database.repositories.auth_repository import AuthRepository
from src.database.repositories.auth_log_repository import AuthenticationLogRepository
from src.core.logging import get_logger


logger = get_logger(__name__)

# Router para endpoints de autenticación
router = APIRouter(prefix="/auth", tags=["Autenticación"])


def get_client_ip(request: Request) -> Optional[str]:
    """
    Obtener la IP real del cliente considerando proxies y load balancers.

    Busca en orden de prioridad:
    1. X-Forwarded-For (estándar para proxies)
    2. X-Real-IP (usado por Nginx)
    3. X-Client-IP (algunos proxies)
    4. CF-Connecting-IP (Cloudflare)
    5. request.client.host (conexión directa)

    Args:
        request: Request de FastAPI

    Returns:
        str: IP del cliente o None si no se puede determinar
    """
    # Headers comunes de proxies (en orden de prioridad)
    ip_headers = [
        "x-forwarded-for",      # Estándar para proxies/load balancers
        "x-real-ip",            # Nginx
        "x-client-ip",          # Algunos proxies
        "cf-connecting-ip",     # Cloudflare
        "x-cluster-client-ip",  # Kubernetes
    ]

    for header in ip_headers:
        ip = request.headers.get(header)
        if ip:
            # X-Forwarded-For puede tener múltiples IPs separadas por comas
            # La primera es la IP original del cliente
            if "," in ip:
                ip = ip.split(",")[0].strip()

            # Validar que la IP tenga formato válido
            if ip and ip.strip():
                return ip.strip()

    # Fallback: IP de la conexión directa
    return request.client.host if request.client else None


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
    # Obtener información del cliente
    ip_address = get_client_ip(request)
    user_agent = request.headers.get("user-agent")

    # Autenticar usuario
    auth_result = await AuthService.authenticate_user(
        session, 
        login_data.email, 
        login_data.password,
        ip=ip_address,
        user_agent=user_agent
    )

    if not auth_result:
        # Check if it's a gating issue vs credentials issue
        user_exists = await AuthRepository.find_user_by_email(session, login_data.email)
        if user_exists and user_exists.password_hash:
            # User exists with password, likely a gating/approval issue
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Su cuenta no está aprobada para acceder al sistema. Contacte a los moderadores de su comunidad."
            )
        else:
            # Credentials issue or user doesn't exist
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email o contraseña incorrectos"
            )

    user, auth_log_id = auth_result

    # Crear sesión y tokens (sin logging adicional porque ya se registró en authenticate_user)
    tokens = await AuthService.create_session_for_user(
        session,
        user,
        ip_address=ip_address,
        user_agent=user_agent,
        log_authentication=False
    )

    # Actualizar el log con el user_session_id
    await AuthenticationLogRepository.update_auth_log_session(
        session,
        auth_log_id,
        UUID(tokens["session_id"])
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
async def google_oauth_login(
    request: Request,
    frontend_redirect: str = Query(None, description="URL del frontend para redirección después del OAuth")
):
    """
    Iniciar proceso de OAuth con Google.

    Redirige al usuario a la página de autorización de Google.

    - **frontend_redirect**: URL opcional del frontend donde redirigir después del OAuth exitoso
    """
    # Generar estado para validación CSRF
    state = str(uuid4())

    # Si hay frontend_redirect, guardarlo en el estado para recuperarlo después
    if frontend_redirect:
        # Guardar la URL de redirección en la sesión o cache temporal
        # Por simplicidad, la incluiremos en el state (en producción usar cache/redis)
        import base64
        import json
        state_data = {
            "state": state,
            "frontend_redirect": frontend_redirect
        }
        encoded_state = base64.urlsafe_b64encode(json.dumps(state_data).encode()).decode()
    else:
        encoded_state = state

    # Obtener URL de autorización
    auth_url = GoogleOAuthService.get_authorization_url(encoded_state)

    return RedirectResponse(url=auth_url, status_code=302)


@router.get(
    "/google/callback",
    summary="Callback de OAuth con Google",
    description="Maneja la respuesta de Google OAuth y autentica al usuario",
    responses={
        200: {"model": TokenResponse, "description": "Autenticación exitosa (JSON response)"},
        302: {"description": "Redirección al frontend con tokens"},
        400: {"model": ErrorResponse, "description": "Error en OAuth o código inválido"},
        422: {"model": ErrorResponse, "description": "Parámetros de callback inválidos"}
    }
)
async def google_oauth_callback(
    request: Request,
    code: str = Query(..., description="Código de autorización de Google"),
    state: str = Query(None, description="Estado para validación CSRF"),
    session: AsyncSession = Depends(get_db_session)
):
    """
    Callback de OAuth con Google.

    - **code**: Código de autorización devuelto por Google
    - **state**: Estado para validación CSRF

    Completa el proceso de OAuth y puede devolver tokens JSON o redirigir al frontend.
    """
    # Decodificar el estado para ver si hay frontend_redirect
    frontend_redirect = None
    if state:
        try:
            import base64
            import json
            decoded_state = json.loads(base64.urlsafe_b64decode(state.encode()).decode())
            if isinstance(decoded_state, dict) and "frontend_redirect" in decoded_state:
                frontend_redirect = decoded_state["frontend_redirect"]
        except:
            # Si no se puede decodificar, usar el state tal como está
            pass

    # Intercambiar código por información del usuario
    oauth_info = await GoogleOAuthService.exchange_code_for_user_info(code)

    if not oauth_info:
        logger.info(f"❌ Failed to get OAuth info from Google")
        if frontend_redirect:
            # Redirigir al frontend con error
            error_url = f"{frontend_redirect}?error=oauth_failed"
            return RedirectResponse(url=error_url, status_code=302)
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Error al obtener información del usuario de Google"
            )

    logger.info(f"✅ Got OAuth info: {oauth_info.email}, provider_user_id: {oauth_info.provider_user_id}")

    # Obtener información del cliente
    ip_address = get_client_ip(request)
    user_agent = request.headers.get("user-agent")

    logger.info(f"🔍 About to authenticate OAuth user: {oauth_info.email}")
    # Autenticar usuario (con gated access control)
    auth_result = await GoogleOAuthService.authenticate_or_create_oauth_user(
        session, 
        oauth_info,
        ip=ip_address,
        user_agent=user_agent
    )
    logger.info(f"🔍 Authentication result: {auth_result is not None}")

    if not auth_result:
        # Usuario no puede hacer login (no registrado/aprobado)
        if frontend_redirect:
            error_url = f"{frontend_redirect}?error=registration_required&message=Your+registration+request+has+been+submitted+for+approval"
            return RedirectResponse(url=error_url, status_code=302)
        else:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Registration required. Your request has been submitted for approval by community moderators."
            )

    user, auth_log_id = auth_result

    # Crear sesión y tokens (sin logging adicional porque ya se registró en OAuth)
    tokens = await AuthService.create_session_for_user(
        session,
        user,
        ip_address=ip_address,
        user_agent=user_agent,
        log_authentication=False
    )

    # Actualizar el log de OAuth con el user_session_id
    await AuthenticationLogRepository.update_auth_log_session(
        session,
        auth_log_id,
        UUID(tokens["session_id"])
    )

    # Convertir usuario a response
    user_response = AuthService.user_to_response(user)

    # Si hay frontend_redirect, redirigir al frontend con cookies seguras
    if frontend_redirect:

        # Preparar datos del usuario para cookie
        user_data = {
            "id": str(user_response.id),
            "email": user_response.email,
            "status": user_response.status,
            "roles": [{"id": str(role.id), "name": role.name} for role in user_response.roles]
        }

        # Crear respuesta de redirección
        response = RedirectResponse(url=frontend_redirect, status_code=302)

        # Establecer cookies seguras con los tokens (solo para desarrollo local)
        # En producción usar httponly=True, secure=True
        response.set_cookie(
            "oauth_access_token", 
            tokens["access_token"],
            max_age=tokens["expires_in"],
            httponly=False,  # False para que JS pueda leerla (solo desarrollo)
            secure=False,    # False para HTTP local (en prod usar True)
            samesite="lax"
        )
        response.set_cookie(
            "oauth_refresh_token", 
            tokens["refresh_token"],
            max_age=7 * 24 * 60 * 60,  # 7 días
            httponly=False,
            secure=False,
            samesite="lax"
        )
        response.set_cookie(
            "oauth_user", 
            json.dumps(user_data),
            max_age=tokens["expires_in"],
            httponly=False,
            secure=False,
            samesite="lax"
        )

        return response

    # Si no hay frontend_redirect, devolver JSON como antes
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

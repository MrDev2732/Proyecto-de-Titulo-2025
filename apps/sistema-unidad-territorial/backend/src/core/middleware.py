"""
Middleware para manejo de autenticación y autorización.

Incluye middleware para expiración de sesión por inactividad y logging de autenticación.
"""

import time
from datetime import datetime, timedelta
from typing import Dict, Any

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from src.core.security import verify_token
from src.core.config import settings
from src.core.logging import get_logger


logger = get_logger(__name__)


class SessionTrackingMiddleware(BaseHTTPMiddleware):
    """
    Middleware para tracking de sesiones y manejo de inactividad.

    Mantiene un registro de la última actividad de cada usuario y
    invalida sesiones que superen el tiempo de inactividad configurado.
    """

    def __init__(self, app, inactivity_timeout_minutes: int = 30):
        """
        Inicializar middleware de tracking de sesiones.

        Args:
            app: Aplicación FastAPI
            inactivity_timeout_minutes: Tiempo límite de inactividad en minutos
        """
        super().__init__(app)
        self.inactivity_timeout = timedelta(minutes=inactivity_timeout_minutes)
        # En producción, esto debería usar Redis o similar
        self.user_sessions: Dict[str, datetime] = {}

    async def dispatch(self, request: Request, call_next) -> Response:
        """
        Procesar request y manejar tracking de sesión.

        Args:
            request: Request HTTP
            call_next: Siguiente middleware/handler

        Returns:
            Response: Respuesta HTTP
        """
        start_time = time.time()

        # Verificar si la ruta requiere autenticación
        if self._requires_auth(request):
            logger.info(f"🔐 SessionTrackingMiddleware: Ruta requiere auth: {request.url.path}")
            # Extraer token del header Authorization
            auth_header = request.headers.get("authorization")
            if auth_header and auth_header.startswith("Bearer "):
                token = auth_header.split(" ")[1]
                logger.info(f"🎫 SessionTrackingMiddleware: Token encontrado en header")

                # Verificar token y actividad de sesión
                session_valid = await self._check_session_activity(token)
                if not session_valid:
                    logger.error(f"❌ SessionTrackingMiddleware: Sesión NO válida, bloqueando request")
                    return JSONResponse(
                        status_code=401,
                        content={
                            "detail": "Sesión expirada por inactividad",
                            "error_code": "SESSION_EXPIRED"
                        }
                    )

                logger.info(f"✅ SessionTrackingMiddleware: Sesión válida, continuando")
                # Actualizar última actividad
                await self._update_session_activity(token)
            else:
                logger.warning(f"⚠️ SessionTrackingMiddleware: No se encontró token en header Authorization")

        # Continuar con el procesamiento normal
        response = await call_next(request)

        # Log timing si es necesario
        process_time = time.time() - start_time
        if process_time > 1.0:  # Log requests lentas
            logger.warning(f"Request lenta: {request.url} - {process_time:.2f}s")

        return response

    def _requires_auth(self, request: Request) -> bool:
        """
        Verificar si una ruta requiere autenticación.

        Args:
            request: Request HTTP

        Returns:
            bool: True si requiere autenticación
        """
        # Rutas que no requieren autenticación
        public_paths = [
            "/health",
            "/",
            f"{settings.api.v1_str}/auth/login",
            f"{settings.api.v1_str}/auth/google/login",
            f"{settings.api.v1_str}/auth/google/callback",
            f"{settings.api.v1_str}/docs",
            f"{settings.api.v1_str}/redoc",
            f"{settings.api.v1_str}/openapi.json",
        ]

        path = request.url.path
        return not any(path.startswith(public_path) for public_path in public_paths)

    async def _check_session_activity(self, token: str) -> bool:
        """
        Verificar si la sesión está activa y no ha expirado por inactividad.

        Args:
            token: Token JWT

        Returns:
            bool: True si la sesión es válida
        """
        # Verificar token JWT primero
        logger.info(f"🔍 SessionTrackingMiddleware: Verificando token (primeros 20 chars): {token[:20]}...")
        token_data = verify_token(token, expected_type="access")
        if not token_data:
            logger.warning(f"⚠️ SessionTrackingMiddleware: Token inválido o expirado")
            return False

        user_id = token_data.user_id
        current_time = datetime.utcnow()
        logger.info(f"✅ SessionTrackingMiddleware: Token válido para user {user_id}")

        # Verificar última actividad
        last_activity = self.user_sessions.get(user_id)
        if last_activity:
            time_since_activity = current_time - last_activity
            if time_since_activity > self.inactivity_timeout:
                # Remover sesión expirada
                self.user_sessions.pop(user_id, None)
                logger.info(f"⏰ Sesión expirada por inactividad: {user_id}")
                return False

        return True

    async def _update_session_activity(self, token: str) -> None:
        """
        Actualizar la última actividad del usuario.

        Args:
            token: Token JWT
        """
        token_data = verify_token(token, expected_type="access")
        if token_data:
            self.user_sessions[token_data.user_id] = datetime.utcnow()


class AuthLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware para logging de eventos de autenticación.

    Registra intentos de login, logout y accesos a recursos protegidos.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        """
        Procesar request y hacer logging de eventos de auth.

        Args:
            request: Request HTTP
            call_next: Siguiente middleware/handler

        Returns:
            Response: Respuesta HTTP
        """
        # Extraer información de autenticación
        auth_info = self._extract_auth_info(request)

        # Ejecutar request
        response = await call_next(request)

        # Log eventos de autenticación
        await self._log_auth_event(request, response, auth_info)

        return response

    def _extract_auth_info(self, request: Request) -> Dict[str, Any]:
        """
        Extraer información de autenticación del request.

        Args:
            request: Request HTTP

        Returns:
            Dict con información de autenticación
        """
        auth_info = {
            "has_token": False,
            "user_id": None,
            "user_email": None,
            "user_agent": request.headers.get("user-agent", "Unknown")
        }

        # Extraer token si existe
        auth_header = request.headers.get("authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
            auth_info["has_token"] = True

            # Decodificar token para obtener info del usuario
            token_data = verify_token(token, expected_type="access")
            if token_data:
                auth_info["user_id"] = token_data.user_id
                auth_info["user_email"] = token_data.email

        return auth_info

    async def _log_auth_event(
        self, 
        request: Request, 
        response: Response, 
        auth_info: Dict[str, Any]
    ) -> None:
        """
        Log eventos de autenticación.

        Args:
            request: Request HTTP
            response: Response HTTP
            auth_info: Información de autenticación extraída
        """
        path = request.url.path
        method = request.method
        status_code = response.status_code

        # Log eventos específicos de autenticación
        if path.endswith("/auth/login"):
            if status_code == 200:
                logger.info(
                    f"User-Agent: {auth_info['user_agent']}"
                )
            else:
                logger.warning(
                    f"Status: {status_code} - User-Agent: {auth_info['user_agent']}"
                )

        elif path.endswith("/auth/logout"):
            if auth_info["user_id"]:
                logger.info(
                    f"🔐 Logout - Usuario: {auth_info['user_id']} - "
                )

        # Log accesos a recursos protegidos con errores de auth
        elif auth_info["has_token"] and status_code == 401:
            logger.warning(
                f"🔒 Acceso denegado - Usuario: {auth_info.get('user_id', 'Unknown')} - "
            )

        # Log accesos exitosos a recursos protegidos (solo DEBUG)
        elif auth_info["has_token"] and status_code == 200 and settings.debug:
            logger.debug(
                f"🔓 Acceso autorizado - Usuario: {auth_info['user_id']} - "
            )

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from src.core.config import settings
from src.core.logging import configure_logging, get_logger
from src.api.auth import router as auth_router
from src.api.password_reset import router as password_reset_router
from src.api.tenant import router as tenant_router
from src.api.registration import router as registration_router
from src.api.membership import router as membership_router
from src.api.certificate import router as certificate_router
from src.api.files import router as files_router
from src.api.email import router as email_router
from src.api.news import router as news_router
from src.api.user_communities import router as user_communities_router
from src.api.projects import router as projects_router
from src.api.spaces import router as spaces_router
from src.api.reservations import router as reservations_router
from src.core.middleware import SessionTrackingMiddleware, AuthLoggingMiddleware
from src.services.auth import AuthInitializer
from src.services.news_initializer import NewsInitializer
from src.database.session import get_transaction_session
from src.database.utils import DatabaseSetup


# Configurar logging
configure_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Gestión del ciclo de vida de la aplicación FastAPI.

    Inicializa recursos al inicio y los limpia al cierre.
    """
    logger.info("🚀 Iniciando Sistema Unidad Territorial Backend...")

    try:
        # Configurar base de datos
        database_setup = DatabaseSetup()
        await database_setup.initialize()
        logger.info("✅ Base de datos configurada correctamente")

        async with get_transaction_session() as session:
            await AuthInitializer.initialize_auth_data(session)
        logger.info("✅ Datos de autenticación inicializados")

        # Inicializar noticias de ejemplo
        async with get_transaction_session() as session:
            await NewsInitializer.initialize_sample_data(session)
        logger.info("✅ Datos de noticias inicializados")

        yield

    except Exception as e:
        logger.error(f"❌ Error durante la inicialización: {e}")
        raise
    finally:
        logger.info("🔄 Cerrando Sistema Unidad Territorial Backend...")


# Crear aplicación FastAPI
app = FastAPI(
    title=settings.api.project_name,
    version="1.0.0",
    description="API del Sistema Unidad Territorial - Gestión de autenticación y roles",
    docs_url=f"{settings.api.v1_str}/docs",
    redoc_url=f"{settings.api.v1_str}/redoc",
    openapi_url=f"{settings.api.v1_str}/openapi.json",
    lifespan=lifespan
)

# Configurar middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4200"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Agregar middleware de autenticación
app.add_middleware(SessionTrackingMiddleware, inactivity_timeout_minutes=30)
app.add_middleware(AuthLoggingMiddleware)


# Manejadores de errores globales
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Manejador para errores HTTP."""
    logger.warning(f"HTTP {exc.status_code}: {exc.detail} - {request.url}")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "detail": exc.detail,
            "error_code": f"HTTP_{exc.status_code}",
            "path": str(request.url.path)
        }
    )


@app.exception_handler(SQLAlchemyError)
async def sqlalchemy_exception_handler(request: Request, exc: SQLAlchemyError):
    """Manejador para errores de base de datos."""
    logger.error(f"Error de base de datos: {exc} - {request.url}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Error interno de base de datos",
            "error_code": "DATABASE_ERROR",
            "path": str(request.url.path)
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Manejador para errores generales."""
    logger.error(f"Error no manejado: {exc} - {request.url}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Error interno del servidor",
            "error_code": "INTERNAL_ERROR",
            "path": str(request.url.path)
        }
    )


# Middleware para logging de requests
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Middleware para logging de todas las requests."""
    start_time = logger.info(f"🔄 {request.method} {request.url}")
    
    try:
        response = await call_next(request)
        logger.info(f"✅ {request.method} {request.url} - {response.status_code}")
        return response
    except Exception as e:
        logger.error(f"❌ {request.method} {request.url} - Error: {e}")
        raise


# Incluir routers
app.include_router(auth_router, prefix=settings.api.v1_str)
app.include_router(password_reset_router, prefix=settings.api.v1_str)
app.include_router(tenant_router, prefix=settings.api.v1_str)
app.include_router(registration_router, prefix=settings.api.v1_str)
app.include_router(membership_router, prefix=settings.api.v1_str)
app.include_router(certificate_router, prefix=settings.api.v1_str)
app.include_router(files_router)
app.include_router(email_router, prefix=settings.api.v1_str)
app.include_router(news_router, prefix=settings.api.v1_str)
app.include_router(user_communities_router, prefix=settings.api.v1_str)
app.include_router(projects_router, prefix=settings.api.v1_str)
app.include_router(spaces_router, prefix=settings.api.v1_str)
app.include_router(reservations_router, prefix=settings.api.v1_str)


# Endpoint de salud
@app.get("/health", tags=["Sistema"])
async def health_check():
    """
    Endpoint de verificación de salud del sistema.

    Retorna el estado actual del servidor.
    """
    return {
        "status": "healthy",
        "service": "Sistema Unidad Territorial Backend",
        "version": "1.0.0",
        "environment": settings.environment
    }


# Endpoint raíz
@app.get("/", tags=["Sistema"])
async def root():
    """
    Endpoint raíz del API.

    Información básica sobre el servicio.
    """
    return {
        "message": "Sistema Unidad Territorial - Backend API",
        "version": "1.0.0",
        "docs": f"{settings.api.v1_str}/docs",
        "health": "/health"
    }


# Endpoint de información del API
@app.get(f"{settings.api.v1_str}/info", tags=["Sistema"])
async def api_info():
    """
    Información detallada del API.

    Incluye versión, configuración y endpoints disponibles.
    """
    return {
        "api_version": "v1",
        "service": settings.api.project_name,
        "version": "1.0.0",
        "environment": settings.environment,
        "debug": settings.debug,
        "endpoints": {
            "authentication": f"{settings.api.v1_str}/auth",
            "docs": f"{settings.api.v1_str}/docs",
            "health": "/health"
        }
    }


if __name__ == "__main__":
    import uvicorn

    # Ejecutar servidor en modo desarrollo
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
        log_level="debug" if settings.debug else "info"
    )

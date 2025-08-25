from collections.abc import AsyncGenerator
from typing import TypeVar
import asyncio
import contextlib

from sqlalchemy import exc, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from src.core.config import settings
from src.core.logging import get_logger
from src.database import Base


logger = get_logger(__name__)
Model = TypeVar("Model", bound=Base)

engine = create_async_engine(
    settings.database.async_url,
    echo=settings.debug,
    pool_size=settings.database.pool_size,
    max_overflow=settings.database.max_overflow,
    # Ajustes para evitar problemas con greenlets
    pool_pre_ping=True,
    pool_recycle=3600,  # Reciclar conexiones cada hora
    future=True
)

# Crear session factory simple (sin scoped_session)
async_session_factory = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Get a database session for FastAPI endpoints.

    Yields:
        AsyncSession: Database session

    Raises:
        SQLAlchemyError: If database connection fails
    """
    # Verificar que estamos en un contexto asyncio
    try:
        asyncio.get_running_loop()
        logger.debug("Creando nueva sesión de base de datos para FastAPI")
    except RuntimeError:
        logger.critical("Intentando obtener sesión de base de datos fuera de un contexto asyncio")
        raise RuntimeError("get_db_session debe ser llamado desde un contexto asyncio")
    
    # Crear sesión directamente sin contextvars
    session = async_session_factory()
    try:
        logger.debug("Sesión de base de datos creada correctamente")
        yield session
        logger.debug("Confirmando transacción en la sesión de base de datos")
        await session.commit()
        logger.debug("Transacción confirmada correctamente")
    except exc.SQLAlchemyError as error:
        logger.error(f"Error de base de datos: {error}", exc_info=True)
        logger.debug("Realizando rollback de la transacción")
        await session.rollback()
        raise
    finally:
        logger.debug("Cerrando sesión de base de datos")
        await session.close()
        logger.debug("Sesión de base de datos cerrada correctamente")


@contextlib.asynccontextmanager
async def get_transaction_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Gestor de contexto que proporciona una sesión de base de datos dentro de un bloque
    y maneja automáticamente commit/rollback.
    
    Ejemplo:
        async with get_transaction_session() as session:
            # hacer operaciones con la sesión
            # al salir del bloque se hace commit o rollback automáticamente
    """
    session = async_session_factory()
    try:
        yield session
        await session.commit()
    except:
        await session.rollback()
        raise
    finally:
        await session.close()

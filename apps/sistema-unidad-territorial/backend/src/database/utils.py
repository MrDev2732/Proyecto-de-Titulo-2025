from sqlalchemy import text, Connection
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.logging import get_logger
from src.database.session import get_transaction_session


logger = get_logger(__name__)


class DatabaseSetup:
    """Utilities for database configuration."""

    @staticmethod
    def get_extensions_sql() -> list[str]:
        """
        Return SQL commands to create necessary PostgreSQL extensions.

        Returns:
            List of SQL commands to create extensions
        """
        return [
            'CREATE EXTENSION IF NOT EXISTS "uuid-ossp"',
            'CREATE EXTENSION IF NOT EXISTS "btree_gist"', 
            'CREATE EXTENSION IF NOT EXISTS "citext"'
        ]

    @staticmethod
    async def setup_extensions_async(session: AsyncSession) -> None:
        """
        Configure necessary extensions in the database asynchronously.

        Args:
            session: Async database session
        """
        extensions_sql = DatabaseSetup.get_extensions_sql()
        for sql_command in extensions_sql:
            await session.execute(text(sql_command))
        await session.commit()

    @staticmethod
    def setup_extensions_sync(connection: Connection) -> None:
        """
        Configure necessary extensions in the database synchronously.
        Usado por Alembic durante las migraciones.

        Args:
            connection: Database connection
        """
        extensions_sql = DatabaseSetup.get_extensions_sql()
        for sql_command in extensions_sql:
            connection.execute(text(sql_command))
        connection.commit()

    @staticmethod
    async def initialize() -> None:
        """
        Inicializar configuración completa de la base de datos.
        """
        try:
            async with get_transaction_session() as session:
                logger.info("🔧 Configurando extensiones de PostgreSQL...")
                await DatabaseSetup.setup_extensions_async(session)

                logger.info("✅ Configuración de base de datos completada")
        except Exception as e:
            logger.error(f"❌ Error en inicialización de base de datos: {e}")
            raise

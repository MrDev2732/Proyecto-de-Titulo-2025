from sqlalchemy import text, Connection
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.logging import get_logger


logger = get_logger(__name__)


class DatabaseSetup:
    """Utilities for database configuration."""

    @staticmethod
    def get_extensions_sql() -> str:
        """
        Return SQL to create necessary PostgreSQL extensions.

        Returns:
            String with SQL commands to create extensions
        """
        return """
        -- Extensions required for the territorial unit system
        CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
        CREATE EXTENSION IF NOT EXISTS "btree_gist";
        CREATE EXTENSION IF NOT EXISTS "citext";
        """

    @staticmethod
    def get_exclude_constraint_sql() -> str:
        """
        Return SQL to create exclusion constraint on reservations.

        This constraint prevents overlapping reservations for the same space.
        Must be executed after creating tables.

        Returns:
            String with SQL command for exclusion constraint
        """
        return """
        -- Constraint to prevent overlapping reservations
        ALTER TABLE reservations ADD CONSTRAINT exclude_reservation_overlap
        EXCLUDE USING gist (
            space_id WITH =,
            tstzrange(start_time, end_time, '[)') WITH &&
        ) WHERE (status IN ('PENDING', 'CONFIRMED'));
        """

    @staticmethod
    def get_public_view_sql() -> str:
        """
        Return SQL to create public views with masked PII.

        Returns:
            String with SQL to create views
        """
        return """
        -- Public view for residents with masked RUT
        CREATE OR REPLACE VIEW v_residents_public AS
        SELECT
          id,
          regexp_replace(rut, '(^[0-9]{1,2}\\.?[0-9]{3}\\.?)[0-9]{3}', '\\1***') AS rut_masked,
          name,
          neighborhood_unit
        FROM residents;
        """

    @staticmethod
    async def setup_extensions_async(session: AsyncSession) -> None:
        """
        Configure necessary extensions in the database asynchronously.

        Args:
            session: Async database session
        """
        await session.execute(text(DatabaseSetup.get_extensions_sql()))
        await session.commit()

    @staticmethod
    async def setup_exclude_constraints_async(session: AsyncSession) -> None:
        """
        Configure exclusion constraints asynchronously.

        Args:
            session: Async database session
        """
        try:
            await session.execute(text(DatabaseSetup.get_exclude_constraint_sql()))
            await session.commit()
        except Exception as e:
            # Constraint might already exist
            await session.rollback()
            logger.info(f"Warning: Could not create exclusion constraint: {e}")

    @staticmethod
    async def setup_public_views_async(session: AsyncSession) -> None:
        """
        Create public views with masked data asynchronously.

        Args:
            session: Async database session
        """
        try:
            await session.execute(text(DatabaseSetup.get_public_view_sql()))
            await session.commit()
        except Exception as e:
            await session.rollback()
            logger.info(f"Warning: Could not create public views: {e}")

    @staticmethod
    def setup_extensions_sync(connection: Connection) -> None:
        """
        Configure necessary extensions in the database synchronously.
        Usado por Alembic durante las migraciones.

        Args:
            connection: Database connection
        """
        connection.execute(text(DatabaseSetup.get_extensions_sql()))
        connection.commit()

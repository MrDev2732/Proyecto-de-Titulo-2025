"""
Utility functions for managing database views.
"""

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.logging import get_logger

from src.database.views import ALL_VIEWS_SQL, ALL_DROP_VIEWS_SQL


logger = get_logger(__name__)


async def create_all_views(session: AsyncSession) -> None:
    """
    Create all database views.

    Args:
        session: Database session
    """
    try:
        for view_name, sql in ALL_VIEWS_SQL.items():
            await session.execute(text(sql))
            logger.info(f"✅ Created view: {view_name}")

        logger.info(f"✅ Successfully created {len(ALL_VIEWS_SQL)} database views")

    except Exception as e:
        logger.error(f"❌ Error creating views: {e}")
        raise


async def drop_all_views(session: AsyncSession) -> None:
    """
    Drop all database views.

    Args:
        session: Database session
    """
    try:
        for sql in ALL_DROP_VIEWS_SQL:
            await session.execute(text(sql))

        logger.info(f"✅ Successfully dropped {len(ALL_DROP_VIEWS_SQL)} database views")

    except Exception as e:
        logger.error(f"❌ Error dropping views: {e}")
        raise


async def recreate_all_views(session: AsyncSession) -> None:
    """
    Drop and recreate all database views.

    Args:
        session: Database session
    """
    logger.info("🔄 Recreating all database views...")
    await drop_all_views(session)
    await create_all_views(session)
    logger.info("✅ All database views recreated successfully")

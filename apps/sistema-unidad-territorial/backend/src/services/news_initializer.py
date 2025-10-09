"""
Inicializador de noticias de ejemplo para el sistema.
"""

from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.database.models import News, Tenant
from src.database.utils import now_chile
from src.core.logging import get_logger

logger = get_logger(__name__)


class NewsInitializer:
    """Inicializador de noticias de ejemplo."""

    @staticmethod
    async def create_sample_news(session: AsyncSession) -> None:
        """
        Crear noticias de ejemplo para demostración.

        Args:
            session: Sesión de base de datos
        """
        try:
            # Verificar si ya existen noticias
            existing_news = await session.execute(select(News).limit(1))
            if existing_news.scalar_one_or_none():
                logger.info("ℹ️  Ya existen noticias en el sistema")
                return

            # Obtener el primer tenant disponible
            tenant_result = await session.execute(select(Tenant).limit(1))
            tenant = tenant_result.scalar_one_or_none()

            if not tenant:
                logger.warning("⚠️ No hay tenants disponibles para crear noticias")
                return

            current_time = now_chile()

            # Crear noticias de ejemplo
            sample_news = [
                {
                    "title": "Bienvenidos al Portal del Residente",
                    "body": "Nos complace anunciar el lanzamiento de nuestro nuevo portal digital para residentes. Aquí podrás acceder a noticias de la comunidad, descargar certificados de residencia y mantenerte informado sobre las actividades vecinales.",
                    "visible_from": current_time - timedelta(days=7),
                    "visible_until": None
                },
                {
                    "title": "Reunión Vecinal - Próximo Sábado",
                    "body": "Los invitamos a participar en la reunión vecinal que se realizará el próximo sábado 14 de octubre a las 10:00 AM en la sede comunitaria. Trataremos temas importantes sobre el mantenimiento de áreas verdes y la organización de actividades para el mes de noviembre.",
                    "visible_from": current_time - timedelta(days=3),
                    "visible_until": current_time + timedelta(days=4)
                },
                {
                    "title": "Mantenimiento de Áreas Verdes",
                    "body": "Informamos que durante la próxima semana se realizarán trabajos de mantenimiento en las áreas verdes de la comunidad. Los trabajos incluyen poda de árboles, riego y plantación de nuevas especies. Agradecemos su comprensión por las molestias que esto pueda ocasionar.",
                    "visible_from": current_time - timedelta(days=1),
                    "visible_until": current_time + timedelta(days=14)
                },
                {
                    "title": "Nuevo Sistema de Certificados Digitales",
                    "body": "A partir de ahora, los residentes pueden descargar sus certificados de residencia directamente desde este portal. El proceso es rápido y seguro, y los certificados tienen validez oficial para todos los trámites municipales.",
                    "visible_from": current_time - timedelta(hours=12),
                    "visible_until": None
                },
                {
                    "title": "Actividades Deportivas de Octubre",
                    "body": "Durante el mes de octubre tendremos diversas actividades deportivas para toda la familia. Incluye torneos de fútbol, clases de yoga al aire libre y caminatas grupales. Las inscripciones están abiertas en la sede comunitaria.",
                    "visible_from": current_time - timedelta(days=5),
                    "visible_until": current_time + timedelta(days=25)
                }
            ]

            # Crear y guardar las noticias
            created_count = 0
            for news_data in sample_news:
                news = News(
                    tenant_id=tenant.id,
                    title=news_data["title"],
                    body=news_data["body"],
                    visible_from=news_data["visible_from"],
                    visible_until=news_data["visible_until"]
                )
                session.add(news)
                created_count += 1

            await session.commit()
            logger.info(f"✅ Creadas {created_count} noticias de ejemplo")

        except Exception as e:
            logger.error(f"❌ Error creando noticias de ejemplo: {e}")
            await session.rollback()
            raise

    @staticmethod
    async def initialize_sample_data(session: AsyncSession) -> None:
        """
        Inicializar datos de ejemplo para noticias.

        Args:
            session: Sesión de base de datos
        """
        logger.info("🗞️ Inicializando datos de noticias de ejemplo...")
        await NewsInitializer.create_sample_news(session)
        logger.info("✅ Inicialización de noticias completada")

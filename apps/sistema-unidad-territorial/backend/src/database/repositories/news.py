from typing import Optional, List, Tuple
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from src.database.models.news import News
from src.database.models.community import ResidentMembership
from src.database.enums import MembershipStatus
from src.database.utils import now_chile
from datetime import datetime
from sqlalchemy import select, and_, or_, func


class NewsRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, news: News) -> News:
        self.db.add(news)
        await self.db.flush()
        await self.db.commit()
        await self.db.refresh(news)
        return news

    async def get(self, news_id) -> Optional[News]:
        result = await self.db.execute(select(News).where(News.id == news_id, News.deleted_at == None))
        return result.scalar_one_or_none()

    async def list(self, only_active: bool = True) -> List[News]:
        stmt = select(News).where(News.deleted_at == None)
        if only_active:
            now = now_chile()
            stmt = stmt.where(News.visible_from <= now)
            stmt = stmt.where((News.visible_until == None) | (News.visible_until >= now))
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def disable(self, news_id) -> Optional[News]:
        news = await self.get(news_id)
        if news:
            news.deleted_at = datetime.utcnow()
            await self.db.flush()
            await self.db.commit()
            await self.db.refresh(news)
        return news

    async def delete(self, news_id) -> Optional[News]:
        result = await self.db.execute(select(News).where(News.id == news_id))
        news = result.scalar_one_or_none()
        if news:
            await self.db.delete(news)
            await self.db.commit()
        return news

    async def get_user_communities(self, user_id: UUID) -> List[UUID]:
        """
        Obtener IDs de todas las comunidades donde el usuario tiene membresía APPROVED.

        Args:
            user_id: ID del usuario

        Returns:
            Lista de UUIDs de comunidades
        """
        result = await self.db.execute(
            select(ResidentMembership.community_id).where(
                and_(
                    ResidentMembership.user_id == user_id,
                    ResidentMembership.status == MembershipStatus.APPROVED,
                    ResidentMembership.deleted_at.is_(None)
                )
            )
        )
        return [row[0] for row in result.all()]

    async def get_active_news_for_communities(
        self,
        community_ids: List[UUID],
        tenant_id: UUID,
        page: int = 1,
        per_page: int = 10,
    ) -> Tuple[List[News], int, int]:
        """
        Obtener noticias activas de las comunidades especificadas con paginación.

        Args:
            community_ids: Lista de IDs de comunidades a consultar
            tenant_id: ID del tenant para seguridad adicional
            page: Número de página
            per_page: Elementos por página

        Returns:
            Tupla de (lista de noticias, total de elementos, total de páginas)
        """
        current_time = now_chile()

        # Construir filtros base
        filters = [
            News.tenant_id == tenant_id,
            News.visible_from <= current_time,
            or_(
                News.visible_until.is_(None),
                News.visible_until >= current_time
            ),
            News.deleted_at.is_(None),
            or_(
                News.community_id.in_(community_ids),
                News.community_id.is_(None)
            )
        ]

        # Query base para noticias activas
        base_query = select(News).where(
            and_(*filters)
        ).order_by(News.created_at.desc())

        # Contar total de noticias
        count_query = select(func.count()).select_from(News).where(
            and_(*filters)
        )
        count_result = await self.db.execute(count_query)
        total = count_result.scalar()

        # Calcular paginación
        total_pages = (total + per_page - 1) // per_page
        offset = (page - 1) * per_page

        # Ejecutar query con paginación
        paginated_query = base_query.offset(offset).limit(per_page)
        result = await self.db.execute(paginated_query)
        news_list = result.scalars().all()

        return list(news_list), total, total_pages

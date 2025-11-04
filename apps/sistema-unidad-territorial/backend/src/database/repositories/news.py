from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from src.database.models.news import News
from src.database.utils import now_chile
from datetime import datetime
from sqlalchemy import select


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

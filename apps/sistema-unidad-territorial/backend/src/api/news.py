"""
Endpoints de noticias para la API.
"""

from typing import List, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_

from src.database.session import get_db_session
from src.database.models import News
from src.schemas import ErrorResponse
from src.core.logging import get_logger
from src.database.utils import now_chile
from pydantic import BaseModel


logger = get_logger(__name__)

# Router para endpoints de noticias
router = APIRouter(prefix="/news", tags=["Noticias"])


class NewsResponse(BaseModel):
    """Response schema para noticias."""
    id: str
    title: str
    body: str
    visible_from: datetime
    visible_until: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class NewsListResponse(BaseModel):
    """Response schema para lista de noticias."""
    news: List[NewsResponse]
    total: int
    page: int
    per_page: int
    total_pages: int


@router.get(
    "/public",
    response_model=NewsListResponse,
    summary="Obtener noticias públicas activas",
    description="Retorna las noticias públicas que están actualmente visibles para residentes",
    responses={
        500: {"model": ErrorResponse, "description": "Error interno del servidor"}
    }
)
async def get_public_news(
    page: int = Query(1, ge=1, description="Número de página"),
    per_page: int = Query(10, ge=1, le=50, description="Elementos por página"),
    session: AsyncSession = Depends(get_db_session)
) -> NewsListResponse:
    """
    Obtener noticias públicas activas.

    **Endpoint público** - No requiere autenticación.

    Retorna las noticias que están actualmente visibles según sus fechas de visibilidad.
    Las noticias se ordenan por fecha de creación (más recientes primero).

    **Parámetros:**
    - **page**: Número de página (por defecto 1)
    - **per_page**: Elementos por página (por defecto 10, máximo 50)

    **Filtros aplicados:**
    - Solo noticias activas (visible_from <= ahora <= visible_until)
    - Ordenadas por fecha de creación descendente
    """
    try:
        current_time = now_chile()

        # Query base para noticias activas
        base_query = select(News).where(
            and_(
                News.visible_from <= current_time,
                or_(
                    News.visible_until.is_(None),
                    News.visible_until >= current_time
                )
            )
        ).order_by(News.created_at.desc())

        # Contar total de noticias activas
        count_query = select(News.id).where(
            and_(
                News.visible_from <= current_time,
                or_(
                    News.visible_until.is_(None),
                    News.visible_until >= current_time
                )
            )
        )

        total_result = await session.execute(count_query)
        total = len(total_result.all())

        # Aplicar paginación
        offset = (page - 1) * per_page
        paginated_query = base_query.offset(offset).limit(per_page)

        # Ejecutar query
        result = await session.execute(paginated_query)
        news_list = result.scalars().all()

        # Convertir a response
        news_responses = [
            NewsResponse(
                id=str(news.id),
                title=news.title,
                body=news.body,
                visible_from=news.visible_from,
                visible_until=news.visible_until,
                created_at=news.created_at,
                updated_at=news.updated_at
            )
            for news in news_list
        ]

        # Calcular páginas totales
        total_pages = (total + per_page - 1) // per_page

        logger.info(f"✅ Retrieved {len(news_responses)} public news (page {page}/{total_pages})")

        return NewsListResponse(
            news=news_responses,
            total=total,
            page=page,
            per_page=per_page,
            total_pages=total_pages
        )

    except Exception as e:
        logger.error(f"❌ Error retrieving public news: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno del servidor al obtener las noticias"
        )

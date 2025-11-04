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
from src.database.repositories.news import NewsRepository
from src.schemas.news import NewsCreate, NewsUpdate, NewsResponse, NewsListResponse
from src.schemas import ErrorResponse
from src.core.logging import get_logger
from src.database.utils import now_chile
from uuid import UUID
from src.core.dependencies import get_current_user  # Ajusta a tu proyecto real
from typing import Annotated
from src.database.models import Tenant

logger = get_logger(__name__)
router = APIRouter(prefix="/news", tags=["Noticias"])


# Endpoint público de paginación
@router.get(
    "/public",
    response_model=NewsListResponse,
    summary="Obtener noticias públicas activas",
    description="Retorna las noticias públicas que están actualmente visibles para residentes",
    responses={500: {"model": ErrorResponse, "description": "Error interno del servidor"}},
)
async def get_public_news(
        page: int = Query(1, ge=1, description="Número de página"),
        per_page: int = Query(10, ge=1, le=50, description="Elementos por página"),
        session: AsyncSession = Depends(get_db_session)
) -> NewsListResponse:
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


# -------------------- ENDPOINTS CRUD --------------------
# Endpoint para crear noticia (POST, usa current_user.tenant_id SIEMPRE)
@router.post("/", response_model=NewsResponse, summary="Crear noticia", description="Crea una noticia nueva", status_code=201)
async def create_news(
    news: NewsCreate,
    session: AsyncSession = Depends(get_db_session),
    current_user=Depends(get_current_user)
):
    try:
        repo = NewsRepository(session)
        noticia = News(
            title=news.title,
            body=news.body,
            visible_from=news.visible_from,
            visible_until=news.visible_until,
            tenant_id=current_user.tenant_id  # Siempre uso el tenant de la sesión
        )
        noticia = await repo.create(noticia)
        return NewsResponse(
            id=str(noticia.id),
            title=noticia.title,
            body=noticia.body,
            visible_from=noticia.visible_from,
            visible_until=noticia.visible_until,
            created_at=noticia.created_at,
            updated_at=noticia.updated_at
        )
    except Exception as e:
        logger.error(f"❌ Error creating news: {e}")
        raise HTTPException(status_code=400, detail="No se pudo crear la noticia")


# Endpoint para editar noticia (PUT). Solo puedes editar si es de tu tenant
@router.post("/{news_id}", response_model=NewsResponse, summary="Editar noticia", description="Edita los detalles de una noticia")
async def update_news(news_id: str, news_data: NewsUpdate, session: AsyncSession = Depends(get_db_session), current_user=Depends(get_current_user)):
    try:
        repo = NewsRepository(session)
        noticia = await repo.get(news_id)
        if not noticia:
            raise HTTPException(status_code=404, detail="Noticia no encontrada")
        if str(noticia.tenant_id) != str(current_user.tenant_id):
            raise HTTPException(status_code=403, detail="No puedes modificar noticias de otro tenant.")
        for field, value in news_data.dict(exclude_unset=True).items():
            setattr(noticia, field, value)
        await session.commit()
        await session.refresh(noticia)
        return NewsResponse(
            id=str(noticia.id),
            title=noticia.title,
            body=noticia.body,
            visible_from=noticia.visible_from,
            visible_until=noticia.visible_until,
            created_at=noticia.created_at,
            updated_at=noticia.updated_at
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error updating news: {e}")
        raise HTTPException(status_code=400, detail="No se pudo editar la noticia")


# Endpoint para deshabilitar noticia (soft delete). Solo si es de tu tenant
@router.delete("/{news_id}", summary="Deshabilitar noticia (soft delete)", description="Deshabilita una noticia en vez de eliminarla físicamente", status_code=204)
async def disable_news(news_id: str, session: AsyncSession = Depends(get_db_session), current_user=Depends(get_current_user)):
    try:
        repo = NewsRepository(session)
        noticia = await repo.get(news_id)
        if not noticia:
            raise HTTPException(status_code=404, detail="Noticia no encontrada")
        if str(noticia.tenant_id) != str(current_user.tenant_id):
            raise HTTPException(status_code=403, detail="No puedes deshabilitar noticias de otro tenant.")
        await repo.disable(news_id)
        return  # 204 No Content
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error disabling (soft deleting) news: {e}")
        raise HTTPException(status_code=400, detail="No se pudo deshabilitar la noticia")

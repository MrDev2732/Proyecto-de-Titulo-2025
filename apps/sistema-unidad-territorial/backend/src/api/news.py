"""
Endpoints de noticias para la API.
"""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.session import get_db_session
from src.database.models import News, User
from src.database.enums import MembershipStatus
from src.schemas import ErrorResponse
from src.core.logging import get_logger
from src.core.dependencies import get_current_active_user, get_current_user
from src.database.repositories.news import NewsRepository
from src.database.repositories.resident import ResidentMembershipRepository
from src.schemas.news import NewsCreate, NewsUpdate, NewsResponse, NewsListResponse


logger = get_logger(__name__)
router = APIRouter(prefix="/news", tags=["Noticias"])


@router.get(
    "/my-communities",
    response_model=NewsListResponse,
    summary="Obtener noticias de mis comunidades",
    description="Retorna las noticias activas de las comunidades donde el usuario tiene membresía aprobada",
    responses={
        500: {"model": ErrorResponse, "description": "Error interno del servidor"}
    }
)
async def get_my_communities_news(
    page: int = Query(1, ge=1, description="Número de página"),
    per_page: int = Query(10, ge=1, le=50, description="Elementos por página"),
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db_session)
) -> NewsListResponse:
    """
    Obtener noticias activas de las comunidades del usuario.

    **Requiere autenticación** - Solo muestra noticias de comunidades donde tienes membresía APPROVED.

    Retorna las noticias que están actualmente visibles según sus fechas de visibilidad
    y que pertenecen a las comunidades donde el usuario tiene membresía aprobada.
    Las noticias se ordenan por fecha de creación (más recientes primero).

    **Parámetros:**
    - **page**: Número de página (por defecto 1)
    - **per_page**: Elementos por página (por defecto 10, máximo 50)

    **Filtros aplicados:**
    - Solo noticias de comunidades donde tienes membresía APPROVED
    - Solo noticias activas (visible_from <= ahora <= visible_until)
    - Ordenadas por fecha de creación descendente
    """
    try:
        # Validar tenant
        user_tenant_id = current_user.tenant_id
        if not user_tenant_id:
            logger.warning(f"⚠️ User {current_user.email} has no tenant_id")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Usuario no tiene un tenant asignado"
            )

        # Obtener noticias usando el repositorio
        repo = NewsRepository(session)

        # Obtener comunidades del usuario
        user_community_ids = await repo.get_user_communities(current_user.id)

        if not user_community_ids:
            logger.info(f"ℹ️ User {current_user.email} has no approved memberships")
            return NewsListResponse(
                news=[],
                total=0,
                page=page,
                per_page=per_page,
                total_pages=0
            )

        # Obtener noticias paginadas
        news_list, total, total_pages = await repo.get_active_news_for_communities(
            community_ids=user_community_ids,
            tenant_id=user_tenant_id,
            page=page,
            per_page=per_page,
        )

        # Convertir a response
        news_responses = [
            NewsResponse(
                id=str(news.id),
                title=news.title,
                body=news.body,
                community_id=str(news.community_id),
                visible_from=news.visible_from,
                visible_until=news.visible_until,
                created_at=news.created_at,
                updated_at=news.updated_at
            )
            for news in news_list
        ]

        logger.info(
            f"✅ Retrieved {len(news_responses)} news for user {current_user.email} "
            f"(page {page}/{total_pages}, {len(user_community_ids)} communities)"
        )

        return NewsListResponse(
            news=news_responses,
            total=total,
            page=page,
            per_page=per_page,
            total_pages=total_pages
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error retrieving user communities news: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno del servidor al obtener las noticias"
        )


@router.post("/", response_model=NewsResponse, summary="Crear noticia", description="Crea una noticia nueva", status_code=201)
async def create_news(
    news: NewsCreate,
    session: AsyncSession = Depends(get_db_session),
    current_user=Depends(get_current_user)
):
    """
    Crear una noticia en una comunidad.

    **Requiere:**
    - Membresía APPROVED en la comunidad especificada
    - El usuario debe pertenecer al mismo tenant que la comunidad
    """
    try:
        # Validar que el usuario tiene membresía aprobada en la comunidad
        membership = await ResidentMembershipRepository.find_user_membership_in_community(
            session,
            user_id=current_user.id,
            community_id=news.community_id
        )

        if not membership:
            logger.warning(
                f"⚠️ User {current_user.email} attempted to create news in community {news.community_id} without membership"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tienes membresía en esta comunidad"
            )

        if membership.status != MembershipStatus.APPROVED:
            logger.warning(
                f"⚠️ User {current_user.email} attempted to create news with non-approved membership (status: {membership.status})"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Tu membresía en esta comunidad no está aprobada (estado: {membership.status.value})"
            )

        # Crear la noticia
        repo = NewsRepository(session)
        noticia = News(
            title=news.title,
            body=news.body,
            community_id=news.community_id,
            visible_from=news.visible_from,
            visible_until=news.visible_until,
            tenant_id=current_user.tenant_id
        )
        noticia = await repo.create(noticia)

        logger.info(f"✅ User {current_user.email} created news {noticia.id} in community {news.community_id}")

        return NewsResponse(
            id=str(noticia.id),
            title=noticia.title,
            body=noticia.body,
            community_id=str(noticia.community_id),
            visible_from=noticia.visible_from,
            visible_until=noticia.visible_until,
            created_at=noticia.created_at,
            updated_at=noticia.updated_at
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error creating news: {e}")
        raise HTTPException(status_code=400, detail="No se pudo crear la noticia")


@router.post("/{news_id}", response_model=NewsResponse, summary="Editar noticia", description="Edita los detalles de una noticia")
async def update_news(news_id: str, news_data: NewsUpdate, session: AsyncSession = Depends(get_db_session), current_user=Depends(get_current_user)):
    """
    Editar una noticia existente.

    **Requiere:**
    - Membresía APPROVED en la comunidad de la noticia
    - Si se intenta cambiar community_id, también se requiere membresía en la nueva comunidad
    """
    try:
        repo = NewsRepository(session)
        noticia = await repo.get(news_id)
        if not noticia:
            raise HTTPException(status_code=404, detail="Noticia no encontrada")

        if str(noticia.tenant_id) != str(current_user.tenant_id):
            raise HTTPException(status_code=403, detail="No puedes modificar noticias de otro tenant.")

        # Validar que el usuario tiene membresía en la comunidad actual de la noticia
        membership = await ResidentMembershipRepository.find_user_membership_in_community(
            session,
            user_id=current_user.id,
            community_id=noticia.community_id
        )

        if not membership or membership.status != MembershipStatus.APPROVED:
            logger.warning(
                f"⚠️ User {current_user.email} attempted to edit news {news_id} without approved membership in community {noticia.community_id}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tienes membresía aprobada en la comunidad de esta noticia"
            )

        # Si se intenta cambiar el community_id, validar membresía en la nueva comunidad
        if news_data.community_id and str(news_data.community_id) != str(noticia.community_id):
            new_membership = await ResidentMembershipRepository.find_user_membership_in_community(
                session,
                user_id=current_user.id,
                community_id=news_data.community_id
            )

            if not new_membership or new_membership.status != MembershipStatus.APPROVED:
                logger.warning(
                    f"⚠️ User {current_user.email} attempted to move news {news_id} to community {news_data.community_id} without membership"
                )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="No tienes membresía aprobada en la comunidad destino"
                )

        # Aplicar actualizaciones
        for field, value in news_data.dict(exclude_unset=True).items():
            setattr(noticia, field, value)
        await session.commit()
        await session.refresh(noticia)

        logger.info(f"✅ User {current_user.email} updated news {news_id}")

        return NewsResponse(
            id=str(noticia.id),
            title=noticia.title,
            body=noticia.body,
            community_id=str(noticia.community_id),
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
    """
    Deshabilitar (soft delete) una noticia.

    **Requiere:**
    - Membresía APPROVED en la comunidad de la noticia
    """
    try:
        repo = NewsRepository(session)
        noticia = await repo.get(news_id)
        if not noticia:
            raise HTTPException(status_code=404, detail="Noticia no encontrada")

        if str(noticia.tenant_id) != str(current_user.tenant_id):
            raise HTTPException(status_code=403, detail="No puedes deshabilitar noticias de otro tenant.")

        # Validar que el usuario tiene membresía en la comunidad de la noticia
        membership = await ResidentMembershipRepository.find_user_membership_in_community(
            session,
            user_id=current_user.id,
            community_id=noticia.community_id
        )

        if not membership or membership.status != MembershipStatus.APPROVED:
            logger.warning(
                f"⚠️ User {current_user.email} attempted to delete news {news_id} without approved membership in community {noticia.community_id}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tienes membresía aprobada en la comunidad de esta noticia"
            )

        await repo.disable(news_id)
        logger.info(f"✅ User {current_user.email} disabled news {news_id}")
        return  # 204 No Content
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error disabling (soft deleting) news: {e}")
        raise HTTPException(status_code=400, detail="No se pudo deshabilitar la noticia")

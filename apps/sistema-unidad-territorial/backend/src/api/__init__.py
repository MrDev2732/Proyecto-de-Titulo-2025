from src.api.auth import router as auth_router
from src.api.community import router as community_router
from src.api.files import router as files_router


__all__ = [
    "auth_router",
    "community_router",
    "files_router"
]

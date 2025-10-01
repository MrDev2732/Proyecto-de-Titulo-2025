from src.api.auth import router as auth_router
from src.api.certificate import router as certificate_router
from src.api.email import router as email_router
from src.api.files import router as files_router
from src.api.membership import router as membership_router
from src.api.registration import router as registration_router
from src.api.tenant import router as tenant_router


__all__ = [
    "auth_router",
    "certificate_router",
    "email_router",
    "files_router",
    "membership_router",
    "registration_router",
    "tenant_router",
]

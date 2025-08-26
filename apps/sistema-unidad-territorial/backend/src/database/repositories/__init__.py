# Repositorios para acceso a datos

from src.database.repositories.auth_repository import (
    AuthRepository,
    OAuthRepository,
    SessionRepository,
)
from src.database.repositories.auth_log_repository import AuthenticationLogRepository
from src.database.repositories.role_repository import RoleRepository
from src.database.repositories.community_repository import (
    CommunityRepository,
    ResidentMembershipRepository,
    RegistrationRequestRepository,
)
from src.database.repositories.login_gating_repository import LoginGatingRepository


__all__ = [
    "AuthRepository",
    "OAuthRepository",
    "SessionRepository",
    "AuthenticationLogRepository",
    "RoleRepository",
    "CommunityRepository",
    "ResidentMembershipRepository", 
    "RegistrationRequestRepository",
    "LoginGatingRepository"
]

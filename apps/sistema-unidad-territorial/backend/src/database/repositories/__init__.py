# Repositorios para acceso a datos

from src.database.repositories.auth import (
    AuthRepository,
    OAuthRepository,
    SessionRepository,
)
from src.database.repositories.auth_log import AuthenticationLogRepository
from src.database.repositories.role import RoleRepository
from src.database.repositories.community import (
    CommunityRepository,
    ResidentMembershipRepository,
    RegistrationRequestRepository,
)
from src.database.repositories.resident import (
    AddressEvidenceRepository,
)
from src.database.repositories.login_gating import LoginGatingRepository
from src.database.repositories.tenant import TenantRepository


__all__ = [
    "AuthRepository",
    "OAuthRepository",
    "SessionRepository",
    "AuthenticationLogRepository",
    "RoleRepository",
    "CommunityRepository",
    "ResidentMembershipRepository", 
    "RegistrationRequestRepository",
    "AddressEvidenceRepository",
    "LoginGatingRepository",
    "TenantRepository"
]

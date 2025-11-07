# Repositorios para acceso a datos

from src.database.repositories.auth import (
    AuthRepository,
    OAuthRepository,
)
from src.database.repositories.auth_log import AuthenticationLogRepository
from src.database.repositories.role import RoleRepository
from src.database.repositories.community import (
    CommunityRepository,
)
from src.database.repositories.resident import (
    AddressEvidenceRepository, ResidentMembershipRepository
)
from src.database.repositories.login_gating import LoginGatingRepository
from src.database.repositories.tenant import TenantRepository
from src.database.repositories.session import SessionRepository
from src.database.repositories.registration import RegistrationRequestRepository
from src.database.repositories.projects import ProjectRepository
from src.database.repositories.spaces import SpaceRepository, ReservationRepository


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
    "TenantRepository",
    "ProjectRepository"
]

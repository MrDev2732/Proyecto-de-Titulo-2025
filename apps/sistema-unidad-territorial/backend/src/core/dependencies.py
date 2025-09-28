"""
Dependencias de FastAPI para autenticación y autorización.
"""

from typing import List, Optional
from uuid import UUID

from fastapi import Depends, HTTPException, status, Path
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, exists

from src.database import (
    User, 
    RegistrationRequest, 
    TenantRoleAssignment,
    CommunityRoleAssignment,
    Community
)
from src.database.session import get_db_session
from src.core.security import verify_token
from src.services.auth import AuthService
from src.core.logging import get_logger


logger = get_logger(__name__)

# Configuración del esquema de seguridad Bearer
security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    session: AsyncSession = Depends(get_db_session)
) -> User:
    """
    Dependencia para obtener el usuario actual validando token y sesión.

    Args:
        credentials: Credenciales de autorización HTTP
        session: Sesión de base de datos

    Returns:
        User: Usuario autenticado

    Raises:
        HTTPException: Si el token es inválido, la sesión no existe o el usuario no está activo
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No se pudieron validar las credenciales",
        headers={"WWW-Authenticate": "Bearer"},
    )

    # Validar token y sesión
    user = await AuthService.validate_session(session, credentials.credentials)
    if user is None:
        raise credentials_exception

    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Dependencia para obtener el usuario actual activo.

    Args:
        current_user: Usuario actual desde get_current_user

    Returns:
        User: Usuario activo

    Raises:
        HTTPException: Si el usuario está inactivo
    """
    if current_user.status != "active":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Usuario inactivo"
        )
    return current_user


def require_roles(allowed_roles: List[str]):
    """
    Factory para crear dependencias que requieren roles específicos.

    Args:
        allowed_roles: Lista de roles permitidos

    Returns:
        Función de dependencia que valida roles
    """
    async def role_dependency(
        current_user: User = Depends(get_current_active_user)
    ) -> User:
        """
        Dependencia que valida que el usuario tenga al menos uno de los roles requeridos.

        Args:
            current_user: Usuario actual activo

        Returns:
            User: Usuario con roles válidos

        Raises:
            HTTPException: Si el usuario no tiene los roles requeridos
        """
        # Obtener todos los roles del usuario de las tres tablas
        user_roles = []
        # Roles de sistema
        user_roles.extend([assignment.role.name for assignment in current_user.system_role_assignments])
        # Roles de tenant
        user_roles.extend([assignment.role.name for assignment in current_user.tenant_role_assignments])
        # Roles de comunidad
        user_roles.extend([assignment.role.name for assignment in current_user.community_role_assignments])

        # Verificar si el usuario tiene al menos uno de los roles requeridos
        if not any(role in user_roles for role in allowed_roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Se requiere uno de los siguientes roles: {', '.join(allowed_roles)}"
            )

        return current_user

    return role_dependency


# Dependencias predefinidas para roles comunes
require_admin = require_roles(["admin"])
require_admin_or_moderator = require_roles(["admin", "moderator"])


async def get_optional_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    session: AsyncSession = Depends(get_db_session)
) -> Optional[User]:
    """
    Dependencia para obtener el usuario actual de forma opcional.
    Útil para endpoints que pueden funcionar con o sin autenticación.

    Args:
        credentials: Credenciales de autorización HTTP (opcional)
        session: Sesión de base de datos

    Returns:
        User: Usuario autenticado o None si no hay token válido
    """
    if not credentials:
        return None

    # Verificar token
    token_data = verify_token(credentials.credentials, expected_type="access")
    if token_data is None:
        return None

    # Obtener usuario desde la base de datos
    try:
        user = await AuthService.get_user_by_id(session, UUID(token_data.user_id))
        return user
    except Exception as e:
        logger.warning(f"Error obteniendo usuario opcional: {e}")
        return None


def create_role_checker(role_name: str):
    """
    Factory para crear checkers de roles específicos.

    Args:
        role_name: Nombre del rol a verificar

    Returns:
        Función que verifica si el usuario tiene el rol específico
    """
    def check_role(user: User) -> bool:
        """
        Verificar si el usuario tiene un rol específico.

        Args:
            user: Usuario a verificar

        Returns:
            bool: True si el usuario tiene el rol
        """
        # Obtener todos los roles del usuario de las tres tablas
        user_roles = []
        # Roles de sistema
        user_roles.extend([assignment.role.name for assignment in user.system_role_assignments])
        # Roles de tenant
        user_roles.extend([assignment.role.name for assignment in user.tenant_role_assignments])
        # Roles de comunidad
        user_roles.extend([assignment.role.name for assignment in user.community_role_assignments])
        return role_name in user_roles

    return check_role


# Checkers predefinidos
is_admin = create_role_checker("admin")
is_moderator = create_role_checker("moderator")
is_user = create_role_checker("user")


async def require_community_access(
    community_id: UUID = Path(..., description="ID de la comunidad"),
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db_session)
) -> User:
    """
    Dependencia que valida que el usuario tenga acceso a una comunidad específica.

    Un usuario tiene acceso si:
    - Es SUPERADMIN (acceso global)
    - Es ADMIN del tenant que contiene la comunidad
    - Es MODERATOR específicamente de esa comunidad

    Args:
        community_id: ID de la comunidad a validar
        current_user: Usuario actual autenticado
        session: Sesión de base de datos

    Returns:
        User: Usuario con acceso validado

    Raises:
        HTTPException: Si el usuario no tiene acceso a la comunidad
    """
    # Obtener todos los roles del usuario
    user_roles = []
    # Roles de sistema
    user_roles.extend([assignment.role.name for assignment in current_user.system_role_assignments])
    # Roles de tenant
    user_roles.extend([assignment.role.name for assignment in current_user.tenant_role_assignments])
    # Roles de comunidad
    user_roles.extend([assignment.role.name for assignment in current_user.community_role_assignments])

    # SUPERADMIN tiene acceso a todo
    if "SUPERADMIN" in user_roles:
        logger.info(f"👑 SUPERADMIN {current_user.email} accessing community {community_id}")
        return current_user

    # Verificar si es ADMIN de tenant que contiene esta comunidad
    tenant_admin_result = await session.execute(
        select(TenantRoleAssignment)
        .join(TenantRoleAssignment.role)
        .where(
            and_(
                TenantRoleAssignment.user_id == current_user.id,
                TenantRoleAssignment.role.has(name="ADMIN"),
                # Verificar que el tenant contenga esta comunidad
                exists().where(
                    and_(
                        Community.id == community_id,
                        Community.tenant_id == TenantRoleAssignment.tenant_id
                    )
                )
            )
        )
    )

    # Verificar si es MODERATOR de esta comunidad específica
    community_moderator_result = await session.execute(
        select(CommunityRoleAssignment)
        .join(CommunityRoleAssignment.role)
        .where(
            and_(
                CommunityRoleAssignment.user_id == current_user.id,
                CommunityRoleAssignment.role.has(name="MODERATOR"),
                CommunityRoleAssignment.community_id == community_id
            )
        )
    )

    tenant_admin = tenant_admin_result.scalar_one_or_none()
    community_moderator = community_moderator_result.scalar_one_or_none()

    role_assignment = tenant_admin or community_moderator

    if not role_assignment:
        logger.warning(f"🚫 User {current_user.email} denied access to community {community_id}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permisos para acceder a esta comunidad"
        )

    logger.info(f"✅ User {current_user.email} granted access to community {community_id}")
    return current_user


async def require_registration_request_access(
    request_id: UUID = Path(..., description="ID de la solicitud de registro"),
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db_session)
) -> User:
    """
    Dependencia que valida que el usuario tenga acceso a una solicitud de registro específica.

    Obtiene la solicitud, extrae su community_id y valida que el usuario tenga permisos
    sobre esa comunidad específica.

    Args:
        request_id: ID de la solicitud de registro
        current_user: Usuario actual autenticado
        session: Sesión de base de datos

    Returns:
        User: Usuario con acceso validado

    Raises:
        HTTPException: Si la solicitud no existe o el usuario no tiene acceso
    """
    # Obtener la solicitud de registro
    result = await session.execute(
        select(RegistrationRequest).where(RegistrationRequest.id == request_id)
    )
    registration_request = result.scalar_one_or_none()

    if not registration_request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Solicitud de registro no encontrada"
        )

    # Validar acceso a la comunidad de la solicitud usando la dependencia existente
    # Simulamos el comportamiento de require_community_access pero con el community_id de la solicitud
    community_id = registration_request.community_id

    # Obtener todos los roles del usuario
    user_roles = []
    # Roles de sistema
    user_roles.extend([assignment.role.name for assignment in current_user.system_role_assignments])
    # Roles de tenant
    user_roles.extend([assignment.role.name for assignment in current_user.tenant_role_assignments])
    # Roles de comunidad
    user_roles.extend([assignment.role.name for assignment in current_user.community_role_assignments])

    # SUPERADMIN tiene acceso a todo
    if "SUPERADMIN" in user_roles:
        logger.info(f"👑 SUPERADMIN {current_user.email} accessing registration request {request_id}")
        return current_user

    # Verificar si es ADMIN de tenant que contiene esta comunidad
    tenant_admin_result = await session.execute(
        select(TenantRoleAssignment)
        .join(TenantRoleAssignment.role)
        .where(
            and_(
                TenantRoleAssignment.user_id == current_user.id,
                TenantRoleAssignment.role.has(name="ADMIN"),
                # Verificar que el tenant contenga esta comunidad
                exists().where(
                    and_(
                        Community.id == community_id,
                        Community.tenant_id == TenantRoleAssignment.tenant_id
                    )
                )
            )
        )
    )

    # Verificar si es MODERATOR de esta comunidad específica
    community_moderator_result = await session.execute(
        select(CommunityRoleAssignment)
        .join(CommunityRoleAssignment.role)
        .where(
            and_(
                CommunityRoleAssignment.user_id == current_user.id,
                CommunityRoleAssignment.role.has(name="MODERATOR"),
                CommunityRoleAssignment.community_id == community_id
            )
        )
    )

    tenant_admin = tenant_admin_result.scalar_one_or_none()
    community_moderator = community_moderator_result.scalar_one_or_none()

    role_assignment = tenant_admin or community_moderator

    if not role_assignment:
        logger.warning(f"🚫 User {current_user.email} denied access to registration request {request_id} (community {community_id})")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permisos para gestionar solicitudes de esta comunidad"
        )

    logger.info(f"✅ User {current_user.email} granted access to registration request {request_id}")
    return current_user

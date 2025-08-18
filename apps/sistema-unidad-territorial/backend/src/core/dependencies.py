"""
Dependencias de FastAPI para autenticación y autorización.
"""

from typing import List, Optional
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import User
from src.database.session import get_db_session
from src.core.security import verify_token
from src.services.auth_service import AuthService
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
        user_roles = [role.name for role in current_user.roles]

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
        user_roles = [role.name for role in user.roles]
        return role_name in user_roles

    return check_role


# Checkers predefinidos
is_admin = create_role_checker("admin")
is_moderator = create_role_checker("moderator")
is_user = create_role_checker("user")


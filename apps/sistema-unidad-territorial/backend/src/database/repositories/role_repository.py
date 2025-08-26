"""
Repository para el sistema unificado de roles y asignaciones.

Maneja todas las operaciones relacionadas con roles, asignaciones y permisos
usando el nuevo sistema unificado.
"""

from typing import List, Optional
from uuid import UUID

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.database.models import Role, RoleAssignment, User
from src.database.enums import RoleScope
from src.core.logging import get_logger


logger = get_logger(__name__)


class RoleRepository:
    """Repository para operaciones del sistema unificado de roles."""

    @staticmethod
    async def create_role(
        session: AsyncSession, 
        name: str, 
        scope: RoleScope
    ) -> Role:
        """
        Crear un nuevo rol con scope.

        Args:
            session: Sesión de base de datos
            name: Nombre del rol
            scope: Scope del rol (GLOBAL, TENANT, COMMUNITY)

        Returns:
            Role: Rol creado
        """
        role = Role(name=name, scope=scope)
        session.add(role)
        await session.flush()
        return role

    @staticmethod
    async def find_role_by_name_and_scope(
        session: AsyncSession, 
        name: str, 
        scope: RoleScope
    ) -> Optional[Role]:
        """
        Buscar rol por nombre y scope.

        Args:
            session: Sesión de base de datos
            name: Nombre del rol
            scope: Scope del rol

        Returns:
            Role: Rol encontrado o None
        """
        result = await session.execute(
            select(Role).where(
                and_(Role.name == name, Role.scope == scope)
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_all_roles(session: AsyncSession) -> List[Role]:
        """
        Obtener todos los roles del sistema.

        Args:
            session: Sesión de base de datos

        Returns:
            List[Role]: Lista de todos los roles
        """
        result = await session.execute(select(Role))
        return list(result.scalars().all())

    @staticmethod
    async def assign_role_to_user(
        session: AsyncSession,
        role_id: UUID,
        user_id: UUID,
        tenant_id: Optional[UUID] = None,
        community_id: Optional[UUID] = None
    ) -> RoleAssignment:
        """
        Asignar un rol a un usuario con contexto específico.

        Args:
            session: Sesión de base de datos
            role_id: ID del rol
            user_id: ID del usuario
            tenant_id: ID del tenant (para roles TENANT)
            community_id: ID de la comunidad (para roles COMMUNITY)

        Returns:
            RoleAssignment: Asignación creada
        """
        assignment = RoleAssignment(
            role_id=role_id,
            user_id=user_id,
            tenant_id=tenant_id,
            community_id=community_id
        )
        session.add(assignment)
        await session.flush()
        return assignment

    @staticmethod
    async def remove_role_assignment(
        session: AsyncSession,
        assignment_id: UUID
    ) -> bool:
        """
        Remover una asignación de rol.

        Args:
            session: Sesión de base de datos
            assignment_id: ID de la asignación

        Returns:
            bool: True si se removió, False si no se encontró
        """
        result = await session.execute(
            select(RoleAssignment).where(RoleAssignment.id == assignment_id)
        )
        assignment = result.scalar_one_or_none()
        
        if assignment:
            await session.delete(assignment)
            return True
        return False

    @staticmethod
    async def get_user_role_assignments(
        session: AsyncSession,
        user_id: UUID
    ) -> List[RoleAssignment]:
        """
        Obtener todas las asignaciones de roles de un usuario.

        Args:
            session: Sesión de base de datos
            user_id: ID del usuario

        Returns:
            List[RoleAssignment]: Lista de asignaciones con roles cargados
        """
        result = await session.execute(
            select(RoleAssignment)
            .options(
                selectinload(RoleAssignment.role),
                selectinload(RoleAssignment.tenant),
                selectinload(RoleAssignment.community)
            )
            .where(RoleAssignment.user_id == user_id)
        )
        return list(result.scalars().all())

    @staticmethod
    async def user_has_role_in_tenant(
        session: AsyncSession,
        user_id: UUID,
        role_name: str,
        tenant_id: UUID
    ) -> bool:
        """
        Verificar si un usuario tiene un rol específico en un tenant.

        Args:
            session: Sesión de base de datos
            user_id: ID del usuario
            role_name: Nombre del rol
            tenant_id: ID del tenant

        Returns:
            bool: True si tiene el rol, False si no
        """
        result = await session.execute(
            select(RoleAssignment)
            .join(Role)
            .where(
                and_(
                    RoleAssignment.user_id == user_id,
                    RoleAssignment.tenant_id == tenant_id,
                    Role.name == role_name,
                    Role.scope == RoleScope.TENANT
                )
            )
        )
        return result.scalar_one_or_none() is not None

    @staticmethod
    async def user_has_role_in_community(
        session: AsyncSession,
        user_id: UUID,
        role_name: str,
        community_id: UUID
    ) -> bool:
        """
        Verificar si un usuario tiene un rol específico en una comunidad.

        Args:
            session: Sesión de base de datos
            user_id: ID del usuario
            role_name: Nombre del rol
            community_id: ID de la comunidad

        Returns:
            bool: True si tiene el rol, False si no
        """
        result = await session.execute(
            select(RoleAssignment)
            .join(Role)
            .where(
                and_(
                    RoleAssignment.user_id == user_id,
                    RoleAssignment.community_id == community_id,
                    Role.name == role_name,
                    Role.scope == RoleScope.COMMUNITY
                )
            )
        )
        return result.scalar_one_or_none() is not None

    @staticmethod
    async def user_has_global_role(
        session: AsyncSession,
        user_id: UUID,
        role_name: str
    ) -> bool:
        """
        Verificar si un usuario tiene un rol global.

        Args:
            session: Sesión de base de datos
            user_id: ID del usuario
            role_name: Nombre del rol

        Returns:
            bool: True si tiene el rol, False si no
        """
        result = await session.execute(
            select(RoleAssignment)
            .join(Role)
            .where(
                and_(
                    RoleAssignment.user_id == user_id,
                    RoleAssignment.tenant_id.is_(None),
                    RoleAssignment.community_id.is_(None),
                    Role.name == role_name,
                    Role.scope == RoleScope.GLOBAL
                )
            )
        )
        return result.scalar_one_or_none() is not None

    @staticmethod
    async def get_community_moderators(
        session: AsyncSession,
        community_id: UUID
    ) -> List[User]:
        """
        Obtener todos los moderadores de una comunidad.

        Args:
            session: Sesión de base de datos
            community_id: ID de la comunidad

        Returns:
            List[User]: Lista de usuarios moderadores
        """
        result = await session.execute(
            select(User)
            .join(RoleAssignment, RoleAssignment.user_id == User.id)
            .join(Role, Role.id == RoleAssignment.role_id)
            .where(
                and_(
                    RoleAssignment.community_id == community_id,
                    Role.name == "MODERATOR",
                    Role.scope == RoleScope.COMMUNITY
                )
            )
        )
        return list(result.scalars().all())

    @staticmethod
    async def get_tenant_admins(
        session: AsyncSession,
        tenant_id: UUID
    ) -> List[User]:
        """
        Obtener todos los administradores de un tenant.

        Args:
            session: Sesión de base de datos
            tenant_id: ID del tenant

        Returns:
            List[User]: Lista de usuarios administradores
        """
        result = await session.execute(
            select(User)
            .join(RoleAssignment, RoleAssignment.user_id == User.id)
            .join(Role, Role.id == RoleAssignment.role_id)
            .where(
                and_(
                    RoleAssignment.tenant_id == tenant_id,
                    Role.name == "ADMIN",
                    Role.scope == RoleScope.TENANT
                )
            )
        )
        return list(result.scalars().all())

    @staticmethod
    async def count_community_moderators(
        session: AsyncSession,
        community_id: UUID
    ) -> int:
        """
        Contar el número de moderadores en una comunidad.

        Args:
            session: Sesión de base de datos
            community_id: ID de la comunidad

        Returns:
            int: Número de moderadores
        """
        result = await session.execute(
            select(RoleAssignment)
            .join(Role)
            .where(
                and_(
                    RoleAssignment.community_id == community_id,
                    Role.name == "MODERATOR",
                    Role.scope == RoleScope.COMMUNITY
                )
            )
        )
        return len(list(result.scalars().all()))

    @staticmethod
    async def user_is_admin_of_any_tenant(
        session: AsyncSession,
        user_id: UUID
    ) -> bool:
        """
        Verificar si un usuario es administrador de algún tenant.

        Args:
            session: Sesión de base de datos
            user_id: ID del usuario

        Returns:
            bool: True si es admin de algún tenant, False si no
        """
        result = await session.execute(
            select(RoleAssignment)
            .join(Role)
            .where(
                and_(
                    RoleAssignment.user_id == user_id,
                    RoleAssignment.tenant_id.is_not(None),
                    Role.name == "ADMIN",
                    Role.scope == RoleScope.TENANT
                )
            )
        )
        return result.scalar_one_or_none() is not None

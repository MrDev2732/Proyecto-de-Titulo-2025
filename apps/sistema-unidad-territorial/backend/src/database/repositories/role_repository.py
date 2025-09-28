"""
Repository para el sistema unificado de roles y asignaciones.

Maneja todas las operaciones relacionadas con roles, asignaciones y permisos
usando el nuevo sistema unificado.
"""

from typing import List, Optional
from uuid import UUID

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import (
    Role, 
    SystemRoleAssignment,
    TenantRoleAssignment,
    CommunityRoleAssignment,
    User
)
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
    async def assign_system_role_to_user(
        session: AsyncSession,
        role_id: UUID,
        user_id: UUID
    ) -> SystemRoleAssignment:
        """
        Asignar un rol de sistema a un usuario.

        Args:
            session: Sesión de base de datos
            role_id: ID del rol
            user_id: ID del usuario

        Returns:
            SystemRoleAssignment: Asignación creada o existente

        Raises:
            ValueError: Si la asignación ya existe
        """
        # Verificar si la asignación ya existe
        existing = await session.execute(
            select(SystemRoleAssignment)
            .where(
                SystemRoleAssignment.role_id == role_id,
                SystemRoleAssignment.user_id == user_id,
                SystemRoleAssignment.deleted_at.is_(None)
            )
        )
        existing_assignment = existing.scalar_one_or_none()

        if existing_assignment:
            # La asignación ya existe, retornarla
            return existing_assignment

        # Crear nueva asignación
        assignment = SystemRoleAssignment(
            role_id=role_id,
            user_id=user_id
        )
        session.add(assignment)
        await session.flush()
        return assignment

    @staticmethod
    async def assign_tenant_role_to_user(
        session: AsyncSession,
        role_id: UUID,
        user_id: UUID,
        tenant_id: UUID
    ) -> TenantRoleAssignment:
        """
        Asignar un rol de tenant a un usuario.

        Args:
            session: Sesión de base de datos
            role_id: ID del rol
            user_id: ID del usuario
            tenant_id: ID del tenant

        Returns:
            TenantRoleAssignment: Asignación creada o existente
        """
        # Verificar si la asignación ya existe
        existing = await session.execute(
            select(TenantRoleAssignment)
            .where(
                TenantRoleAssignment.role_id == role_id,
                TenantRoleAssignment.user_id == user_id,
                TenantRoleAssignment.tenant_id == tenant_id,
                TenantRoleAssignment.deleted_at.is_(None)
            )
        )
        existing_assignment = existing.scalar_one_or_none()

        if existing_assignment:
            # La asignación ya existe, retornarla
            return existing_assignment

        # Crear nueva asignación
        assignment = TenantRoleAssignment(
            role_id=role_id,
            user_id=user_id,
            tenant_id=tenant_id
        )
        session.add(assignment)
        await session.flush()
        return assignment

    @staticmethod
    async def assign_community_role_to_user(
        session: AsyncSession,
        role_id: UUID,
        user_id: UUID,
        community_id: UUID
    ) -> CommunityRoleAssignment:
        """
        Asignar un rol de comunidad a un usuario.

        Args:
            session: Sesión de base de datos
            role_id: ID del rol
            user_id: ID del usuario
            community_id: ID de la comunidad

        Returns:
            CommunityRoleAssignment: Asignación creada o existente
        """
        # Verificar si la asignación ya existe
        existing = await session.execute(
            select(CommunityRoleAssignment)
            .where(
                CommunityRoleAssignment.role_id == role_id,
                CommunityRoleAssignment.user_id == user_id,
                CommunityRoleAssignment.community_id == community_id,
                CommunityRoleAssignment.deleted_at.is_(None)
            )
        )
        existing_assignment = existing.scalar_one_or_none()

        if existing_assignment:
            # La asignación ya existe, retornarla
            return existing_assignment

        # Crear nueva asignación
        assignment = CommunityRoleAssignment(
            role_id=role_id,
            user_id=user_id,
            community_id=community_id
        )
        session.add(assignment)
        await session.flush()
        return assignment

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
            select(TenantRoleAssignment)
            .join(Role)
            .where(
                and_(
                    TenantRoleAssignment.user_id == user_id,
                    TenantRoleAssignment.tenant_id == tenant_id,
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
            select(CommunityRoleAssignment)
            .join(Role)
            .where(
                and_(
                    CommunityRoleAssignment.user_id == user_id,
                    CommunityRoleAssignment.community_id == community_id,
                    Role.name == role_name,
                    Role.scope == RoleScope.COMMUNITY
                )
            )
        )
        return result.scalar_one_or_none() is not None

    @staticmethod
    async def user_has_system_role(
        session: AsyncSession,
        user_id: UUID,
        role_name: str
    ) -> bool:
        """
        Verificar si un usuario tiene un rol de sistema.

        Args:
            session: Sesión de base de datos
            user_id: ID del usuario
            role_name: Nombre del rol

        Returns:
            bool: True si tiene el rol, False si no
        """
        result = await session.execute(
            select(SystemRoleAssignment)
            .join(Role)
            .where(
                and_(
                    SystemRoleAssignment.user_id == user_id,
                    Role.name == role_name,
                    Role.scope == RoleScope.SYSTEM
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
            .join(CommunityRoleAssignment, CommunityRoleAssignment.user_id == User.id)
            .join(Role, Role.id == CommunityRoleAssignment.role_id)
            .where(
                and_(
                    CommunityRoleAssignment.community_id == community_id,
                    Role.name == "MODERATOR",
                    Role.scope == RoleScope.COMMUNITY
                )
            )
        )
        return list(result.scalars().all())

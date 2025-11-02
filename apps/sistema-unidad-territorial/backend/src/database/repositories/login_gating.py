"""
Repository for login gating and access control logic.

Handles all database queries related to determining if users
are allowed to access the system based on their membership
status and role assignments.
"""

from typing import List, Dict, Optional
from uuid import UUID as PyUUID

from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.logging import get_logger   
from src.database.models import (
    User,
    UserEmail,
    Role,
    RoleAssignment,
    Community,
    ResidentMembership,
    RegistrationRequest,
    Tenant,
    UserOauthIdentity,
)
from src.database.enums import (
    UserStatus,
    MembershipStatus,
    RoleScope,
    RegistrationStatus,
)


logger = get_logger(__name__)


class LoginGatingRepository:
    """Repository for login access control verification."""

    @staticmethod
    async def can_user_login_by_email(session: AsyncSession, email: str) -> bool:
        """
        Check if a user can login by email.

        Args:
            session: Database session
            email: User email address

        Returns:
            True if user is allowed to login, False otherwise
        """
        # 1. Find user by email (join with user_emails)
        result = await session.execute(
            select(User)
            .join(UserEmail, User.id == UserEmail.user_id)
            .where(UserEmail.email == email.lower())
        )
        user = result.scalar_one_or_none()

        if not user or user.status != UserStatus.ACTIVE:
            return False

        return await LoginGatingRepository._check_user_access(session, user.id)

    @staticmethod
    async def can_user_login_by_oauth(
        session: AsyncSession, 
        provider: str, 
        provider_user_id: str
    ) -> bool:
        """
        Check if a user can login via OAuth.

        Args:
            session: Database session
            provider: OAuth provider
            provider_user_id: User ID from OAuth provider

        Returns:
            True if user is allowed to login, False otherwise
        """
        # 1. Find OAuth identity
        oauth_result = await session.execute(
            select(UserOauthIdentity)
            .options(selectinload(UserOauthIdentity.user))
            .where(
                and_(
                    UserOauthIdentity.provider == provider,
                    UserOauthIdentity.provider_user_id == provider_user_id
                )
            )
        )
        oauth_identity = oauth_result.scalar_one_or_none()

        if not oauth_identity:
            return False

        user = oauth_identity.user
        if user.status != UserStatus.ACTIVE:
            return False

        return await LoginGatingRepository._check_user_access(session, user.id)

    @staticmethod
    async def is_user_allowed_to_login(session: AsyncSession, user_id: PyUUID) -> bool:
        """
        Check if a user is allowed to login by user ID.

        Args:
            session: Database session
            user_id: User UUID

        Returns:
            True if user is allowed to login, False otherwise
        """
        # Verify user exists and is active
        result = await session.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()

        if not user or user.status != UserStatus.ACTIVE:
            return False

        return await LoginGatingRepository._check_user_access(session, user_id)

    @staticmethod
    async def _check_user_access(session: AsyncSession, user_id: PyUUID) -> bool:
        """
        Internal method to check if user has access (global roles, admin role or approved membership).

        Args:
            session: Database session
            user_id: User UUID

        Returns:
            True if user has access, False otherwise
        """
        logger.debug(f"Checking user access for user_id: {user_id}")

        # Check if user has SYSTEM roles (SUPERADMIN, SUPPORT)
        global_assignment = await session.execute(
            select(RoleAssignment)
            .join(Role, RoleAssignment.role_id == Role.id)
            .where(
                and_(
                    RoleAssignment.user_id == user_id,
                    RoleAssignment.scope_type == 'system',
                    Role.scope == RoleScope.SYSTEM
                )
            )
        )

        global_role = global_assignment.first()
        if global_role:
            logger.debug(f"User has GLOBAL access - allowing login")
            return True

        # Check if user is tenant admin
        admin_assignment = await session.execute(
            select(RoleAssignment)
            .join(Role, RoleAssignment.role_id == Role.id)
            .where(
                and_(
                    RoleAssignment.user_id == user_id,
                    RoleAssignment.scope_type == 'tenant',
                    Role.scope == RoleScope.TENANT,
                    Role.name == "ADMIN"
                )
            )
        )

        admin_role = admin_assignment.scalar_one_or_none()
        if admin_role:
            logger.debug(f"User has ADMIN access - allowing login")
            return True

        # Check if user has approved membership in any community
        membership = await session.execute(
            select(ResidentMembership).where(
                and_(
                    ResidentMembership.user_id == user_id,
                    ResidentMembership.status == MembershipStatus.APPROVED
                )
            )
        )

        membership_found = membership.scalar_one_or_none()

        if membership_found:
            logger.debug(f"User has approved membership - allowing login")
            return True
        else:
            logger.debug(f"User access denied")
            return False

    @staticmethod
    async def get_user_communities(session: AsyncSession, user_id: PyUUID) -> List[Dict]:
        """
        Get communities where the user has approved membership.

        Args:
            session: Database session
            user_id: User UUID

        Returns:
            List of community dictionaries
        """
        result = await session.execute(
            select(ResidentMembership, Community)
            .join(Community, ResidentMembership.community_id == Community.id)
            .where(
                and_(
                    ResidentMembership.user_id == user_id,
                    ResidentMembership.status == MembershipStatus.APPROVED
                )
            )
            .order_by(Community.name)
        )

        communities = []
        for membership, community in result:
            communities.append({
                "id": str(community.id),
                "name": community.name,
                "description": community.description,
                "verified": membership.verified,
                "verified_at": membership.verified_at
            })

        return communities

    @staticmethod
    async def get_user_tenant_admin_roles(session: AsyncSession, user_id: PyUUID) -> List[Dict]:
        """
        Get tenant admin roles for the user.

        Args:
            session: Database session
            user_id: User UUID

        Returns:
            List of tenant dictionaries where user has admin role
        """
        result = await session.execute(
            select(RoleAssignment, Role, Tenant)
            .join(Role, RoleAssignment.role_id == Role.id)
            .join(Tenant, RoleAssignment.scope_id == Tenant.id)
            .where(
                and_(
                    RoleAssignment.user_id == user_id,
                    RoleAssignment.scope_type == 'tenant',
                    Role.scope == RoleScope.TENANT
                )
            )
            .order_by(Tenant.name)
        )

        tenants = []
        for assignment, role, tenant in result:
            tenants.append({
                "id": str(tenant.id),
                "name": tenant.name,
                "role_name": role.name,
                "assigned_at": assignment.created_at
            })

        return tenants

    @staticmethod
    async def get_user_community_moderator_roles(session: AsyncSession, user_id: PyUUID) -> List[Dict]:
        """
        Get community moderator roles for the user.

        Args:
            session: Database session
            user_id: User UUID

        Returns:
            List of community dictionaries where user has moderator role
        """
        result = await session.execute(
            select(RoleAssignment, Role, Community)
            .join(Role, RoleAssignment.role_id == Role.id)
            .join(Community, RoleAssignment.scope_id == Community.id)
            .where(
                and_(
                    RoleAssignment.user_id == user_id,
                    RoleAssignment.scope_type == 'community',
                    Role.scope == RoleScope.COMMUNITY
                )
            )
            .order_by(Community.name)
        )

        communities = []
        for assignment, role, community in result:
            communities.append({
                "id": str(community.id),
                "name": community.name,
                "description": community.description,
                "role_name": role.name,
                "assigned_at": assignment.created_at
            })

        return communities

    @staticmethod
    async def get_pending_registration_requests_for_moderator(
        session: AsyncSession, 
        user_id: PyUUID
    ) -> List[Dict]:
        """
        Get pending registration requests for communities where user is a moderator.

        Args:
            session: Database session
            user_id: Moderator user UUID

        Returns:
            List of pending registration requests
        """
        result = await session.execute(
            select(RegistrationRequest, Community)
            .join(Community, RegistrationRequest.community_id == Community.id)
            .join(
                RoleAssignment, 
                and_(
                    RoleAssignment.scope_id == Community.id,
                    RoleAssignment.scope_type == 'community',
                    RoleAssignment.user_id == user_id
                )
            )
            .join(Role, RoleAssignment.role_id == Role.id)
            .where(
                and_(
                    Role.name == "MODERATOR",
                    Role.scope == RoleScope.COMMUNITY,
                    RegistrationRequest.status == RegistrationStatus.PENDING
                )
            )
            .order_by(RegistrationRequest.created_at.desc())
        )

        requests = []
        for request, community in result:
            requests.append({
                "id": str(request.id),
                "email": request.email,
                "full_name": request.full_name,
                "rut": request.rut,
                "address": request.address,
                "provider": request.provider.value,
                "created_at": request.created_at,
                "community_name": community.name,
                "community_id": str(community.id)
            })

        return requests

    @staticmethod
    async def find_default_tenant(session: AsyncSession) -> Optional[Tenant]:
        """
        Get the default tenant for auto registration.

        Args:
            session: Database session

        Returns:
            Default tenant or None
        """
        result = await session.execute(
            select(Tenant).limit(1)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def find_default_community_for_tenant(
        session: AsyncSession, 
        tenant_id: PyUUID
    ) -> Optional[Community]:
        """
        Get the default community for a tenant.

        Args:
            session: Database session
            tenant_id: Tenant UUID

        Returns:
            Default community or None
        """
        result = await session.execute(
            select(Community).where(Community.tenant_id == tenant_id).limit(1)
        )
        return result.scalar_one_or_none()

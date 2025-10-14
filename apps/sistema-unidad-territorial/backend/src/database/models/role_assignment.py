"""
Modelo de asignación de roles polimórfico unificado.

Reemplaza las 3 tablas separadas (SystemRoleAssignment, TenantRoleAssignment, 
CommunityRoleAssignment) por una sola tabla polimórfica.
"""

from typing import Optional
from uuid import UUID as PyUUID

from sqlalchemy import (
    Column,
    ForeignKey,
    String,
    CheckConstraint,
    Index,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, Mapped

from src.database import SCHEMA
from src.database.models.base import SoftDeleteBaseModel


class RoleAssignment(SoftDeleteBaseModel):
    """
    Asignación de roles polimórfica unificada.

    Soporta tres tipos de scope:
    - system: Roles de sistema (admin global, etc.)
    - tenant: Roles de municipalidad (municipal_admin, municipal_user)
    - community: Roles de comunidad (member, moderator, president, etc.)

    COHERENCIA MULTI-TENANT:
    - Para scope='tenant': tenant_id debe coincidir con scope_id
    - Para scope='community': tenant_id debe coincidir con community.tenant_id
    - Para scope='system': tenant_id debe ser NULL
    """

    __tablename__ = 'role_assignments'

    role_id: Mapped[PyUUID] = Column(
        UUID(as_uuid=True), 
        ForeignKey(f'{SCHEMA}.roles.id', ondelete='CASCADE'), 
        nullable=False,
        comment="Role ID"
    )
    user_id: Mapped[PyUUID] = Column(
        UUID(as_uuid=True), 
        ForeignKey(f'{SCHEMA}.users.id', ondelete='CASCADE'), 
        nullable=False,
        comment="User ID"
    )

    # Scope polimórfico
    scope_type: Mapped[str] = Column(
        String(20),
        nullable=False,
        comment="Tipo de scope: system, tenant, community"
    )
    scope_id: Mapped[Optional[PyUUID]] = Column(
        UUID(as_uuid=True),
        nullable=True,
        comment="ID del scope (NULL para system)"
    )

    # Tenant para coherencia multi-tenant
    tenant_id: Mapped[Optional[PyUUID]] = Column(
        UUID(as_uuid=True),
        nullable=True,
        comment="Tenant ID para coherencia (NULL solo para system)"
    )

    # Constraints y schema
    __table_args__ = (
        CheckConstraint(
            "scope_type IN ('system', 'tenant', 'community')",
            name='ck_role_assignment_scope_type'
        ),
        CheckConstraint(
            "(scope_type = 'system' AND scope_id IS NULL AND tenant_id IS NULL) OR "
            "(scope_type IN ('tenant', 'community') AND scope_id IS NOT NULL AND tenant_id IS NOT NULL)",
            name='ck_role_assignment_scope_consistency'
        ),
        # Unicidad por scope
        UniqueConstraint(
            'user_id', 'role_id', 'scope_type', 'scope_id',
            name='uq_role_assignment_unique_per_scope'
        ),
        # Índices para performance
        Index('ix_role_assignment_user', 'user_id'),
        Index('ix_role_assignment_scope', 'scope_type', 'scope_id'),
        Index('ix_role_assignment_tenant', 'tenant_id'),
        Index('ix_role_assignment_role', 'role_id'),
        {'schema': SCHEMA}
    )

    # Relationships
    role: Mapped["Role"] = relationship("Role", foreign_keys=[role_id])
    user: Mapped["User"] = relationship("User", foreign_keys=[user_id])

    # Relationships polimórficos (se resuelven en tiempo de ejecución)
    tenant: Mapped[Optional["Tenant"]] = relationship(
        "Tenant", 
        foreign_keys=[tenant_id],
        viewonly=True
    )
    community: Mapped[Optional["Community"]] = relationship(
        "Community",
        foreign_keys=[scope_id],
        viewonly=True,
        primaryjoin="and_(RoleAssignment.scope_id == Community.id, RoleAssignment.scope_type == 'community')"
    )

    @property
    def is_system_role(self) -> bool:
        """Check if this is a system-level role."""
        return self.scope_type == 'system'

    @property
    def is_tenant_role(self) -> bool:
        """Check if this is a tenant-level role."""
        return self.scope_type == 'tenant'

    @property
    def is_community_role(self) -> bool:
        """Check if this is a community-level role."""
        return self.scope_type == 'community'

    def get_scope_name(self) -> str:
        """Get human-readable scope name."""
        if self.is_system_role:
            return "Sistema"
        elif self.is_tenant_role:
            return f"Municipalidad (ID: {self.scope_id})"
        elif self.is_community_role:
            return f"Comunidad (ID: {self.scope_id})"
        else:
            return "Desconocido"

    def __repr__(self) -> str:
        return (f"RoleAssignment(id={self.id}, user_id={self.user_id}, "
                f"role_id={self.role_id}, scope={self.scope_type}:{self.scope_id})")

"""Add circular foreign keys and missing indexes

Revision ID: 84d203af796a
Revises: 39b6e161dc00
Create Date: 2025-09-28 02:19:52.087000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '84d203af796a'
down_revision: Union[str, Sequence[str], None] = '39b6e161dc00'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add circular foreign keys

    # 1. Add FK from user_emails to users
    op.create_foreign_key(
        'fk_user_emails_user_id', 
        'user_emails', 
        'users',
        ['user_id'], 
        ['id'], 
        ondelete='CASCADE',
        source_schema='sistema_unidad_territorial',
        referent_schema='sistema_unidad_territorial'
    )

    # 2. Add FK from users to user_emails (primary_email_id)
    op.create_foreign_key(
        'fk_users_primary_email_id', 
        'users', 
        'user_emails',
        ['primary_email_id'], 
        ['id'], 
        ondelete='SET NULL',
        source_schema='sistema_unidad_territorial',
        referent_schema='sistema_unidad_territorial'
    )

    # Add missing indexes for user_emails
    op.create_index(
        'idx_user_email_user', 
        'user_emails', 
        ['user_id'],
        schema='sistema_unidad_territorial'
    )
    op.create_index(
        'idx_user_email_verified', 
        'user_emails', 
        ['email', 'verified_at'],
        schema='sistema_unidad_territorial'
    )
    op.create_index(
        'idx_user_email_primary', 
        'user_emails', 
        ['user_id', 'is_primary'],
        schema='sistema_unidad_territorial'
    )

    # Partial unique index to ensure only one primary email per user
    op.execute("""
        CREATE UNIQUE INDEX idx_user_primary_email_unique 
        ON sistema_unidad_territorial.user_emails (user_id) 
        WHERE is_primary = true
    """)

    # Add missing index for users
    op.create_index(
        'idx_user_primary_email', 
        'users', 
        ['primary_email_id'],
        schema='sistema_unidad_territorial'
    )

    # Add missing indexes for user_sessions
    op.create_index(
        'idx_user_session_access_token', 
        'user_sessions', 
        ['access_token_hash'],
        unique=True,
        schema='sistema_unidad_territorial'
    )
    op.create_index(
        'idx_user_session_user_active', 
        'user_sessions', 
        ['user_id', 'is_active'],
        schema='sistema_unidad_territorial'
    )
    op.create_index(
        'idx_user_session_tenant_active', 
        'user_sessions', 
        ['tenant_id', 'is_active'],
        schema='sistema_unidad_territorial'
    )
    op.create_index(
        'idx_user_session_expires', 
        'user_sessions', 
        ['expires_at'],
        schema='sistema_unidad_territorial'
    )
    op.create_index(
        'idx_user_session_ip_created', 
        'user_sessions', 
        ['ip_address', 'created_at'],
        schema='sistema_unidad_territorial'
    )

    # Add missing indexes for authentication_log
    op.create_index(
        'idx_authlog_user_ts', 
        'authentication_log', 
        ['user_id', 'created_at'],
        schema='sistema_unidad_territorial'
    )
    op.create_index(
        'idx_authlog_email_ts', 
        'authentication_log', 
        ['email', 'created_at'],
        schema='sistema_unidad_territorial'
    )
    op.create_index(
        'idx_authlog_ip_ts', 
        'authentication_log', 
        ['ip', 'created_at'],
        schema='sistema_unidad_territorial'
    )
    op.create_index(
        'idx_authlog_tenant_ts', 
        'authentication_log', 
        ['tenant_id', 'created_at'],
        schema='sistema_unidad_territorial'
    )

    # Partial index for failed authentication attempts (critical for rate limiting)
    op.execute("""
        CREATE INDEX idx_authlog_fail_ts 
        ON sistema_unidad_territorial.authentication_log (created_at) 
        WHERE result = 'FAIL'
    """)

    op.create_index(
        'idx_authlog_request', 
        'authentication_log', 
        ['request_id'],
        schema='sistema_unidad_territorial'
    )

    # Add missing indexes for role assignments
    op.create_index(
        'idx_system_roleass_user', 
        'system_role_assignments', 
        ['user_id'],
        schema='sistema_unidad_territorial'
    )
    op.create_index(
        'idx_system_roleass_role', 
        'system_role_assignments', 
        ['role_id'],
        schema='sistema_unidad_territorial'
    )
    
    op.create_index(
        'idx_tenant_roleass_user', 
        'tenant_role_assignments', 
        ['user_id'],
        schema='sistema_unidad_territorial'
    )
    op.create_index(
        'idx_tenant_roleass_tenant', 
        'tenant_role_assignments', 
        ['tenant_id'],
        schema='sistema_unidad_territorial'
    )
    op.create_index(
        'idx_tenant_roleass_role', 
        'tenant_role_assignments', 
        ['role_id'],
        schema='sistema_unidad_territorial'
    )

    op.create_index(
        'idx_community_roleass_user', 
        'community_role_assignments', 
        ['user_id'],
        schema='sistema_unidad_territorial'
    )
    op.create_index(
        'idx_community_roleass_community', 
        'community_role_assignments', 
        ['community_id'],
        schema='sistema_unidad_territorial'
    )
    op.create_index(
        'idx_community_roleass_role', 
        'community_role_assignments', 
        ['role_id'],
        schema='sistema_unidad_territorial'
    )

    # Add missing indexes for oauth identities
    op.create_index(
        'idx_oauth_user', 
        'user_oauth_identities', 
        ['user_id'],
        schema='sistema_unidad_territorial'
    )
    op.create_index(
        'idx_oauth_provider_email', 
        'user_oauth_identities', 
        ['provider', 'provider_email'],
        schema='sistema_unidad_territorial'
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Drop indexes in reverse order
    op.drop_index('idx_oauth_provider_email', 'user_oauth_identities', schema='sistema_unidad_territorial')
    op.drop_index('idx_oauth_user', 'user_oauth_identities', schema='sistema_unidad_territorial')

    op.drop_index('idx_community_roleass_role', 'community_role_assignments', schema='sistema_unidad_territorial')
    op.drop_index('idx_community_roleass_community', 'community_role_assignments', schema='sistema_unidad_territorial')
    op.drop_index('idx_community_roleass_user', 'community_role_assignments', schema='sistema_unidad_territorial')

    op.drop_index('idx_tenant_roleass_role', 'tenant_role_assignments', schema='sistema_unidad_territorial')
    op.drop_index('idx_tenant_roleass_tenant', 'tenant_role_assignments', schema='sistema_unidad_territorial')
    op.drop_index('idx_tenant_roleass_user', 'tenant_role_assignments', schema='sistema_unidad_territorial')
    
    op.drop_index('idx_system_roleass_role', 'system_role_assignments', schema='sistema_unidad_territorial')
    op.drop_index('idx_system_roleass_user', 'system_role_assignments', schema='sistema_unidad_territorial')

    op.drop_index('idx_authlog_request', 'authentication_log', schema='sistema_unidad_territorial')
    op.execute("DROP INDEX IF EXISTS sistema_unidad_territorial.idx_authlog_fail_ts")
    op.drop_index('idx_authlog_tenant_ts', 'authentication_log', schema='sistema_unidad_territorial')
    op.drop_index('idx_authlog_ip_ts', 'authentication_log', schema='sistema_unidad_territorial')
    op.drop_index('idx_authlog_email_ts', 'authentication_log', schema='sistema_unidad_territorial')
    op.drop_index('idx_authlog_user_ts', 'authentication_log', schema='sistema_unidad_territorial')

    op.drop_index('idx_user_session_ip_created', 'user_sessions', schema='sistema_unidad_territorial')
    op.drop_index('idx_user_session_expires', 'user_sessions', schema='sistema_unidad_territorial')
    op.drop_index('idx_user_session_tenant_active', 'user_sessions', schema='sistema_unidad_territorial')
    op.drop_index('idx_user_session_user_active', 'user_sessions', schema='sistema_unidad_territorial')
    op.drop_index('idx_user_session_access_token', 'user_sessions', schema='sistema_unidad_territorial')

    op.drop_index('idx_user_primary_email', 'users', schema='sistema_unidad_territorial')

    op.execute("DROP INDEX IF EXISTS sistema_unidad_territorial.idx_user_primary_email_unique")
    op.drop_index('idx_user_email_primary', 'user_emails', schema='sistema_unidad_territorial')
    op.drop_index('idx_user_email_verified', 'user_emails', schema='sistema_unidad_territorial')
    op.drop_index('idx_user_email_user', 'user_emails', schema='sistema_unidad_territorial')

    # Drop foreign keys
    op.drop_constraint('fk_users_primary_email_id', 'users', schema='sistema_unidad_territorial', type_='foreignkey')
    op.drop_constraint('fk_user_emails_user_id', 'user_emails', schema='sistema_unidad_territorial', type_='foreignkey')

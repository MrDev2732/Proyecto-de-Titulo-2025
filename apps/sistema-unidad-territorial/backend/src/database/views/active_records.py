"""
Views for filtering active (non-soft-deleted) records.

These views provide a clean interface for the application layer,
automatically filtering out soft-deleted records.
"""

from src.database import SCHEMA

# SQL for creating views that filter active records
ACTIVE_VIEWS_SQL = {
    "active_users": f"""
        CREATE OR REPLACE VIEW {SCHEMA}.active_users AS
        SELECT * FROM {SCHEMA}.users 
        WHERE deleted_at IS NULL;
    """,

    "active_tenants": f"""
        CREATE OR REPLACE VIEW {SCHEMA}.active_tenants AS
        SELECT * FROM {SCHEMA}.tenants 
        WHERE deleted_at IS NULL;
    """,

    "active_communities": f"""
        CREATE OR REPLACE VIEW {SCHEMA}.active_communities AS
        SELECT * FROM {SCHEMA}.communities 
        WHERE deleted_at IS NULL;
    """,

    "active_resident_memberships": f"""
        CREATE OR REPLACE VIEW {SCHEMA}.active_resident_memberships AS
        SELECT * FROM {SCHEMA}.resident_memberships 
        WHERE deleted_at IS NULL;
    """,

    "active_system_role_assignments": f"""
        CREATE OR REPLACE VIEW {SCHEMA}.active_system_role_assignments AS
        SELECT * FROM {SCHEMA}.system_role_assignments 
        WHERE deleted_at IS NULL;
    """,

    "active_tenant_role_assignments": f"""
        CREATE OR REPLACE VIEW {SCHEMA}.active_tenant_role_assignments AS
        SELECT * FROM {SCHEMA}.tenant_role_assignments 
        WHERE deleted_at IS NULL;
    """,

    "active_community_role_assignments": f"""
        CREATE OR REPLACE VIEW {SCHEMA}.active_community_role_assignments AS
        SELECT * FROM {SCHEMA}.community_role_assignments 
        WHERE deleted_at IS NULL;
    """,

    # Composite views for common queries
    "active_community_board_members": f"""
        CREATE OR REPLACE VIEW {SCHEMA}.active_community_board_members AS
        SELECT 
            rm.*,
            ue.email,
            u.status as user_status,
            c.name as community_name,
            c.tenant_id
        FROM {SCHEMA}.resident_memberships rm
        JOIN {SCHEMA}.users u ON rm.user_id = u.id
        LEFT JOIN {SCHEMA}.user_emails ue ON u.primary_email_id = ue.id
        JOIN {SCHEMA}.communities c ON rm.community_id = c.id
        WHERE rm.deleted_at IS NULL 
          AND u.deleted_at IS NULL 
          AND c.deleted_at IS NULL
          AND rm.board_role IS NOT NULL
          AND rm.status = 'APPROVED';
    """,

    "active_user_memberships": f"""
        CREATE OR REPLACE VIEW {SCHEMA}.active_user_memberships AS
        SELECT 
            rm.*,
            c.name as community_name,
            c.tenant_id,
            t.name as tenant_name
        FROM {SCHEMA}.resident_memberships rm
        JOIN {SCHEMA}.communities c ON rm.community_id = c.id
        JOIN {SCHEMA}.tenants t ON c.tenant_id = t.id
        WHERE rm.deleted_at IS NULL 
          AND c.deleted_at IS NULL 
          AND t.deleted_at IS NULL
          AND rm.status = 'APPROVED';
    """
}

# SQL for dropping views (useful for migrations)
DROP_ACTIVE_VIEWS_SQL = [
    f"DROP VIEW IF EXISTS {SCHEMA}.active_users CASCADE;",
    f"DROP VIEW IF EXISTS {SCHEMA}.active_tenants CASCADE;",
    f"DROP VIEW IF EXISTS {SCHEMA}.active_communities CASCADE;",
    f"DROP VIEW IF EXISTS {SCHEMA}.active_resident_memberships CASCADE;",
    f"DROP VIEW IF EXISTS {SCHEMA}.active_system_role_assignments CASCADE;",
    f"DROP VIEW IF EXISTS {SCHEMA}.active_tenant_role_assignments CASCADE;",
    f"DROP VIEW IF EXISTS {SCHEMA}.active_community_role_assignments CASCADE;",
    f"DROP VIEW IF EXISTS {SCHEMA}.active_community_board_members CASCADE;",
    f"DROP VIEW IF EXISTS {SCHEMA}.active_user_memberships CASCADE;",
]

# Example usage in repositories:
"""
# Instead of:
users = session.query(User).filter(User.deleted_at.is_(None)).all()

# Use:
users = session.execute(text("SELECT * FROM active_users")).fetchall()

# Or create SQLAlchemy models for the views:
class ActiveUser(Base):
    __table__ = Table('active_users', Base.metadata, autoload_with=engine)
"""

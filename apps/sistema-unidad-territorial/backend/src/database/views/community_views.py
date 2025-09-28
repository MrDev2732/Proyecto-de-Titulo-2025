"""
Community management and access control views.

These views handle community membership, role assignments,
and login access control logic.
"""

from src.database import SCHEMA

# Community and access control views
COMMUNITY_VIEWS_SQL = {
    "user_is_allowed_to_login": f"""
        CREATE OR REPLACE VIEW {SCHEMA}.v_user_is_allowed_to_login AS
        SELECT
          u.id AS user_id,
          CASE
            WHEN u.status <> 'ACTIVE' THEN FALSE
            WHEN EXISTS (
              SELECT 1 FROM {SCHEMA}.tenant_role_assignments tra
              JOIN {SCHEMA}.roles r ON r.id = tra.role_id
              WHERE tra.user_id = u.id AND r.scope = 'TENANT' AND r.name = 'ADMIN'
            ) THEN TRUE
            WHEN EXISTS (
              SELECT 1 FROM {SCHEMA}.resident_memberships rm
              WHERE rm.user_id = u.id AND rm.status = 'APPROVED'
            ) THEN TRUE
            ELSE FALSE
          END AS allowed
        FROM {SCHEMA}.users u;
    """,

    "community_moderators": f"""
        CREATE OR REPLACE VIEW {SCHEMA}.v_community_moderators AS
        SELECT 
            c.id as community_id,
            c.name as community_name,
            c.tenant_id,
            u.id as user_id,
            ue.email as user_email,
            cra.created_at as assigned_at
        FROM {SCHEMA}.communities c
        JOIN {SCHEMA}.community_role_assignments cra ON c.id = cra.community_id
        JOIN {SCHEMA}.roles r ON cra.role_id = r.id
        JOIN {SCHEMA}.users u ON cra.user_id = u.id
        LEFT JOIN {SCHEMA}.user_emails ue ON u.primary_email_id = ue.id
        WHERE r.name = 'MODERATOR' 
          AND r.scope = 'COMMUNITY'
          AND cra.deleted_at IS NULL
          AND c.deleted_at IS NULL
          AND u.deleted_at IS NULL
        ORDER BY c.name, ue.email;
    """,

    "community_member_count": f"""
        CREATE OR REPLACE VIEW {SCHEMA}.v_community_member_count AS
        SELECT 
            c.id as community_id,
            c.name as community_name,
            c.tenant_id,
            COUNT(rm.id) as total_members,
            COUNT(CASE WHEN rm.status = 'APPROVED' THEN 1 END) as approved_members,
            COUNT(CASE WHEN rm.status = 'PENDING' THEN 1 END) as pending_members,
            COUNT(CASE WHEN rm.board_role IS NOT NULL THEN 1 END) as board_members
        FROM {SCHEMA}.communities c
        LEFT JOIN {SCHEMA}.resident_memberships rm ON c.id = rm.community_id 
            AND rm.deleted_at IS NULL
        WHERE c.deleted_at IS NULL
        GROUP BY c.id, c.name, c.tenant_id
        ORDER BY c.name;
    """,

    "user_community_roles": f"""
        CREATE OR REPLACE VIEW {SCHEMA}.v_user_community_roles AS
        SELECT 
            u.id as user_id,
            ue.email,
            c.id as community_id,
            c.name as community_name,
            c.tenant_id,
            r.name as role_name,
            r.scope as role_scope,
            rm.board_role,
            rm.status as membership_status,
            cra.created_at as role_assigned_at,
            rm.created_at as membership_created_at
        FROM {SCHEMA}.users u
        LEFT JOIN {SCHEMA}.user_emails ue ON u.primary_email_id = ue.id
        LEFT JOIN {SCHEMA}.resident_memberships rm ON u.id = rm.user_id AND rm.deleted_at IS NULL
        LEFT JOIN {SCHEMA}.communities c ON rm.community_id = c.id AND c.deleted_at IS NULL
        LEFT JOIN {SCHEMA}.community_role_assignments cra ON u.id = cra.user_id 
            AND c.id = cra.community_id AND cra.deleted_at IS NULL
        LEFT JOIN {SCHEMA}.roles r ON cra.role_id = r.id
        WHERE u.deleted_at IS NULL
        ORDER BY ue.email, c.name, r.name;
    """,

    "tenant_admin_users": f"""
        CREATE OR REPLACE VIEW {SCHEMA}.v_tenant_admin_users AS
        SELECT 
            t.id as tenant_id,
            t.name as tenant_name,
            u.id as user_id,
            ue.email as user_email,
            u.status as user_status,
            tra.created_at as admin_assigned_at
        FROM {SCHEMA}.tenants t
        JOIN {SCHEMA}.tenant_role_assignments tra ON t.id = tra.tenant_id
        JOIN {SCHEMA}.roles r ON tra.role_id = r.id
        JOIN {SCHEMA}.users u ON tra.user_id = u.id
        LEFT JOIN {SCHEMA}.user_emails ue ON u.primary_email_id = ue.id
        WHERE r.name = 'ADMIN' 
          AND r.scope = 'TENANT'
          AND tra.deleted_at IS NULL
          AND t.deleted_at IS NULL
          AND u.deleted_at IS NULL
        ORDER BY t.name, ue.email;
    """
}

# SQL for dropping community views
DROP_COMMUNITY_VIEWS_SQL = [
    f"DROP VIEW IF EXISTS {SCHEMA}.v_user_is_allowed_to_login CASCADE;",
    f"DROP VIEW IF EXISTS {SCHEMA}.v_community_moderators CASCADE;",
    f"DROP VIEW IF EXISTS {SCHEMA}.v_community_member_count CASCADE;",
    f"DROP VIEW IF EXISTS {SCHEMA}.v_user_community_roles CASCADE;",
    f"DROP VIEW IF EXISTS {SCHEMA}.v_tenant_admin_users CASCADE;",
]

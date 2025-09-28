"""
Authentication and security related views.

These views provide insights into authentication patterns,
security events, and user behavior analysis.
"""

from src.database import SCHEMA

# Authentication and security views
AUTH_VIEWS_SQL = {
    "auth_failures_24h": f"""
        CREATE OR REPLACE VIEW {SCHEMA}.v_auth_failures_24h AS
        SELECT 
            tenant_id, 
            email, 
            ip, 
            provider, 
            method, 
            failure_reason, 
            error_code,
            risk_score,
            geo_country,
            user_agent,
            created_at
        FROM {SCHEMA}.authentication_log
        WHERE result = 'FAIL' 
          AND created_at >= now() - INTERVAL '24 hours'
        ORDER BY created_at DESC;
    """,

    "auth_rate_limit_analysis": f"""
        CREATE OR REPLACE VIEW {SCHEMA}.v_auth_rate_limit_analysis AS
        SELECT 
            ip,
            COUNT(*) as total_attempts,
            SUM(CASE WHEN result = 'FAIL' THEN 1 ELSE 0 END) as failed_attempts,
            SUM(CASE WHEN result = 'SUCCESS' THEN 1 ELSE 0 END) as success_attempts,
            ROUND(
                SUM(CASE WHEN result = 'FAIL' THEN 1 ELSE 0 END)::numeric / COUNT(*)::numeric * 100, 
                2
            ) as failure_rate_percent,
            MIN(created_at) as first_attempt,
            MAX(created_at) as last_attempt,
            COUNT(DISTINCT email) as unique_emails,
            COUNT(DISTINCT user_id) as unique_users,
            array_agg(DISTINCT geo_country) FILTER (WHERE geo_country IS NOT NULL) as countries,
            AVG(risk_score) FILTER (WHERE risk_score IS NOT NULL) as avg_risk_score
        FROM {SCHEMA}.authentication_log
        WHERE created_at >= now() - INTERVAL '24 hours'
        GROUP BY ip
        HAVING COUNT(*) >= 5  -- Solo IPs con al menos 5 intentos
        ORDER BY failed_attempts DESC, total_attempts DESC;
    """,

    "suspicious_auth_users": f"""
        CREATE OR REPLACE VIEW {SCHEMA}.v_suspicious_auth_users AS
        SELECT 
            u.id as user_id,
            ue.email,
            u.status,
            COUNT(al.id) as total_auth_attempts,
            SUM(CASE WHEN al.result = 'FAIL' THEN 1 ELSE 0 END) as failed_attempts,
            COUNT(DISTINCT al.ip) as unique_ips,
            COUNT(DISTINCT al.geo_country) as unique_countries,
            AVG(al.risk_score) FILTER (WHERE al.risk_score IS NOT NULL) as avg_risk_score,
            MAX(al.created_at) as last_attempt,
            array_agg(DISTINCT al.failure_reason) 
                FILTER (WHERE al.failure_reason IS NOT NULL) as failure_reasons
        FROM {SCHEMA}.users u
        LEFT JOIN {SCHEMA}.user_emails ue ON u.primary_email_id = ue.id
        JOIN {SCHEMA}.authentication_log al ON u.id = al.user_id
        WHERE al.created_at >= now() - INTERVAL '7 days'
        GROUP BY u.id, ue.email, u.status
        HAVING 
            SUM(CASE WHEN al.result = 'FAIL' THEN 1 ELSE 0 END) >= 10  -- 10+ fallos
            OR COUNT(DISTINCT al.ip) >= 5  -- 5+ IPs diferentes
            OR COUNT(DISTINCT al.geo_country) >= 3  -- 3+ países diferentes
        ORDER BY failed_attempts DESC, unique_ips DESC;
    """,

    "user_login_summary": f"""
        CREATE OR REPLACE VIEW {SCHEMA}.v_user_login_summary AS
        SELECT 
            u.id as user_id,
            ue.email,
            u.status,
            COUNT(al.id) as total_login_attempts,
            SUM(CASE WHEN al.result = 'SUCCESS' THEN 1 ELSE 0 END) as successful_logins,
            SUM(CASE WHEN al.result = 'FAIL' THEN 1 ELSE 0 END) as failed_logins,
            MAX(CASE WHEN al.result = 'SUCCESS' THEN al.created_at END) as last_successful_login,
            MAX(CASE WHEN al.result = 'FAIL' THEN al.created_at END) as last_failed_login,
            COUNT(DISTINCT al.ip) as unique_ips_used,
            array_agg(DISTINCT al.provider) as auth_providers_used
        FROM {SCHEMA}.users u
        LEFT JOIN {SCHEMA}.user_emails ue ON u.primary_email_id = ue.id
        LEFT JOIN {SCHEMA}.authentication_log al ON u.id = al.user_id
        WHERE al.created_at >= now() - INTERVAL '30 days' OR al.id IS NULL
        GROUP BY u.id, ue.email, u.status
        ORDER BY last_successful_login DESC NULLS LAST;
    """
}

# SQL for dropping auth views
DROP_AUTH_VIEWS_SQL = [
    f"DROP VIEW IF EXISTS {SCHEMA}.v_auth_failures_24h CASCADE;",
    f"DROP VIEW IF EXISTS {SCHEMA}.v_auth_rate_limit_analysis CASCADE;",
    f"DROP VIEW IF EXISTS {SCHEMA}.v_suspicious_auth_users CASCADE;",
    f"DROP VIEW IF EXISTS {SCHEMA}.v_user_login_summary CASCADE;",
]

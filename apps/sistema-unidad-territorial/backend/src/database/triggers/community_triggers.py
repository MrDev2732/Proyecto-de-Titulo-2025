"""
Database triggers for community-related business rules.
"""

from sqlalchemy import text
from src.database import SCHEMA

# Trigger function to limit moderators per community (max 3) - Updated for new role assignment tables
LIMIT_MODERATORS_FUNCTION = text(f"""
CREATE OR REPLACE FUNCTION {SCHEMA}.trg_limit_moderators()
RETURNS trigger AS $$
DECLARE cnt INT;
BEGIN
  IF (SELECT name FROM {SCHEMA}.roles WHERE id = NEW.role_id) = 'MODERATOR'
     AND (SELECT scope FROM {SCHEMA}.roles WHERE id = NEW.role_id) = 'COMMUNITY' THEN
    SELECT COUNT(*) INTO cnt
    FROM {SCHEMA}.community_role_assignments cra
    WHERE cra.community_id = NEW.community_id
      AND cra.role_id IN (SELECT id FROM {SCHEMA}.roles WHERE name='MODERATOR' AND scope='COMMUNITY');
    IF cnt >= 3 THEN
      RAISE EXCEPTION 'Community % already has the maximum of 3 moderators', NEW.community_id;
    END IF;
  END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;
""")

# Drop trigger if exists and create new one
DROP_LIMIT_MODERATORS_TRIGGER = text(f"""
DROP TRIGGER IF EXISTS limit_moderators ON {SCHEMA}.community_role_assignments;
""")

CREATE_LIMIT_MODERATORS_TRIGGER = text(f"""
CREATE TRIGGER limit_moderators
BEFORE INSERT ON {SCHEMA}.community_role_assignments
FOR EACH ROW EXECUTE FUNCTION {SCHEMA}.trg_limit_moderators();
""")

# Login gating view - now managed in src.database.views.community_views
# This is kept for backward compatibility but should use the centralized views module
LOGIN_GATING_VIEW = text(f"""
-- This view is now managed in src.database.views.community_views
-- Use: from src.database.views.community_views import COMMUNITY_VIEWS_SQL
-- Then: COMMUNITY_VIEWS_SQL["user_is_allowed_to_login"]
SELECT 1; -- Placeholder to avoid empty statement
""")

# Function to check if user can login by email (updated for new User/UserEmail model)
CAN_USER_LOGIN_FUNCTION = text(f"""
CREATE OR REPLACE FUNCTION {SCHEMA}.can_user_login(p_email CITEXT)
RETURNS BOOLEAN AS $$
DECLARE uid UUID; ok BOOLEAN;
BEGIN
  SELECT u.id INTO uid 
  FROM {SCHEMA}.users u
  JOIN {SCHEMA}.user_emails ue ON u.id = ue.user_id
  WHERE ue.email = p_email;
  IF uid IS NULL THEN RETURN FALSE; END IF;
  SELECT allowed INTO ok FROM {SCHEMA}.v_user_is_allowed_to_login WHERE user_id = uid;
  RETURN COALESCE(ok, FALSE);
END;
$$ LANGUAGE plpgsql STABLE;
""")

# Function to check if user can login via OAuth (updated for unified system)
CAN_OAUTH_LOGIN_FUNCTION = text(f"""
CREATE OR REPLACE FUNCTION {SCHEMA}.can_oauth_login(p_provider TEXT, p_provider_user_id TEXT)
RETURNS BOOLEAN AS $$
DECLARE uid UUID; ok BOOLEAN;
BEGIN
  SELECT u.id
  INTO uid
  FROM {SCHEMA}.user_oauth_identities oi
  JOIN {SCHEMA}.users u ON u.id = oi.user_id
  WHERE oi.provider = p_provider AND oi.provider_user_id = p_provider_user_id;
  IF uid IS NULL THEN RETURN FALSE; END IF;
  SELECT allowed INTO ok FROM {SCHEMA}.v_user_is_allowed_to_login WHERE user_id = uid;
  RETURN COALESCE(ok, FALSE);
END;
$$ LANGUAGE plpgsql STABLE;
""")

# Drop statements for cleanup
DROP_LOGIN_FUNCTIONS = text(f"""
DROP FUNCTION IF EXISTS {SCHEMA}.can_oauth_login;
DROP FUNCTION IF EXISTS {SCHEMA}.can_user_login;
DROP VIEW IF EXISTS {SCHEMA}.v_user_is_allowed_to_login;
""")

DROP_MODERATOR_TRIGGER_FUNCTION = text(f"""
DROP TRIGGER IF EXISTS limit_moderators ON {SCHEMA}.community_role_assignments;
DROP FUNCTION IF EXISTS {SCHEMA}.trg_limit_moderators;
""")

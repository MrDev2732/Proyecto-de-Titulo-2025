"""
Database triggers for community-related business rules.
"""

from sqlalchemy import text
from src.database import SCHEMA

# Trigger function to limit moderators per community (max 3) - New unified version
LIMIT_MODERATORS_FUNCTION = text(f"""
CREATE OR REPLACE FUNCTION {SCHEMA}.trg_limit_moderators()
RETURNS trigger AS $$
DECLARE cnt INT;
BEGIN
  IF (SELECT name FROM {SCHEMA}.roles WHERE id = NEW.role_id) = 'MODERATOR'
     AND (SELECT scope FROM {SCHEMA}.roles WHERE id = NEW.role_id) = 'COMMUNITY' THEN
    SELECT COUNT(*) INTO cnt
    FROM {SCHEMA}.role_assignments ra
    WHERE ra.community_id = NEW.community_id
      AND ra.role_id IN (SELECT id FROM {SCHEMA}.roles WHERE name='MODERATOR' AND scope='COMMUNITY');
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
DROP TRIGGER IF EXISTS limit_moderators ON {SCHEMA}.role_assignments;
""")

CREATE_LIMIT_MODERATORS_TRIGGER = text(f"""
CREATE TRIGGER limit_moderators
BEFORE INSERT ON {SCHEMA}.role_assignments
FOR EACH ROW EXECUTE FUNCTION {SCHEMA}.trg_limit_moderators();
""")

# Login gating view - checks if user is allowed to log in (updated for unified system)
LOGIN_GATING_VIEW = text(f"""
CREATE OR REPLACE VIEW {SCHEMA}.v_user_is_allowed_to_login AS
SELECT
  u.id AS user_id,
  CASE
    WHEN u.status <> 'ACTIVE' THEN FALSE
    WHEN EXISTS (
      SELECT 1 FROM {SCHEMA}.role_assignments ra
      JOIN {SCHEMA}.roles r ON r.id = ra.role_id
      WHERE ra.user_id = u.id AND r.scope = 'TENANT' AND r.name = 'ADMIN'
    ) THEN TRUE
    WHEN EXISTS (
      SELECT 1 FROM {SCHEMA}.resident_memberships rm
      WHERE rm.user_id = u.id AND rm.status = 'APPROVED'
    ) THEN TRUE
    ELSE FALSE
  END AS allowed
FROM {SCHEMA}.users u;
""")

# Function to check if user can login by email (updated for unified system)
CAN_USER_LOGIN_FUNCTION = text(f"""
CREATE OR REPLACE FUNCTION {SCHEMA}.can_user_login(p_email CITEXT)
RETURNS BOOLEAN AS $$
DECLARE uid UUID; ok BOOLEAN;
BEGIN
  SELECT id INTO uid FROM {SCHEMA}.users WHERE email = p_email;
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
DROP TRIGGER IF EXISTS limit_moderators ON {SCHEMA}.role_assignments;
DROP FUNCTION IF EXISTS {SCHEMA}.trg_limit_moderators;
""")

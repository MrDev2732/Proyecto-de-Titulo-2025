"""
Triggers para validar la consistencia de role assignments con role scopes.
Esto reemplaza las CHECK constraints que no pueden usar subqueries en PostgreSQL.
"""

from src.database import SCHEMA

# Función trigger para validar role scope assignments
ROLE_ASSIGNMENT_SCOPE_VALIDATION_FUNCTION = f"""
CREATE OR REPLACE FUNCTION {SCHEMA}.validate_role_assignment_scope()
RETURNS TRIGGER AS $$
DECLARE
    role_scope TEXT;
BEGIN
    -- Obtener el scope del rol
    SELECT scope INTO role_scope 
    FROM {SCHEMA}.roles 
    WHERE id = NEW.role_id;

    -- Si no se encuentra el rol, permitir que falle en el FK constraint
    IF role_scope IS NULL THEN
        RETURN NEW;
    END IF;

    -- Validaciones según el scope del rol
    CASE role_scope
        WHEN 'GLOBAL' THEN
            -- GLOBAL: no debe tener tenant_id ni community_id
            IF NEW.tenant_id IS NOT NULL OR NEW.community_id IS NOT NULL THEN
                RAISE EXCEPTION 'GLOBAL scope roles cannot have tenant_id or community_id context'
                    USING ERRCODE = 'check_violation';
            END IF;

        WHEN 'TENANT' THEN
            -- TENANT: debe tener tenant_id pero no community_id
            IF NEW.tenant_id IS NULL OR NEW.community_id IS NOT NULL THEN
                RAISE EXCEPTION 'TENANT scope roles require tenant_id and cannot have community_id'
                    USING ERRCODE = 'check_violation';
            END IF;

        WHEN 'COMMUNITY' THEN
            -- COMMUNITY: debe tener community_id (tenant_id es opcional)
            IF NEW.community_id IS NULL THEN
                RAISE EXCEPTION 'COMMUNITY scope roles require community_id'
                    USING ERRCODE = 'check_violation';
            END IF;

        ELSE
            RAISE EXCEPTION 'Unknown role scope: %', role_scope
                USING ERRCODE = 'check_violation';
    END CASE;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
"""

# Trigger que ejecuta la validación
ROLE_ASSIGNMENT_SCOPE_VALIDATION_TRIGGER = f"""
DROP TRIGGER IF EXISTS trg_validate_role_assignment_scope ON {SCHEMA}.role_assignments;

CREATE TRIGGER trg_validate_role_assignment_scope
    BEFORE INSERT OR UPDATE ON {SCHEMA}.role_assignments
    FOR EACH ROW
    EXECUTE FUNCTION {SCHEMA}.validate_role_assignment_scope();
"""

# Función para cleanup del trigger (para rollback)
DROP_ROLE_ASSIGNMENT_SCOPE_VALIDATION = f"""
DROP TRIGGER IF EXISTS trg_validate_role_assignment_scope ON {SCHEMA}.role_assignments;
DROP FUNCTION IF EXISTS {SCHEMA}.validate_role_assignment_scope();
"""

__all__ = [
    "ROLE_ASSIGNMENT_SCOPE_VALIDATION_FUNCTION",
    "ROLE_ASSIGNMENT_SCOPE_VALIDATION_TRIGGER", 
    "DROP_ROLE_ASSIGNMENT_SCOPE_VALIDATION"
]

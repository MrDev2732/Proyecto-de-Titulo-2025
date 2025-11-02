"""
Triggers para validar la consistencia de role assignments con role scopes.
Esto reemplaza las CHECK constraints que no pueden usar subqueries en PostgreSQL.
"""

from src.database import SCHEMA

# Función trigger para validar role scope assignments con la nueva estructura polimórfica
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

    -- Validaciones según el scope del rol usando la nueva estructura polimórfica
    CASE role_scope
        WHEN 'SYSTEM' THEN
            -- SYSTEM: scope_type debe ser 'system', scope_id y tenant_id deben ser NULL
            IF NEW.scope_type != 'system' OR NEW.scope_id IS NOT NULL OR NEW.tenant_id IS NOT NULL THEN
                RAISE EXCEPTION 'SYSTEM scope roles must have scope_type=system, scope_id=NULL, tenant_id=NULL'
                    USING ERRCODE = 'check_violation';
            END IF;

        WHEN 'TENANT' THEN
            -- TENANT: scope_type debe ser 'tenant', scope_id debe coincidir con tenant_id
            IF NEW.scope_type != 'tenant' OR NEW.scope_id IS NULL OR NEW.tenant_id IS NULL OR NEW.scope_id != NEW.tenant_id THEN
                RAISE EXCEPTION 'TENANT scope roles must have scope_type=tenant, scope_id=tenant_id'
                    USING ERRCODE = 'check_violation';
            END IF;

        WHEN 'COMMUNITY' THEN
            -- COMMUNITY: scope_type debe ser 'community', scope_id debe ser community_id, tenant_id requerido
            IF NEW.scope_type != 'community' OR NEW.scope_id IS NULL OR NEW.tenant_id IS NULL THEN
                RAISE EXCEPTION 'COMMUNITY scope roles must have scope_type=community, scope_id=community_id, tenant_id required'
                    USING ERRCODE = 'check_violation';
            END IF;
            
            -- Verificar que la comunidad pertenece al tenant especificado
            IF NOT EXISTS (
                SELECT 1 FROM {SCHEMA}.communities 
                WHERE id = NEW.scope_id AND tenant_id = NEW.tenant_id
            ) THEN
                RAISE EXCEPTION 'Community % does not belong to tenant %', NEW.scope_id, NEW.tenant_id
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

# Trigger que ejecuta la validación - ACTUALIZADO para la nueva estructura polimórfica
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

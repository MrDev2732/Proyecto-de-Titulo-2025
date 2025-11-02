"""
Triggers y vistas SQL para el sistema de autenticación
Integración de triggers para alertas automáticas y análisis de seguridad.
"""

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.logging import get_logger
from src.database.views.auth_views import AUTH_VIEWS_SQL


logger = get_logger(__name__)


class AuthenticationTriggers:
    """Clase para gestionar triggers del sistema de autenticación."""

    @staticmethod
    async def create_auth_log_views(session: AsyncSession) -> None:
        """
        Crear vistas operativas para authentication_log.

        Note: Views are now managed centrally in src.database.views module.
        This method is kept for backward compatibility but delegates to the views module.

        Args:
            session: Sesión de base de datos
        """
        try:
            # Create auth-related views
            for view_name, sql in AUTH_VIEWS_SQL.items():
                await session.execute(text(sql))
                logger.info(f"✅ Created auth view: {view_name}")

            logger.info("Vistas de authentication_log creadas exitosamente")

        except Exception as e:
            logger.error(f"Error creando vistas de authentication_log: {e}", exc_info=True)
            raise

    @staticmethod
    async def create_auth_alert_function(session: AsyncSession) -> None:
        """
        Crear función para alertas automáticas de seguridad.

        Args:
            session: Sesión de base de datos
        """
        try:
            function_auth_alerts = text("""
                CREATE OR REPLACE FUNCTION trg_authlog_alerts()
                RETURNS trigger AS $$
                DECLARE
                    alert_email TEXT;
                    alert_subject TEXT;
                    alert_body TEXT;
                    user_email TEXT;
                BEGIN
                    -- Solo procesar fallos con alto riesgo
                    IF NEW.result != 'FAIL' OR COALESCE(NEW.risk_score, 0) < 80 THEN
                        RETURN NEW;
                    END IF;

                    -- Determinar el email del usuario para la alerta
                    IF NEW.user_id IS NOT NULL THEN
                        SELECT email INTO user_email 
                        FROM sistema_unidad_territorial.users 
                        WHERE id = NEW.user_id;
                        
                        alert_email := COALESCE(user_email, NEW.email, 'soporte@unidadterritorial.cl');
                    ELSE
                        alert_email := COALESCE(NEW.email, 'soporte@unidadterritorial.cl');
                    END IF;

                    -- Construir mensaje de alerta
                    alert_subject := 'Alerta de Seguridad - Intento de acceso sospechoso';
                    alert_body := format(
                        'Se detectó un intento fallido de acceso con riesgo alto:

                Email: %s
                IP: %s
                País: %s
                Proveedor: %s
                Método: %s
                Razón del fallo: %s
                Puntuación de riesgo: %s
                Fecha: %s

                Si no reconoce este intento, contacte al soporte inmediatamente.',
                        COALESCE(NEW.email, 'No especificado'),
                        COALESCE(host(NEW.ip), 'No especificado'),
                        COALESCE(NEW.geo_country, 'No especificado'),
                        NEW.provider,
                        NEW.method,
                        COALESCE(NEW.failure_reason::text, 'No especificado'),
                        COALESCE(NEW.risk_score::text, 'No especificado'),
                        NEW.created_at::text
                    );

                    -- Insertar en outbox para envío de email
                    INSERT INTO sistema_unidad_territorial.outbox(type, payload, next_attempt_at)
                    VALUES (
                        'email',
                        jsonb_build_object(
                            'to', alert_email,
                            'subject', alert_subject,
                            'body', alert_body,
                            'priority', 'high',
                            'auth_log_id', NEW.id::text,
                            'risk_score', NEW.risk_score
                        ),
                        now()
                    );

                    -- También crear alerta interna para administradores
                    INSERT INTO sistema_unidad_territorial.outbox(type, payload, next_attempt_at)
                    VALUES (
                        'admin_alert',
                        jsonb_build_object(
                            'type', 'high_risk_auth_failure',
                            'user_email', alert_email,
                            'ip', host(NEW.ip),
                            'country', NEW.geo_country,
                            'risk_score', NEW.risk_score,
                            'failure_reason', NEW.failure_reason,
                            'auth_log_id', NEW.id::text,
                            'timestamp', NEW.created_at
                        ),
                        now()
                    );

                    RETURN NEW;
                END;
                $$ LANGUAGE plpgsql;
            """)

            await session.execute(function_auth_alerts)
            logger.info("Función de alertas de autenticación creada exitosamente")

        except Exception as e:
            logger.error(f"Error creando función de alertas: {e}", exc_info=True)
            raise

    @staticmethod
    async def create_geo_change_function(session: AsyncSession) -> None:
        """
        Crear función para detectar cambios geográficos sospechosos.

        Args:
            session: Sesión de base de datos
        """
        try:
            function_geo_change = text("""
                CREATE OR REPLACE FUNCTION trg_authlog_geo_change()
                RETURNS trigger AS $$
                DECLARE
                    last_success_country TEXT;
                    hours_since_last_success INTEGER;
                BEGIN
                    -- Solo procesar éxitos con geolocalización
                    IF NEW.result != 'SUCCESS' OR NEW.geo_country IS NULL OR NEW.user_id IS NULL THEN
                        RETURN NEW;
                    END IF;

                    -- Buscar el último login exitoso del usuario
                    SELECT 
                        geo_country,
                        EXTRACT(EPOCH FROM (NEW.created_at - created_at)) / 3600
                    INTO 
                        last_success_country,
                        hours_since_last_success
                    FROM sistema_unidad_territorial.authentication_log
                    WHERE user_id = NEW.user_id 
                      AND result = 'SUCCESS'
                      AND geo_country IS NOT NULL
                      AND id != NEW.id
                    ORDER BY created_at DESC
                    LIMIT 1;

                    -- Si hay un cambio de país en menos de 4 horas, alertar
                    IF last_success_country IS NOT NULL 
                       AND last_success_country != NEW.geo_country 
                       AND hours_since_last_success < 4 THEN

                        INSERT INTO sistema_unidad_territorial.outbox(type, payload, next_attempt_at)
                        VALUES (
                            'email',
                            jsonb_build_object(
                                'to', NEW.email,
                                'subject', 'Acceso desde nueva ubicación detectado',
                                'body', format(
                                    'Detectamos un acceso exitoso a tu cuenta desde una nueva ubicación:

                    Ubicación anterior: %s
                    Nueva ubicación: %s
                    Tiempo transcurrido: %s horas
                    IP: %s
                    Fecha: %s

                    Si fuiste tú, ignora este mensaje. Si no, contacta al soporte inmediatamente.',
                                    last_success_country,
                                    NEW.geo_country,
                                    hours_since_last_success::text,
                                    COALESCE(host(NEW.ip), 'No especificado'),
                                    NEW.created_at::text
                                ),
                                'priority', 'medium',
                                'auth_log_id', NEW.id::text,
                                'geo_change', true
                            ),
                            now()
                        );
                    END IF;

                    RETURN NEW;
                END;
                $$ LANGUAGE plpgsql;
            """)

            await session.execute(function_geo_change)
            logger.info("Función de detección geográfica creada exitosamente")

        except Exception as e:
            logger.error(f"Error creando función de detección geográfica: {e}", exc_info=True)
            raise

    @staticmethod
    async def create_cleanup_function(session: AsyncSession) -> None:
        """
        Crear función de limpieza para logs antiguos.

        Args:
            session: Sesión de base de datos
        """
        try:
            function_cleanup = text("""
                CREATE OR REPLACE FUNCTION cleanup_old_auth_logs(
                    retention_months INTEGER DEFAULT 12
                ) RETURNS INTEGER AS $$
                DECLARE
                    deleted_count INTEGER;
                    cutoff_date TIMESTAMP;
                BEGIN
                    cutoff_date := now() - (retention_months || ' months')::INTERVAL;

                    DELETE FROM sistema_unidad_territorial.authentication_log 
                    WHERE created_at < cutoff_date;

                    GET DIAGNOSTICS deleted_count = ROW_COUNT;

                    RETURN deleted_count;
                END;
                $$ LANGUAGE plpgsql;
            """)

            await session.execute(function_cleanup)
            logger.info("Función de limpieza creada exitosamente")

        except Exception as e:
            logger.error(f"Error creando función de limpieza: {e}", exc_info=True)
            raise

    @staticmethod
    async def create_triggers(session: AsyncSession) -> None:
        """
        Crear triggers para authentication_log.

        Args:
            session: Sesión de base de datos
        """
        try:
            # Eliminar triggers existentes
            drop_alerts_trigger = text("DROP TRIGGER IF EXISTS authlog_alerts ON sistema_unidad_territorial.authentication_log;")
            drop_geo_trigger = text("DROP TRIGGER IF EXISTS authlog_geo_change ON sistema_unidad_territorial.authentication_log;")

            await session.execute(drop_alerts_trigger)
            await session.execute(drop_geo_trigger)

            # Crear trigger para alertas automáticas
            create_alerts_trigger = text("""
                CREATE TRIGGER authlog_alerts
                    AFTER INSERT ON sistema_unidad_territorial.authentication_log
                    FOR EACH ROW 
                    EXECUTE FUNCTION trg_authlog_alerts();
            """)

            # Crear trigger para detección de cambios geográficos
            create_geo_trigger = text("""
                CREATE TRIGGER authlog_geo_change
                    AFTER INSERT ON sistema_unidad_territorial.authentication_log
                    FOR EACH ROW 
                    EXECUTE FUNCTION trg_authlog_geo_change();
            """)

            await session.execute(create_alerts_trigger)
            await session.execute(create_geo_trigger)

            logger.info("Triggers de autenticación creados exitosamente")

        except Exception as e:
            logger.error(f"Error creando triggers: {e}", exc_info=True)
            raise

    @staticmethod
    async def check_dependencies_exist(session: AsyncSession) -> bool:
        """
        Verificar si todas las dependencias requeridas existen.

        Args:
            session: Sesión de base de datos

        Returns:
            True si todas las dependencias existen, False en caso contrario
        """
        required_tables = ['authentication_log', 'outbox', 'users']

        for table in required_tables:
            exists = await AuthenticationTriggers.check_table_exists(session, table)
            if not exists:
                logger.warning(f"⚠️ Tabla requerida '{table}' no existe")
                return False

        return True

    @staticmethod
    async def check_table_exists(session: AsyncSession, table_name: str, schema: str = 'sistema_unidad_territorial') -> bool:
        """
        Verificar si una tabla existe en el esquema.

        Args:
            session: Sesión de base de datos
            table_name: Nombre de la tabla
            schema: Esquema de la base de datos

        Returns:
            True si la tabla existe, False en caso contrario
        """
        try:
            check_sql = text("""
                SELECT EXISTS (
                    SELECT 1 
                    FROM information_schema.tables 
                    WHERE table_schema = :schema 
                    AND table_name = :table_name
                );
            """)

            result = await session.execute(check_sql, {"schema": schema, "table_name": table_name})
            exists = result.scalar()
            return bool(exists)

        except Exception as e:
            logger.error(f"Error verificando existencia de tabla {table_name}: {e}")
            return False

    @staticmethod
    async def setup_all_auth_triggers(session: AsyncSession) -> None:
        """
        Configurar todos los triggers y vistas de autenticación.

        Args:
            session: Sesión de base de datos
        """
        try:
            logger.info("Iniciando configuración de triggers de autenticación...")

            # Verificar que todas las dependencias existen
            dependencies_exist = await AuthenticationTriggers.check_dependencies_exist(session)

            if not dependencies_exist:
                logger.warning("⚠️ No todas las tablas requeridas existen aún. Los triggers se configurarán después de ejecutar las migraciones.")
                return

            # Crear vistas
            await AuthenticationTriggers.create_auth_log_views(session)

            # Crear funciones
            await AuthenticationTriggers.create_auth_alert_function(session)
            await AuthenticationTriggers.create_geo_change_function(session)
            await AuthenticationTriggers.create_cleanup_function(session)

            # Crear triggers
            await AuthenticationTriggers.create_triggers(session)

            # Commit de todos los cambios
            await session.commit()

            logger.info("Configuración de triggers de autenticación completada exitosamente")

        except Exception as e:
            await session.rollback()
            logger.error(f"Error en configuración de triggers: {e}", exc_info=True)
            raise

    @staticmethod
    async def drop_all_auth_triggers(session: AsyncSession) -> None:
        """
        Eliminar todos los triggers y vistas de autenticación.

        Args:
            session: Sesión de base de datos
        """
        try:
            # Drop triggers
            await session.execute(text("DROP TRIGGER IF EXISTS authlog_alerts ON sistema_unidad_territorial.authentication_log;"))
            await session.execute(text("DROP TRIGGER IF EXISTS authlog_geo_change ON sistema_unidad_territorial.authentication_log;"))

            # Drop functions
            await session.execute(text("DROP FUNCTION IF EXISTS trg_authlog_alerts();"))
            await session.execute(text("DROP FUNCTION IF EXISTS trg_authlog_geo_change();"))
            await session.execute(text("DROP FUNCTION IF EXISTS cleanup_old_auth_logs(INTEGER);"))

            # Drop views
            await session.execute(text("DROP VIEW IF EXISTS v_auth_failures_24h;"))
            await session.execute(text("DROP VIEW IF EXISTS v_auth_rate_limit_analysis;"))
            await session.execute(text("DROP VIEW IF EXISTS v_suspicious_auth_users;"))

            await session.commit()

            logger.info("Triggers y vistas de autenticación eliminados exitosamente")

        except Exception as e:
            await session.rollback()
            logger.error(f"Error eliminando triggers: {e}", exc_info=True)
            raise

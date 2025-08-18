import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool, text

from src.core.config import settings
from src.database import Base
from src.database.utils import DatabaseSetup

# Configuración de Alembic
config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Configurar el schema antes de importar los modelos
Base.metadata.schema = settings.database.db_schema

# Importar los modelos después de configurar el schema
from src.database.models import *

# Configuración de la base de datos
target_metadata = Base.metadata

# Obtener el ambiente y configurar la URL de conexión
script_location = config.get_main_option("script_location")
versions_path = settings.migrations.get_versions_path(
    settings.environment,
    script_location
)

# Crear la carpeta de versiones si no existe
if not os.path.exists(versions_path):
    os.makedirs(versions_path)


# Configurar la ubicación de las versiones
config.set_main_option("version_locations", versions_path)
config.set_main_option("sqlalchemy.url", settings.database.sync_url)


def include_object(object, name, type_, reflected, compare_to):
    """Determina qué objetos incluir en las migraciones."""
    schema = settings.database.db_schema.strip()

    if type_ == "table":
        return object.schema and object.schema == schema
    elif type_ == "column":
        return object.table.schema and object.table.schema == schema
    elif type_ == "sequence":
        return object.schema and object.schema == schema
    return False


def create_schemas_and_extensions(connection):
    """Crea el schema y configura las extensiones necesarias."""
    schema = settings.database.db_schema.strip()

    # Crear schema si no existe
    connection.execute(text(f"CREATE SCHEMA IF NOT EXISTS {schema}"))
    connection.commit()

    # Configurar extensiones PostgreSQL necesarias
    try:
        DatabaseSetup.setup_extensions_sync(connection)
        print("PostgreSQL extensions configured successfully")
    except Exception as e:
        print(f"Warning: Could not configure PostgreSQL extensions: {e}")
        # No fallar si las extensiones ya existen o no se pueden crear


def run_migrations_online():
    """Ejecuta las migraciones en modo online."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    try:
        with connectable.connect() as connection:
            create_schemas_and_extensions(connection)

            context.configure(
                connection=connection,
                target_metadata=target_metadata,
                include_schemas=True,
                include_object=include_object,
                version_table_schema=settings.database.db_schema.strip(),
                compare_type=True
            )

            with context.begin_transaction():
                context.run_migrations()
    except Exception as e:
        print(f"Error during migration: {e}")
        raise


def run_migrations_offline():
    """Ejecuta las migraciones en modo offline."""
    url = config.get_main_option("sqlalchemy.url")

    engine = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
        url=url
    )

    with engine.connect() as connection:
        create_schemas_and_extensions(connection)

    context.configure(
        url=url,
        target_metadata=target_metadata,
        include_schemas=True,
        include_object=include_object,
        version_table_schema=settings.database.db_schema.strip()
    )

    with context.begin_transaction():
        context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

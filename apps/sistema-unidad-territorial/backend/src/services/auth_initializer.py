"""
Servicio para inicializar datos básicos de autenticación.

Crea roles predeterminados y usuario administrador inicial.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from src.database.repositories.auth_repository import AuthRepository, RoleRepository
from src.database.enums import UserStatus
from src.database.triggers.auth_triggers import AuthenticationTriggers
from src.core.security import get_password_hash
from src.core.logging import get_logger


logger = get_logger(__name__)


class AuthInitializer:
    """Inicializador de datos de autenticación."""

    DEFAULT_ROLES = [
        "admin",
        "moderator", 
        "user"
    ]

    @staticmethod
    async def create_default_roles(session: AsyncSession) -> None:
        """
        Crear roles predeterminados si no existen.

        Args:
            session: Sesión de base de datos
        """
        logger.info("🔧 Verificando roles predeterminados...")

        for role_name in AuthInitializer.DEFAULT_ROLES:
            # Verificar si el rol ya existe
            existing_role = await RoleRepository.find_role_by_name(session, role_name)

            if not existing_role:
                # Crear el rol
                await RoleRepository.create_role(session, role_name)
                logger.info(f"✅ Rol '{role_name}' creado")
            else:
                logger.info(f"ℹ️  Rol '{role_name}' ya existe")

        await session.commit()
        logger.info("✅ Roles predeterminados verificados")

    @staticmethod
    async def create_admin_user(
        session: AsyncSession,
        email: str,
        password: str,
        force_update: bool = False
    ) -> None:
        """
        Crear usuario administrador inicial.

        Args:
            session: Sesión de base de datos
            email: Email del administrador
            password: Contraseña del administrador
            force_update: Si True, actualiza la contraseña si el usuario ya existe
        """
        logger.info(f"🔧 Verificando usuario administrador: {email}")

        # Verificar si el usuario ya existe
        existing_user = await AuthRepository.find_user_by_email(session, email)

        if existing_user:
            if force_update:
                # Actualizar contraseña
                await AuthRepository.update_user_password(
                    session, 
                    existing_user, 
                    get_password_hash(password)
                )
                await AuthRepository.update_user_status(
                    session, 
                    existing_user, 
                    UserStatus.ACTIVE
                )
                logger.info(f"🔄 Usuario administrador '{email}' actualizado")
            else:
                logger.info(f"ℹ️  Usuario administrador '{email}' ya existe")

            user = existing_user
        else:
            # Crear nuevo usuario administrador
            user = await AuthRepository.create_user(
                session,
                email=email,
                password_hash=get_password_hash(password),
                status=UserStatus.ACTIVE
            )
            logger.info(f"✅ Usuario administrador '{email}' creado")

        # Asegurar que tenga el rol de administrador
        admin_role = await RoleRepository.find_role_by_name(session, "admin")

        if admin_role:
            # Cargar los roles del usuario explícitamente
            await session.refresh(user, ["roles"])

            if admin_role not in user.roles:
                user.roles.append(admin_role)
                logger.info(f"✅ Rol 'admin' asignado a '{email}'")

        await session.commit()

    @staticmethod
    async def setup_auth_triggers(session: AsyncSession) -> None:
        """
        Configurar triggers y vistas de autenticación.

        Args:
            session: Sesión de base de datos
        """
        logger.info("🔧 Configurando triggers de autenticación...")

        try:
            await AuthenticationTriggers.setup_all_auth_triggers(session)
            logger.info("✅ Triggers de autenticación configurados")

        except Exception as e:
            logger.warning(f"⚠️ No se pudieron configurar los triggers: {e}")
            logger.info("ℹ️ Los triggers se configurarán después de ejecutar las migraciones de la base de datos")
            # No hacer rollback ni raise, solo continuar

    @staticmethod
    async def initialize_auth_data(
        session: AsyncSession,
        admin_email: str = "vin.orellana@duocuc.cl",
        admin_password: str = "admin123",
        force_update_admin: bool = False,
        setup_triggers: bool = True
    ) -> None:
        """
        Inicializar todos los datos básicos de autenticación.

        Args:
            session: Sesión de base de datos
            admin_email: Email del administrador inicial
            admin_password: Contraseña del administrador inicial
            force_update_admin: Si True, actualiza el admin si ya existe
            setup_triggers: Si True, configura los triggers de autenticación
        """
        logger.info("🚀 Iniciando configuración completa de autenticación...")

        try:
            # Crear roles predeterminados
            await AuthInitializer.create_default_roles(session)

            # Crear usuario administrador
            await AuthInitializer.create_admin_user(
                session, 
                admin_email, 
                admin_password,
                force_update_admin
            )

            # Configurar triggers de autenticación si se solicita
            if setup_triggers:
                await AuthInitializer.setup_auth_triggers(session)

            logger.info("✅ Configuración completa de autenticación terminada")

        except Exception as e:
            logger.error(f"❌ Error en configuración de autenticación: {e}")
            await session.rollback()
            raise

    @staticmethod
    async def initialize_only_triggers(session: AsyncSession) -> None:
        """
        Configurar solo los triggers de autenticación (útil para migraciones).

        Args:
            session: Sesión de base de datos
        """
        logger.info("🔧 Configurando únicamente triggers de autenticación...")

        try:
            await AuthInitializer.setup_auth_triggers(session)
            logger.info("✅ Triggers de autenticación configurados exitosamente")

        except Exception as e:
            logger.error(f"❌ Error configurando triggers: {e}")
            await session.rollback()
            raise

    @staticmethod
    async def drop_auth_triggers(session: AsyncSession) -> None:
        """
        Eliminar todos los triggers de autenticación.

        Args:
            session: Sesión de base de datos
        """
        logger.info("🗑️ Eliminando triggers de autenticación...")

        try:
            await AuthenticationTriggers.drop_all_auth_triggers(session)
            logger.info("✅ Triggers de autenticación eliminados")

        except Exception as e:
            logger.error(f"❌ Error eliminando triggers: {e}")
            await session.rollback()
            raise

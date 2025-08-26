"""
Servicio para inicializar datos básicos de autenticación.

Crea roles predeterminados y usuario administrador inicial.
"""

from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.repositories import AuthRepository, RoleRepository
from src.database.enums import UserStatus, RoleScope
from src.database.triggers.community_triggers import (
    LIMIT_MODERATORS_FUNCTION,
    DROP_LIMIT_MODERATORS_TRIGGER,
    CREATE_LIMIT_MODERATORS_TRIGGER,
    LOGIN_GATING_VIEW,
    CAN_USER_LOGIN_FUNCTION,
    CAN_OAUTH_LOGIN_FUNCTION
)
from src.database.triggers.auth_triggers import AuthenticationTriggers
from src.core.security import get_password_hash
from src.core.logging import get_logger


logger = get_logger(__name__)


class AuthInitializer:
    """Inicializador de datos de autenticación."""

    # Los roles por defecto ahora se manejan con scope en AuthCommunityInitializer
    # Mantenemos solo roles globales básicos aquí
    DEFAULT_GLOBAL_ROLES = [
        "SUPERADMIN",
        "SUPPORT"
    ]

    @staticmethod
    async def create_default_roles(session: AsyncSession) -> None:
        """
        Crear roles predeterminados si no existen.

        Args:
            session: Sesión de base de datos
        """
        logger.info("🔧 Verificando roles predeterminados...")

        for role_name in AuthInitializer.DEFAULT_GLOBAL_ROLES:
            # Verificar si el rol ya existe
            existing_role = await RoleRepository.find_role_by_name_and_scope(
                session, role_name, RoleScope.GLOBAL
            )

            if not existing_role:
                # Crear el rol
                await RoleRepository.create_role(session, role_name, RoleScope.GLOBAL)
                logger.info(f"✅ Rol global '{role_name}' creado")
            else:
                logger.info(f"ℹ️  Rol global '{role_name}' ya existe")

        await session.commit()
        logger.info("✅ Roles predeterminados verificados")

    @staticmethod
    async def create_all_unified_roles(session: AsyncSession) -> None:
        """
        Crear todos los roles del sistema unificado.

        Args:
            session: Sesión de base de datos
        """
        logger.info("🔧 Creando todos los roles del sistema unificado...")

        all_roles = [
            ("SUPERADMIN", RoleScope.GLOBAL),
            ("SUPPORT", RoleScope.GLOBAL),
            ("ADMIN", RoleScope.TENANT),
            ("MODERATOR", RoleScope.COMMUNITY),
        ]

        for role_name, scope in all_roles:
            existing_role = await RoleRepository.find_role_by_name_and_scope(
                session, role_name, scope
            )

            if not existing_role:
                await RoleRepository.create_role(session, role_name, scope)
                logger.info(f"✅ Rol '{role_name}' con scope '{scope.value}' creado")
            else:
                logger.info(f"ℹ️  Rol '{role_name}' con scope '{scope.value}' ya existe")

        await session.commit()
        logger.info("✅ Todos los roles del sistema unificado verificados")

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

        # Asignar todos los roles disponibles al usuario administrador
        await AuthInitializer._assign_all_roles_to_user(session, user)

        await session.commit()

    @staticmethod
    async def _assign_all_roles_to_user(session: AsyncSession, user) -> None:
        """
        Asignar todos los roles disponibles al usuario.

        Args:
            session: Sesión de base de datos
            user: Usuario al que asignar los roles
        """
        logger.info(f"🔧 Asignando todos los roles al usuario {user.email}...")

        # Obtener todos los roles existentes
        all_roles = await RoleRepository.get_all_roles(session)

        for role in all_roles:
            try:
                if role.scope == RoleScope.GLOBAL:
                    # Roles globales no requieren contexto
                    await RoleRepository.assign_role_to_user(
                        session,
                        role_id=role.id,
                        user_id=user.id,
                        tenant_id=None,
                        community_id=None
                    )
                    logger.info(f"✅ Rol GLOBAL '{role.name}' asignado")

                elif role.scope == RoleScope.TENANT:
                    # Para roles TENANT, se asignarán cuando se creen tenants específicos
                    logger.info(f"ℹ️  Rol TENANT '{role.name}' se asignará cuando se creen tenants específicos")

                elif role.scope == RoleScope.COMMUNITY:
                    # Para roles COMMUNITY, se asignarán cuando se creen communities específicas
                    logger.info(f"ℹ️  Rol COMMUNITY '{role.name}' se asignará cuando se creen communities específicas")

            except Exception as e:
                logger.warning(f"⚠️ No se pudo asignar rol '{role.name}' con scope '{role.scope}': {e}")
                # Continuar con el siguiente rol
                continue

        logger.info(f"✅ Roles globales asignados al usuario {user.email}")

    @staticmethod
    async def assign_contextual_roles_to_admin(
        session: AsyncSession, 
        user_email: str,
        tenant_id: UUID = None,
        community_id: UUID = None
    ) -> None:
        """
        Asignar roles contextuales (TENANT/COMMUNITY) al usuario administrador.

        Args:
            session: Sesión de base de datos
            user_email: Email del usuario administrador
            tenant_id: ID del tenant para asignar rol ADMIN
            community_id: ID de la community para asignar rol MODERATOR
        """
        logger.info(f"🔧 Asignando roles contextuales al usuario {user_email}...")

        # Buscar el usuario
        user = await AuthRepository.find_user_by_email(session, user_email)
        if not user:
            logger.error(f"❌ Usuario {user_email} no encontrado")
            return

        # Asignar rol ADMIN si se proporciona tenant_id
        if tenant_id:
            admin_role = await RoleRepository.find_role_by_name_and_scope(
                session, "ADMIN", RoleScope.TENANT
            )
            if admin_role:
                try:
                    await RoleRepository.assign_role_to_user(
                        session,
                        role_id=admin_role.id,
                        user_id=user.id,
                        tenant_id=tenant_id,
                        community_id=None
                    )
                    logger.info(f"✅ Rol ADMIN asignado para tenant {tenant_id}")
                except Exception as e:
                    logger.warning(f"⚠️ No se pudo asignar rol ADMIN: {e}")

        # Asignar rol MODERATOR si se proporciona community_id
        if community_id:
            moderator_role = await RoleRepository.find_role_by_name_and_scope(
                session, "MODERATOR", RoleScope.COMMUNITY
            )
            if moderator_role:
                try:
                    await RoleRepository.assign_role_to_user(
                        session,
                        role_id=moderator_role.id,
                        user_id=user.id,
                        tenant_id=None,  # Los roles COMMUNITY pueden tener tenant_id opcional
                        community_id=community_id
                    )
                    logger.info(f"✅ Rol MODERATOR asignado para community {community_id}")
                except Exception as e:
                    logger.warning(f"⚠️ No se pudo asignar rol MODERATOR: {e}")

        await session.commit()
        logger.info(f"✅ Roles contextuales asignados al usuario {user_email}")

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
    async def setup_community_triggers(session: AsyncSession) -> None:
        """
        Configurar triggers y funciones específicos de comunidades.

        Args:
            session: Sesión de base de datos
        """
        logger.info("🔧 Configurando triggers de comunidad...")

        try:
            # Crear función para limitar moderadores
            await session.execute(LIMIT_MODERATORS_FUNCTION)

            # Crear trigger para limitar moderadores
            await session.execute(DROP_LIMIT_MODERATORS_TRIGGER)
            await session.execute(CREATE_LIMIT_MODERATORS_TRIGGER)

            # Crear vista y funciones de control de login
            await session.execute(LOGIN_GATING_VIEW)
            await session.execute(CAN_USER_LOGIN_FUNCTION)
            await session.execute(CAN_OAUTH_LOGIN_FUNCTION)

            await session.commit()
            logger.info("✅ Triggers de comunidad configurados")

        except Exception as e:
            logger.warning(f"⚠️ No se pudieron configurar los triggers de comunidad: {e}")
            logger.info("ℹ️ Los triggers de comunidad se configurarán después de ejecutar las migraciones")
            # No hacer rollback ni raise, solo continuar

    @staticmethod
    async def initialize_auth_data(
        session: AsyncSession,
        admin_email: str = "vin.orellana@duocuc.cl",
        admin_password: str = "admin123",
        force_update_admin: bool = False,
        setup_triggers: bool = True,
        setup_community_features: bool = True
    ) -> None:
        """
        Inicializar todos los datos básicos de autenticación y comunidades.

        Args:
            session: Sesión de base de datos
            admin_email: Email del administrador inicial
            admin_password: Contraseña del administrador inicial
            force_update_admin: Si True, actualiza el admin si ya existe
            setup_triggers: Si True, configura los triggers de autenticación
            setup_community_features: Si True, configura el sistema de comunidades
        """
        logger.info("🚀 Iniciando configuración completa del sistema...")

        try:
            # Crear todos los roles del sistema unificado
            await AuthInitializer.create_all_unified_roles(session)

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

            # Configurar funciones de comunidad si se solicita
            if setup_community_features:
                await AuthInitializer.setup_community_triggers(session)

            logger.info("✅ Configuración completa del sistema terminada")

        except Exception as e:
            logger.error(f"❌ Error en configuración del sistema: {e}")
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

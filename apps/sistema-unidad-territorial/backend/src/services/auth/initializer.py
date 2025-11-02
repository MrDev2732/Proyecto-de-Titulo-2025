"""
Servicio para inicializar datos básicos de autenticación.

Crea roles predeterminados y usuario administrador inicial.
"""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.repositories import (
    AuthRepository,
    RoleRepository,
    CommunityRepository,
    ResidentMembershipRepository,
)
from src.database.enums import UserStatus, RoleScope, MembershipStatus
from src.database.models import Tenant
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
                session, role_name, RoleScope.SYSTEM
            )

            if not existing_role:
                # Crear el rol
                await RoleRepository.create_role(session, role_name, RoleScope.SYSTEM)
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
            ("SUPERADMIN", RoleScope.SYSTEM),
            ("SUPPORT", RoleScope.SYSTEM),
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
        force_update: bool = False,
        full_name: str = "Administrador del Sistema",
        rut: str = "12345678-5"
    ) -> None:
        """
        Crear usuario administrador inicial.

        Args:
            session: Sesión de base de datos
            email: Email del administrador
            password: Contraseña del administrador
            force_update: Si True, actualiza la contraseña si el usuario ya existe
            full_name: Nombre completo del administrador
            rut: RUT del administrador
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
                status=UserStatus.ACTIVE,
                full_name=full_name,
                rut=rut
            )
            logger.info(f"✅ Usuario administrador '{email}' creado con nombre '{full_name}' y RUT '{rut}'")

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
                if role.scope == RoleScope.SYSTEM:
                    # Roles de sistema no requieren contexto
                    assignment = await RoleRepository.assign_system_role_to_user(
                        session,
                        role_id=role.id,
                        user_id=user.id
                    )
                    # Verificar si es una asignación nueva o existente
                    if assignment.created_at == assignment.updated_at:
                        logger.info(f"✅ Rol SYSTEM '{role.name}' asignado")
                    else:
                        logger.info(f"ℹ️  Rol SYSTEM '{role.name}' ya estaba asignado")

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
    async def create_demo_tenant(
        session: AsyncSession,
        tenant_name: str = "Municipalidad de Ejemplo"
    ) -> Tenant:
        """
        Crear un tenant de demostración si no existe.

        Args:
            session: Sesión de base de datos
            tenant_name: Nombre del tenant

        Returns:
            Tenant: Tenant creado o existente
        """
        logger.info(f"🏛️ Verificando tenant de demostración: {tenant_name}")
        
        result = await session.execute(
            select(Tenant).where(Tenant.name == tenant_name)
        )
        existing_tenant = result.scalar_one_or_none()

        if existing_tenant:
            logger.info(f"ℹ️  Tenant '{tenant_name}' ya existe")
            return existing_tenant

        # Crear nuevo tenant
        tenant = Tenant(name=tenant_name)
        session.add(tenant)
        await session.flush()
        
        logger.info(f"✅ Tenant '{tenant_name}' creado con ID: {tenant.id}")
        return tenant

    @staticmethod
    async def create_demo_community(
        session: AsyncSession,
        tenant_id: UUID,
        community_name: str = "Junta de Vecinos Villa Ejemplo",
        community_description: str = "Comunidad de demostración para pruebas del sistema"
    ):
        """
        Crear una comunidad de demostración si no existe.

        Args:
            session: Sesión de base de datos
            tenant_id: ID del tenant
            community_name: Nombre de la comunidad
            community_description: Descripción de la comunidad

        Returns:
            Community: Comunidad creada o existente
        """
        logger.info(f"🏘️ Verificando comunidad de demostración: {community_name}")

        # Buscar si ya existe la comunidad
        existing_community = await CommunityRepository.find_community_by_name(
            session, tenant_id, community_name
        )

        if existing_community:
            logger.info(f"ℹ️  Comunidad '{community_name}' ya existe")
            return existing_community

        # Crear nueva comunidad
        community = await CommunityRepository.create_community(
            session=session,
            tenant_id=tenant_id,
            name=community_name,
            description=community_description
        )

        logger.info(f"✅ Comunidad '{community_name}' creada con ID: {community.id}")
        return community

    @staticmethod
    async def create_admin_community_membership(
        session: AsyncSession,
        user_id: UUID,
        community_id: UUID
    ):
        """
        Crear membresía de administrador en la comunidad.

        Args:
            session: Sesión de base de datos
            user_id: ID del usuario administrador
            community_id: ID de la comunidad
        """
        logger.info(f"👥 Creando membresía de administrador en comunidad {community_id}")

        # Verificar si ya existe la membresía
        existing_membership = await ResidentMembershipRepository.find_user_membership_in_community(
            session, user_id, community_id
        )

        if existing_membership:
            logger.info(f"ℹ️  Membresía ya existe para usuario {user_id}")
            return existing_membership

        # Crear nueva membresía aprobada y verificada
        membership = await ResidentMembershipRepository.create_membership(
            session=session,
            user_id=user_id,
            community_id=community_id,
            status=MembershipStatus.APPROVED,
            verified=True
        )

        logger.info(f"✅ Membresía creada para usuario {user_id} en comunidad {community_id}")
        return membership

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
                # Verificar si el usuario ya tiene el rol ADMIN en este tenant
                has_admin_role = await RoleRepository.user_has_role_in_tenant(
                    session, user.id, "ADMIN", tenant_id
                )

                if has_admin_role:
                    logger.info(f"ℹ️  Usuario ya tiene rol ADMIN en tenant {tenant_id}")
                else:
                    try:
                        await RoleRepository.assign_tenant_role_to_user(
                            session,
                            role_id=admin_role.id,
                            user_id=user.id,
                            tenant_id=tenant_id
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
                # Verificar si el usuario ya tiene el rol MODERATOR en esta comunidad
                has_moderator_role = await RoleRepository.user_has_role_in_community(
                    session, user.id, "MODERATOR", community_id
                )

                if has_moderator_role:
                    logger.info(f"ℹ️  Usuario ya tiene rol MODERATOR en community {community_id}")
                else:
                    try:
                        await RoleRepository.assign_community_role_to_user(
                            session,
                            role_id=moderator_role.id,
                            user_id=user.id,
                            community_id=community_id
                        )
                        logger.info(f"✅ Rol MODERATOR asignado para community {community_id}")
                    except Exception as e:
                        logger.warning(f"⚠️ No se pudo asignar rol MODERATOR: {e}")

        await session.commit()
        logger.info(f"✅ Roles contextuales asignados al usuario {user_email}")

    @staticmethod
    async def setup_demo_community_data(
        session: AsyncSession,
        admin_email: str
    ) -> None:
        """
        Configurar datos de demostración: tenant, comunidad y membresía del admin.

        Args:
            session: Sesión de base de datos
            admin_email: Email del usuario administrador
        """
        logger.info("🏘️ Configurando datos de demostración de comunidad...")

        try:
            # 1. Crear tenant de demostración
            demo_tenant = await AuthInitializer.create_demo_tenant(session)

            # 2. Crear comunidad de demostración
            demo_community = await AuthInitializer.create_demo_community(
                session, demo_tenant.id
            )

            # 3. Buscar el usuario administrador
            admin_user = await AuthRepository.find_user_by_email(session, admin_email)
            if not admin_user:
                logger.error(f"❌ Usuario administrador {admin_email} no encontrado")
                return

            # 4. Crear membresía del administrador en la comunidad
            await AuthInitializer.create_admin_community_membership(
                session, admin_user.id, demo_community.id
            )

            # 5. Asignar roles contextuales al administrador
            await AuthInitializer.assign_contextual_roles_to_admin(
                session=session,
                user_email=admin_email,
                tenant_id=demo_tenant.id,
                community_id=demo_community.id
            )

            logger.info("✅ Datos de demostración de comunidad configurados exitosamente")
            logger.info(f"   📍 Tenant: {demo_tenant.name} (ID: {demo_tenant.id})")
            logger.info(f"   🏘️ Comunidad: {demo_community.name} (ID: {demo_community.id})")
            logger.info(f"   👤 Usuario {admin_email} es miembro y moderador de la comunidad")

        except Exception as e:
            logger.error(f"❌ Error configurando datos de demostración: {e}")
            raise

    @staticmethod
    async def initialize_auth_data(
        session: AsyncSession,
        admin_email: str = "vin.orellana@duocuc.cl",
        admin_password: str = "admin123",
        admin_full_name: str = "Vincenzo Orellana",
        admin_rut: str = "21545905-5",
        force_update_admin: bool = False,
        setup_triggers: bool = True,
        setup_community_features: bool = True,
        create_demo_data: bool = True
    ) -> None:
        """
        Inicializar todos los datos básicos de autenticación y comunidades.

        Args:
            session: Sesión de base de datos
            admin_email: Email del administrador inicial
            admin_password: Contraseña del administrador inicial
            admin_full_name: Nombre completo del administrador inicial
            admin_rut: RUT del administrador inicial
            force_update_admin: Si True, actualiza el admin si ya existe
            setup_triggers: Si True, configura los triggers de autenticación
            setup_community_features: Si True, configura el sistema de comunidades
            create_demo_data: Si True, crea tenant y comunidad de demostración
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
                force_update_admin,
                admin_full_name,
                admin_rut
            )

            # Crear datos de demostración si se solicita
            if create_demo_data:
                await AuthInitializer.setup_demo_community_data(session, admin_email)

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

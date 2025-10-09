"""
Servicio para manejo de aprobaciones de solicitudes de registro.

Contiene la lógica de negocio para aprobar solicitudes y crear todo el ecosistema de datos.
"""

from typing import Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from src.database.models import User, RegistrationRequest, Community
from src.database.repositories import (
    AuthRepository,
    RegistrationRequestRepository,
    ResidentMembershipRepository, 
    AddressEvidenceRepository
)
from src.database.enums import MembershipStatus, UserStatus
from src.core.security import generate_secure_password, get_password_hash
from src.core.logging import get_logger
from src.services.email import EmailService


logger = get_logger(__name__)


class RegistrationApprovalService:
    """Servicio para aprobación de solicitudes de registro."""

    @staticmethod
    async def approve_registration_request(
        session: AsyncSession,
        request_id: UUID,
        decided_by: UUID,
        decision_notes: Optional[str] = None
    ) -> RegistrationRequest:
        """
        Aprobar una solicitud de registro y crear todo el ecosistema de datos.

        Args:
            session: Sesión de base de datos
            request_id: ID de la solicitud
            decided_by: ID del moderador que aprueba
            decision_notes: Notas opcionales del moderador

        Returns:
            RegistrationRequest: Solicitud aprobada

        Raises:
            HTTPException: Si la solicitud no se encuentra
        """
        # Aprobar la solicitud
        approved_request = await RegistrationRequestRepository.approve_registration_request(
            session=session,
            request_id=request_id,
            decided_by=decided_by,
            decision_notes=decision_notes
        )

        if not approved_request:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Solicitud de registro no encontrada"
            )

        # Buscar o crear usuario
        user = await RegistrationApprovalService._get_or_create_user(
            session=session,
            registration_request=approved_request
        )

        # Crear evidencias de dirección a partir de los adjuntos
        if approved_request.attachments:
            evidences = await AddressEvidenceRepository.create_address_evidence_from_attachments(
                session=session,
                user_id=user.id,
                attachments=approved_request.attachments,
                tenant_id=approved_request.tenant_id
            )
            logger.info(f"✅ Created {len(evidences)} address evidence records for user {approved_request.email}")

        # Crear membresía para el usuario en la comunidad
        await ResidentMembershipRepository.create_membership(
            session=session,
            user_id=user.id,
            community_id=approved_request.community_id,
            status=MembershipStatus.APPROVED,
            verified=True
        )
        logger.info(f"✅ Created membership for user {approved_request.email} in community {approved_request.community_id}")

        return approved_request

    @staticmethod
    async def _get_or_create_user(
        session: AsyncSession,
        registration_request: RegistrationRequest
    ) -> User:
        """
        Buscar usuario existente o crear uno nuevo con contraseña aleatoria y datos completos.

        Args:
            session: Sesión de base de datos
            registration_request: Solicitud de registro con todos los datos del usuario

        Returns:
            User: Usuario encontrado o creado
        """
        email = registration_request.email

        # Buscar usuario existente
        user = await AuthRepository.find_user_by_email(session, email)

        if not user:
            # Crear usuario con contraseña aleatoria y datos completos
            random_password = generate_secure_password()
            logger.info(f"🔑 Temporary password for {email}: {random_password}")
            user = await AuthRepository.create_user(
                session=session,
                email=email,
                password_hash=get_password_hash(random_password),
                status=UserStatus.ACTIVE,
                full_name=registration_request.full_name,
                rut=registration_request.rut,
                address=registration_request.address
            )

            logger.info(f"✅ Created new user {email} with complete profile data")
            logger.info(f"   👤 Name: {registration_request.full_name}")
            logger.info(f"   🆔 RUT: {registration_request.rut}")
            logger.info(f"   🏠 Address: {registration_request.address}")

            # Enviar email de bienvenida con contraseña temporal
            try:
                community = await session.get(Community, registration_request.community_id)
                community_name = community.name if community else "Comunidad"

                email_sent = await EmailService.send_welcome_email(
                    to_email=email,
                    full_name=registration_request.full_name,
                    temporary_password=random_password,
                    community_name=community_name
                )

                if email_sent:
                    logger.info(f"📧 Welcome email sent to {email}")
                else:
                    logger.warning(f"⚠️ Failed to send welcome email to {email}")

            except Exception as e:
                logger.error(f"❌ Error sending welcome email to {email}: {e}")

            # Para desarrollo, también loggeamos la contraseña
            logger.info(f"🔑 Temporary password for {email}: {random_password}")
        else:
            logger.info(f"✅ Found existing user {email}")

            # Si el usuario existe pero no tiene datos completos, actualizarlos
            needs_update = False
            if not user.full_name and registration_request.full_name:
                user.full_name = registration_request.full_name
                needs_update = True

            if not user.rut and registration_request.rut:
                user.rut = registration_request.rut
                needs_update = True

            if not user.address and registration_request.address:
                user.address = registration_request.address
                needs_update = True

            if needs_update:
                await session.flush()
                logger.info(f"🔄 Updated existing user {email} with missing profile data")

        return user

    @staticmethod
    async def register_resident_manually(
        session: AsyncSession,
        community_id: UUID,
        email: str,
        full_name: str,
        rut: str,
        address: str,
        registered_by: UUID,
        notes: Optional[str] = None
    ) -> tuple[User, UUID, Optional[str]]:
        """
        Registrar manualmente a un vecino sin pasar por el proceso de solicitud.

        Args:
            session: Sesión de base de datos
            community_id: ID de la comunidad
            email: Email del vecino
            full_name: Nombre completo del vecino
            rut: RUT del vecino
            address: Dirección del vecino
            registered_by: ID del moderador que registra
            notes: Notas opcionales del moderador

        Returns:
            tuple: (Usuario creado/encontrado, ID de membresía, contraseña temporal si es nuevo usuario)

        Raises:
            HTTPException: Si hay errores en el proceso
        """
        # Buscar o crear usuario
        user = await AuthRepository.find_user_by_email(session, email)
        temporary_password = None

        if not user:
            # Crear usuario con contraseña aleatoria y datos completos
            temporary_password = generate_secure_password()
            user = await AuthRepository.create_user(
                session=session,
                email=email,
                password_hash=get_password_hash(temporary_password),
                status=UserStatus.ACTIVE,
                full_name=full_name,
                rut=rut,
                address=address
            )
            logger.info(f"✅ Created new user {email} via manual registration")
            logger.info(f"   👤 Name: {full_name}")
            logger.info(f"   🆔 RUT: {rut}")
            logger.info(f"   🏠 Address: {address}")
            logger.info(f"   🔑 Temporary password: {temporary_password}")

            # Enviar email de bienvenida con contraseña temporal
            try:
                community = await session.get(Community, community_id)
                community_name = community.name if community else "Comunidad"

                email_sent = await EmailService.send_welcome_email(
                    to_email=email,
                    full_name=full_name,
                    temporary_password=temporary_password,
                    community_name=community_name
                )

                if email_sent:
                    logger.info(f"📧 Welcome email sent to {email} for manual registration")
                else:
                    logger.warning(f"⚠️ Failed to send welcome email to {email} for manual registration")

            except Exception as e:
                logger.error(f"❌ Error sending welcome email for manual registration to {email}: {e}")
        else:
            logger.info(f"✅ Found existing user {email} for manual registration")

            # Si el usuario existe pero no tiene datos completos, actualizarlos
            needs_update = False
            if not user.full_name and full_name:
                user.full_name = full_name
                needs_update = True

            if not user.rut and rut:
                user.rut = rut
                needs_update = True

            if not user.address and address:
                user.address = address
                needs_update = True

            if needs_update:
                await session.flush()
                logger.info(f"🔄 Updated existing user {email} with missing profile data")

        # Verificar si ya tiene membresía en esta comunidad
        existing_membership = await ResidentMembershipRepository.find_user_membership_in_community(
            session, user.id, community_id
        )

        if existing_membership:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El usuario ya tiene una membresía en esta comunidad"
            )

        # Crear membresía para el usuario en la comunidad
        membership = await ResidentMembershipRepository.create_membership(
            session=session,
            user_id=user.id,
            community_id=community_id,
            status=MembershipStatus.APPROVED,
            verified=True
        )

        logger.info(f"✅ Created membership for user {email} in community {community_id} via manual registration by {registered_by}")
        if notes:
            logger.info(f"   📝 Notes: {notes}")

        return user, membership.id, temporary_password

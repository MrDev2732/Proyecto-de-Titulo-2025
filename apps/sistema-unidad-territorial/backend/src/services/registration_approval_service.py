"""
Servicio para manejo de aprobaciones de solicitudes de registro.

Contiene la lógica de negocio para aprobar solicitudes y crear todo el ecosistema de datos.
"""

from typing import Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from src.database.models import User, RegistrationRequest
from src.database.repositories.auth_repository import AuthRepository
from src.database.repositories.community_repository import (
    RegistrationRequestRepository,
    ResidentMembershipRepository
)
from src.database.repositories.resident_repository import AddressEvidenceRepository
from src.database.enums import MembershipStatus, UserStatus
from src.core.security import generate_secure_password, get_password_hash
from src.core.logging import get_logger


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

            # TODO: Enviar email con la contraseña temporal al usuario
            # Por ahora solo loggeamos la contraseña (NO hacer esto en producción)
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

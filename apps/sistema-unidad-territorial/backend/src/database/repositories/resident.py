"""
Repository para manejo de residentes y evidencias de dirección.

Contiene todas las operaciones relacionadas con el modelo Resident y AddressEvidence.
"""

from typing import List, Optional
from uuid import UUID

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.database import (
    now_chile,
    ResidentMembership,
    RegistrationRequestAttachment,
    MembershipStatus,
    AddressEvidence,
    RegistrationRequestAttachment,
)
from src.database.enums import EvidenceType
from src.core.logging import get_logger


logger = get_logger(__name__)

class ResidentMembershipRepository:
    """Repository para operaciones de membresías de residentes."""

    @staticmethod
    async def create_membership(
        session: AsyncSession,
        user_id: UUID,
        community_id: UUID,
        status: MembershipStatus = MembershipStatus.PENDING,
        verified: bool = False
    ) -> ResidentMembership:
        """
        Crear una nueva membresía de residente.

        Args:
            session: Sesión de base de datos
            user_id: ID del usuario
            community_id: ID de la comunidad
            status: Estado de la membresía
            verified: Si está verificada

        Returns:
            ResidentMembership: Membresía creada
        """
        membership = ResidentMembership(
            user_id=user_id,
            community_id=community_id,
            status=status,
            verified=verified
        )
        session.add(membership)
        await session.flush()
        return membership

    @staticmethod
    async def find_user_membership_in_community(
        session: AsyncSession,
        user_id: UUID,
        community_id: UUID
    ) -> Optional[ResidentMembership]:
        """
        Buscar la membresía de un usuario en una comunidad específica.

        Args:
            session: Sesión de base de datos
            user_id: ID del usuario
            community_id: ID de la comunidad

        Returns:
            ResidentMembership: Membresía encontrada o None
        """
        result = await session.execute(
            select(ResidentMembership).where(
                and_(
                    ResidentMembership.user_id == user_id,
                    ResidentMembership.community_id == community_id
                )
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_user_approved_memberships(
        session: AsyncSession,
        user_id: UUID
    ) -> List[ResidentMembership]:
        """
        Obtener todas las membresías aprobadas de un usuario.

        Args:
            session: Sesión de base de datos
            user_id: ID del usuario

        Returns:
            List[ResidentMembership]: Lista de membresías aprobadas
        """
        result = await session.execute(
            select(ResidentMembership)
            .options(selectinload(ResidentMembership.community))
            .where(
                and_(
                    ResidentMembership.user_id == user_id,
                    ResidentMembership.status == MembershipStatus.APPROVED
                )
            )
        )
        return list(result.scalars().all())

    @staticmethod
    async def user_has_approved_membership(
        session: AsyncSession,
        user_id: UUID
    ) -> bool:
        """
        Verificar si un usuario tiene al menos una membresía aprobada.

        Args:
            session: Sesión de base de datos
            user_id: ID del usuario

        Returns:
            bool: True si tiene membresía aprobada, False si no
        """
        result = await session.execute(
            select(ResidentMembership).where(
                and_(
                    ResidentMembership.user_id == user_id,
                    ResidentMembership.status == MembershipStatus.APPROVED
                )
            )
        )
        return result.scalar_one_or_none() is not None

    @staticmethod
    async def approve_membership(
        session: AsyncSession,
        membership_id: UUID,
        verified: bool = True
    ) -> Optional[ResidentMembership]:
        """
        Aprobar una membresía y opcionalmente verificarla.

        Args:
            session: Sesión de base de datos
            membership_id: ID de la membresía
            verified: Si marcar como verificada

        Returns:
            ResidentMembership: Membresía actualizada o None si no se encontró
        """
        result = await session.execute(
            select(ResidentMembership).where(ResidentMembership.id == membership_id)
        )
        membership = result.scalar_one_or_none()

        if membership:
            membership.status = MembershipStatus.APPROVED
            membership.verified = verified
            if verified:
                membership.verified_at = now_chile()
            await session.flush()

        return membership


class AddressEvidenceRepository:
    """Repository para operaciones de evidencias de dirección."""

    @staticmethod
    async def create_address_evidence(
        session: AsyncSession,
        tenant_id: UUID,
        user_id: UUID,
        evidence_type: str,
        bucket: str,
        storage_key: str,
        sha256: str,
        mime_type: str
    ) -> AddressEvidence:
        """
        Crear una nueva evidencia de dirección.

        Args:
            session: Sesión de base de datos
            tenant_id: ID del tenant
            user_id: ID del usuario
            evidence_type: Tipo de evidencia
            bucket: Bucket donde se almacena el archivo
            storage_key: Clave de almacenamiento del archivo
            sha256: Hash SHA256 del archivo
            mime_type: Tipo MIME del archivo

        Returns:
            AddressEvidence: Evidencia creada
        """
        evidence = AddressEvidence(
            tenant_id=tenant_id,
            user_id=user_id,
            type=evidence_type,
            bucket=bucket,
            storage_key=storage_key,
            sha256=sha256,
            mime_type=mime_type
        )

        session.add(evidence)
        await session.flush()
        return evidence

    @staticmethod
    async def create_address_evidence_from_attachments(
        session: AsyncSession,
        user_id: UUID,
        attachments: List[RegistrationRequestAttachment],
        tenant_id: UUID
    ) -> List[AddressEvidence]:
        """
        Crear evidencias de dirección a partir de los adjuntos de la solicitud.

        Args:
            session: Sesión de base de datos
            user_id: ID del usuario
            attachments: Lista de adjuntos de la solicitud
            tenant_id: ID del tenant

        Returns:
            List[AddressEvidence]: Lista de evidencias creadas
        """
        evidences = []

        for attachment in attachments:
            # Mapear tipos de adjuntos a tipos de evidencia
            evidence_type = EvidenceType.OTHER
            if attachment.kind.value == "utility_bill":
                evidence_type = EvidenceType.UTILITY_BILL
            elif attachment.kind.value in ["id_card_front", "id_card_back"]:
                # Los documentos de identidad se pueden considerar como "other"
                evidence_type = EvidenceType.OTHER

            evidence = await AddressEvidenceRepository.create_address_evidence(
                session=session,
                tenant_id=tenant_id,
                user_id=user_id,
                evidence_type=evidence_type.value,
                bucket=attachment.bucket,
                storage_key=attachment.storage_key,
                sha256=attachment.sha256,
                mime_type=attachment.mime_type
            )

            evidences.append(evidence)

        return evidences

    @staticmethod
    async def get_user_evidences(
        session: AsyncSession,
        user_id: UUID
    ) -> List[AddressEvidence]:
        """
        Obtener todas las evidencias de un usuario.

        Args:
            session: Sesión de base de datos
            user_id: ID del usuario

        Returns:
            List[AddressEvidence]: Lista de evidencias
        """
        result = await session.execute(
            select(AddressEvidence).where(AddressEvidence.user_id == user_id)
        )
        return list(result.scalars().all())

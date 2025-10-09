"""
Repository para manejo de residentes y evidencias de dirección.

Contiene todas las operaciones relacionadas con el modelo Resident y AddressEvidence.
"""

from typing import List
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import AddressEvidence, RegistrationRequestAttachment
from src.database.enums import EvidenceType
from src.core.logging import get_logger


logger = get_logger(__name__)


class AddressEvidenceRepository:
    """Repository para operaciones de evidencias de dirección."""

    @staticmethod
    async def create_address_evidence(
        session: AsyncSession,
        tenant_id: UUID,
        user_id: UUID,
        evidence_type: str,
        url: str
    ) -> AddressEvidence:
        """
        Crear una nueva evidencia de dirección.

        Args:
            session: Sesión de base de datos
            tenant_id: ID del tenant
            user_id: ID del usuario
            evidence_type: Tipo de evidencia
            url: URL del archivo

        Returns:
            AddressEvidence: Evidencia creada
        """
        evidence = AddressEvidence(
            tenant_id=tenant_id,
            user_id=user_id,
            type=evidence_type,
            url=url
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
                url=attachment.url
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

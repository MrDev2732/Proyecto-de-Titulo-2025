"""
Servicio para manejo de archivos y almacenamiento local.
"""

import shutil
from pathlib import Path
from typing import List, Optional
from uuid import UUID, uuid4
from fastapi import UploadFile, HTTPException, status

from src.core.config import get_settings
from src.core.logging import get_logger


logger = get_logger(__name__)
settings = get_settings()


class FileService:
    """Servicio para manejar archivos de evidencia de solicitudes."""

    # Tipos de archivos permitidos
    ALLOWED_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.pdf'}
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

    @staticmethod
    def get_evidence_directory(request_id: UUID) -> Path:
        """
        Obtener el directorio de evidencia para una solicitud específica.

        Args:
            request_id: ID de la solicitud de registro

        Returns:
            Path: Ruta al directorio de evidencia
        """
        base_dir = Path(settings.files.upload_directory) if hasattr(settings, 'files') else Path("uploads")
        evidence_dir = base_dir / f"evidence-{request_id}"

        # Crear directorio si no existe
        evidence_dir.mkdir(parents=True, exist_ok=True)

        return evidence_dir

    @staticmethod
    def validate_file(file: UploadFile) -> None:
        """
        Validar que el archivo cumple con los requisitos.

        Args:
            file: Archivo subido

        Raises:
            HTTPException: Si el archivo no es válido
        """
        if not file.filename:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Nombre de archivo requerido"
            )

        # Validar extensión
        file_extension = Path(file.filename).suffix.lower()
        if file_extension not in FileService.ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Tipo de archivo no permitido. Permitidos: {', '.join(FileService.ALLOWED_EXTENSIONS)}"
            )

        # Validar tamaño (si está disponible)
        if hasattr(file, 'size') and file.size and file.size > FileService.MAX_FILE_SIZE:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"Archivo muy grande. Máximo permitido: {FileService.MAX_FILE_SIZE // (1024*1024)}MB"
            )

    @staticmethod
    async def save_evidence_file(
        request_id: UUID,
        file: UploadFile,
        document_type: str
    ) -> str:
        """
        Guardar archivo de evidencia en el directorio correspondiente.

        Args:
            request_id: ID de la solicitud de registro
            file: Archivo a guardar
            document_type: Tipo de documento (id_card_front, id_card_back, utility_bill)

        Returns:
            str: Ruta relativa del archivo guardado
        """
        # Validar archivo
        FileService.validate_file(file)

        # Obtener directorio de evidencia
        evidence_dir = FileService.get_evidence_directory(request_id)

        # Generar nombre único para el archivo
        file_extension = Path(file.filename).suffix.lower()
        unique_filename = f"{document_type}_{uuid4().hex[:8]}{file_extension}"
        file_path = evidence_dir / unique_filename

        try:
            # Guardar archivo
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)

            # Retornar ruta relativa
            relative_path = f"evidence-{request_id}/{unique_filename}"

            logger.info(f"✅ Archivo guardado: {relative_path}")
            return relative_path

        except Exception as e:
            logger.error(f"❌ Error guardando archivo: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error interno guardando archivo"
            )
        finally:
            file.file.close()

    @staticmethod
    async def save_multiple_evidence_files(
        request_id: UUID,
        id_card_front: UploadFile,
        id_card_back: UploadFile,
        utility_bill: UploadFile,
        additional_files: Optional[List[UploadFile]] = None
    ) -> dict:
        """
        Guardar múltiples archivos de evidencia para una solicitud.

        Args:
            request_id: ID de la solicitud de registro
            id_card_front: Foto frontal del carnet
            id_card_back: Foto trasera del carnet
            utility_bill: Foto de cuenta de servicios
            additional_files: Archivos adicionales opcionales

        Returns:
            dict: Diccionario con las rutas de los archivos guardados
        """
        try:
            # Guardar archivos requeridos
            files_saved = {
                'id_card_front_url': await FileService.save_evidence_file(
                    request_id, id_card_front, "id_card_front"
                ),
                'id_card_back_url': await FileService.save_evidence_file(
                    request_id, id_card_back, "id_card_back"
                ),
                'utility_bill_url': await FileService.save_evidence_file(
                    request_id, utility_bill, "utility_bill"
                )
            }

            # Guardar archivos adicionales si existen
            additional_urls = []
            if additional_files:
                for i, additional_file in enumerate(additional_files):
                    additional_url = await FileService.save_evidence_file(
                        request_id, additional_file, f"additional_{i}"
                    )
                    additional_urls.append(additional_url)

            files_saved['additional_files'] = additional_urls

            return files_saved

        except Exception as e:
            # Si hay error, limpiar archivos parcialmente guardados
            FileService.cleanup_evidence_directory(request_id)
            raise e

    @staticmethod
    def cleanup_evidence_directory(request_id: UUID) -> None:
        """
        Limpiar directorio de evidencia en caso de error.

        Args:
            request_id: ID de la solicitud de registro
        """
        try:
            evidence_dir = FileService.get_evidence_directory(request_id)
            if evidence_dir.exists():
                shutil.rmtree(evidence_dir)
                logger.info(f"🧹 Directorio de evidencia limpiado: evidence-{request_id}")
        except Exception as e:
            logger.warning(f"⚠️ Error limpiando directorio: {e}")

    @staticmethod
    def get_file_url(relative_path: str) -> str:
        """
        Generar URL completa para acceder a un archivo.

        Args:
            relative_path: Ruta relativa del archivo

        Returns:
            str: URL completa del archivo
        """
        base_url = getattr(settings, 'files', {}).get('base_url', '/files')
        return f"{base_url}/{relative_path}"

    @staticmethod
    def file_exists(relative_path: str) -> bool:
        """
        Verificar si un archivo existe.

        Args:
            relative_path: Ruta relativa del archivo
 
        Returns:
            bool: True si el archivo existe
        """
        base_dir = Path(settings.files.upload_directory) if hasattr(settings, 'files') else Path("uploads")
        full_path = base_dir / relative_path
        return full_path.exists()

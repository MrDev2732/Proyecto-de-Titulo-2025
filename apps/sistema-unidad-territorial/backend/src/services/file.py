"""
Servicio para manejo de archivos y almacenamiento local.
"""

import hashlib
import shutil
from pathlib import Path
from typing import Dict, List, Optional
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
    ) -> Dict[str, str]:
        """
        Guardar archivo de evidencia en el directorio correspondiente.

        Args:
            request_id: ID de la solicitud de registro
            file: Archivo a guardar
            document_type: Tipo de documento (id_card_front, id_card_back, utility_bill)

        Returns:
            Dict[str, str]: Diccionario con información del archivo guardado:
                - bucket: Nombre del bucket (directorio base)
                - storage_key: Clave de almacenamiento (ruta relativa)
                - sha256: Hash SHA256 del archivo
                - mime_type: Tipo MIME del archivo
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
            # Calcular hash SHA256 mientras se guarda el archivo
            sha256_hash = hashlib.sha256()

            # Guardar archivo y calcular hash
            with open(file_path, "wb") as buffer:
                # Leer y escribir en chunks para manejar archivos grandes
                while chunk := file.file.read(8192):
                    sha256_hash.update(chunk)
                    buffer.write(chunk)

            # Obtener tipo MIME del archivo
            mime_type = file.content_type or FileService._get_mime_type_from_extension(file_extension)

            # Generar ruta relativa (storage_key)
            storage_key = f"evidence-{request_id}/{unique_filename}"

            # Bucket es el directorio base de uploads
            bucket = str(evidence_dir.parent.name) if evidence_dir.parent.name != "." else "uploads"

            file_info = {
                "bucket": bucket,
                "storage_key": storage_key,
                "sha256": sha256_hash.hexdigest(),
                "mime_type": mime_type
            }

            logger.info(f"✅ Archivo guardado: {storage_key} (SHA256: {file_info['sha256'][:16]}...)")
            return file_info

        except Exception as e:
            logger.error(f"❌ Error guardando archivo: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error interno guardando archivo"
            )
        finally:
            file.file.close()
    
    @staticmethod
    def _get_mime_type_from_extension(extension: str) -> str:
        """
        Obtener tipo MIME basado en la extensión del archivo.

        Args:
            extension: Extensión del archivo (incluye el punto)

        Returns:
            str: Tipo MIME correspondiente
        """
        mime_types = {
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.pdf': 'application/pdf'
        }
        return mime_types.get(extension.lower(), 'application/octet-stream')

    @staticmethod
    async def save_multiple_evidence_files(
        request_id: UUID,
        id_card_front: UploadFile,
        id_card_back: UploadFile,
        utility_bill: UploadFile,
        additional_files: Optional[List[UploadFile]] = None
    ) -> Dict[str, any]:
        """
        Guardar múltiples archivos de evidencia para una solicitud.

        Args:
            request_id: ID de la solicitud de registro
            id_card_front: Foto frontal del carnet
            id_card_back: Foto trasera del carnet
            utility_bill: Foto de cuenta de servicios
            additional_files: Archivos adicionales opcionales

        Returns:
            dict: Diccionario con información de los archivos guardados:
                - id_card_front: Dict con bucket, storage_key, sha256, mime_type
                - id_card_back: Dict con bucket, storage_key, sha256, mime_type
                - utility_bill: Dict con bucket, storage_key, sha256, mime_type
                - additional_files: Lista de dicts con información de archivos adicionales
        """
        try:
            # Guardar archivos requeridos
            files_saved = {
                'id_card_front': await FileService.save_evidence_file(
                    request_id, id_card_front, "id_card_front"
                ),
                'id_card_back': await FileService.save_evidence_file(
                    request_id, id_card_back, "id_card_back"
                ),
                'utility_bill': await FileService.save_evidence_file(
                    request_id, utility_bill, "utility_bill"
                )
            }

            # Guardar archivos adicionales si existen
            additional_file_infos = []
            if additional_files:
                for i, additional_file in enumerate(additional_files):
                    file_info = await FileService.save_evidence_file(
                        request_id, additional_file, f"additional_{i}"
                    )
                    additional_file_infos.append(file_info)

            files_saved['additional_files'] = additional_file_infos

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

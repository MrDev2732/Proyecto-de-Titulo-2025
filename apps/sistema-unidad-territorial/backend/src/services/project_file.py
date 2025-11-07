"""
Servicio para manejo de archivos de proyectos.
"""

import hashlib
from pathlib import Path
from typing import List
from uuid import UUID, uuid4
from fastapi import UploadFile, HTTPException, status

from src.core.config import settings
from src.core.logging import get_logger


logger = get_logger(__name__)


class ProjectFileService:
    """Servicio para manejar archivos adjuntos de proyectos."""

    # Tipos de archivos permitidos para proyectos
    ALLOWED_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.pdf', '.doc', '.docx', '.xls', '.xlsx'}
    MAX_FILE_SIZE = 15 * 1024 * 1024  # 15MB

    @staticmethod
    def get_project_directory(project_id: UUID) -> Path:
        """
        Obtener el directorio de archivos para un proyecto específico.

        Args:
            project_id: ID del proyecto

        Returns:
            Path: Ruta al directorio de archivos del proyecto
        """
        base_dir = Path(settings.files.upload_directory) if hasattr(settings, 'files') else Path("uploads")
        project_dir = base_dir / f"projects-{project_id}"

        # Crear directorio si no existe
        project_dir.mkdir(parents=True, exist_ok=True)

        return project_dir

    @staticmethod
    def validate_file(file: UploadFile) -> None:
        """
        Validar que el archivo cumpla con los requisitos.

        Args:
            file: Archivo a validar

        Raises:
            HTTPException: Si el archivo no es válido
        """
        if not file.filename:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El archivo debe tener un nombre"
            )

        # Validar extensión
        file_extension = Path(file.filename).suffix.lower()
        if file_extension not in ProjectFileService.ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Tipo de archivo no permitido. Extensiones permitidas: {', '.join(ProjectFileService.ALLOWED_EXTENSIONS)}"
            )

        # Validar tamaño (si el file tiene size)
        if hasattr(file.file, 'seek') and hasattr(file.file, 'tell'):
            file.file.seek(0, 2)  # Ir al final
            file_size = file.file.tell()
            file.file.seek(0)  # Volver al inicio

            if file_size > ProjectFileService.MAX_FILE_SIZE:
                raise HTTPException(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    detail=f"Archivo muy grande. Tamaño máximo: {ProjectFileService.MAX_FILE_SIZE // (1024*1024)}MB"
                )

    @staticmethod
    def calculate_sha256(file_content: bytes) -> str:
        """
        Calcular el hash SHA256 del contenido del archivo.

        Args:
            file_content: Contenido del archivo en bytes

        Returns:
            str: Hash SHA256 en hexadecimal
        """
        return hashlib.sha256(file_content).hexdigest()

    @staticmethod
    async def save_project_file(
        project_id: UUID,
        file: UploadFile
    ) -> dict:
        """
        Guardar archivo adjunto de un proyecto.

        Args:
            project_id: ID del proyecto
            file: Archivo a guardar

        Returns:
            dict: Información del archivo guardado (storage_key, sha256, mime_type, original_filename)
        """
        # Validar archivo
        ProjectFileService.validate_file(file)

        # Obtener directorio del proyecto
        project_dir = ProjectFileService.get_project_directory(project_id)

        # Generar nombre único para el archivo
        file_extension = Path(file.filename).suffix.lower()
        unique_filename = f"{uuid4().hex[:12]}{file_extension}"
        file_path = project_dir / unique_filename

        try:
            # Leer contenido del archivo
            file_content = await file.read()

            # Calcular hash
            sha256_hash = ProjectFileService.calculate_sha256(file_content)

            # Guardar archivo
            with open(file_path, "wb") as buffer:
                buffer.write(file_content)

            # Determinar tipo MIME
            mime_type = file.content_type or "application/octet-stream"

            # Generar storage_key (ruta relativa)
            storage_key = f"projects-{project_id}/{unique_filename}"

            logger.info(f"✅ Archivo de proyecto guardado: {storage_key}")

            return {
                "bucket": "local",
                "storage_key": storage_key,
                "sha256": sha256_hash,
                "mime_type": mime_type,
                "original_filename": file.filename
            }

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"❌ Error guardando archivo de proyecto: {e}")
            # Intentar limpiar archivo si se creó
            if file_path.exists():
                file_path.unlink()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error interno guardando archivo"
            )
        finally:
            await file.close()

    @staticmethod
    async def save_multiple_project_files(
        project_id: UUID,
        files: List[UploadFile]
    ) -> List[dict]:
        """
        Guardar múltiples archivos para un proyecto.

        Args:
            project_id: ID del proyecto
            files: Lista de archivos a guardar

        Returns:
            List[dict]: Lista con información de archivos guardados
        """
        saved_files = []

        for file in files:
            try:
                file_info = await ProjectFileService.save_project_file(project_id, file)
                saved_files.append(file_info)
            except Exception as e:
                logger.error(f"❌ Error guardando archivo {file.filename}: {e}")
                # Continuar con los demás archivos
                continue

        return saved_files

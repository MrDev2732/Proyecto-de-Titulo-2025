"""
Endpoints para servir archivos estáticos.
"""

from pathlib import Path
from fastapi import APIRouter, HTTPException, status
from fastapi.responses import FileResponse

from src.core.config import settings
from src.core.logging import get_logger

logger = get_logger(__name__)

# Router para endpoints de archivos
router = APIRouter(prefix="/files", tags=["Archivos"])


@router.get(
    "/{file_path:path}",
    summary="Servir archivo estático",
    description="Sirve archivos estáticos desde el directorio de uploads"
)
async def serve_file(file_path: str):
    """
    Servir archivo estático desde el directorio de uploads.

    Args:
        file_path: Ruta relativa del archivo (ej: evidence-123/id_card_front_abc.jpg)
        
    Returns:
        FileResponse: Archivo solicitado
    """
    try:
        # Construir ruta completa
        base_dir = Path(settings.files.upload_directory)
        full_path = base_dir / file_path

        # Verificar que el archivo existe
        if not full_path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Archivo no encontrado"
            )

        # Verificar que está dentro del directorio permitido (seguridad)
        if not str(full_path.resolve()).startswith(str(base_dir.resolve())):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Acceso no permitido"
            )

        # Determinar tipo de contenido basado en extensión
        content_type = "application/octet-stream"
        if full_path.suffix.lower() in ['.jpg', '.jpeg']:
            content_type = "image/jpeg"
        elif full_path.suffix.lower() == '.png':
            content_type = "image/png"
        elif full_path.suffix.lower() == '.pdf':
            content_type = "application/pdf"

        return FileResponse(
            path=str(full_path),
            media_type=content_type,
            filename=full_path.name
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error sirviendo archivo {file_path}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno del servidor"
        )

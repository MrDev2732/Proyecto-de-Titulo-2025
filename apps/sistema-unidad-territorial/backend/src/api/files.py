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
    "/test/{request_id}",
    summary="Probar acceso a archivos de evidencia",
    description="Endpoint de prueba para verificar archivos de una solicitud específica"
)
async def test_evidence_files(request_id: str):
    """
    Probar acceso a archivos de evidencia para una solicitud específica.
    """
    try:
        base_dir = Path(settings.files.upload_directory)
        evidence_dir = base_dir / f"evidence-{request_id}"

        logger.info(f"🔍 Testing evidence directory: {evidence_dir}")
        logger.info(f"🔍 Directory exists: {evidence_dir.exists()}")

        if not evidence_dir.exists():
            return {
                "status": "error",
                "message": f"Evidence directory not found: {evidence_dir}",
                "base_dir": str(base_dir),
                "evidence_dir": str(evidence_dir)
            }

        # Listar archivos en el directorio
        files = list(evidence_dir.glob("*"))
        file_info = []

        for file_path in files:
            if file_path.is_file():
                file_info.append({
                    "name": file_path.name,
                    "size": file_path.stat().st_size,
                    "relative_path": f"evidence-{request_id}/{file_path.name}",
                    "full_path": str(file_path),
                    "url": f"/files/evidence-{request_id}/{file_path.name}"
                })

        return {
            "status": "success",
            "request_id": request_id,
            "base_dir": str(base_dir),
            "evidence_dir": str(evidence_dir),
            "files_found": len(file_info),
            "files": file_info
        }

    except Exception as e:
        logger.error(f"❌ Error testing evidence files: {e}")
        return {
            "status": "error",
            "message": str(e)
        }


@router.get(
    "/debug",
    summary="Debug de configuración de archivos",
    description="Endpoint para debuggear la configuración de archivos"
)
async def debug_files_config():
    """
    Debug de la configuración de archivos.
    """
    try:
        base_dir = Path(settings.files.upload_directory)

        return {
            "status": "success",
            "config": {
                "upload_directory": settings.files.upload_directory,
                "base_url": settings.files.base_url,
                "max_file_size": settings.files.max_file_size,
                "allowed_extensions": settings.files.allowed_extensions
            },
            "paths": {
                "base_dir": str(base_dir),
                "base_dir_absolute": str(base_dir.absolute()),
                "base_dir_exists": base_dir.exists(),
                "working_directory": str(Path.cwd())
            },
            "evidence_directories": [
                str(p) for p in base_dir.glob("evidence-*") if p.is_dir()
            ] if base_dir.exists() else []
        }

    except Exception as e:
        logger.error(f"❌ Error in debug endpoint: {e}")
        return {
            "status": "error",
            "message": str(e)
        }


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
        logger.info(f"🔍 Serving file request: {file_path}")

        # Construir ruta completa
        base_dir = Path(settings.files.upload_directory)
        full_path = base_dir / file_path

        logger.info(f"🔍 Base directory: {base_dir}")
        logger.info(f"🔍 Full path: {full_path}")
        logger.info(f"🔍 File exists: {full_path.exists()}")

        # Verificar que el archivo existe
        if not full_path.exists():
            logger.warning(f"❌ File not found: {full_path}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Archivo no encontrado"
            )

        # Verificar que está dentro del directorio permitido (seguridad)
        if not str(full_path.resolve()).startswith(str(base_dir.resolve())):
            logger.warning(f"🚫 Access denied to: {full_path}")
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

        logger.info(f"✅ Serving file: {full_path} with content-type: {content_type}")
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

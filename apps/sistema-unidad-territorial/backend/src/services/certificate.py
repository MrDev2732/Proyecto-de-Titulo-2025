"""
Servicio para generar certificados de residencia personalizados.
"""

import os
import io
from datetime import datetime
from typing import Optional, Dict, Any
from pathlib import Path

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.colors import black
from PyPDF2 import PdfReader, PdfWriter

from src.core.config import settings
from src.core.logging import get_logger


logger = get_logger(__name__)


class CertificateService:
    """Servicio para generar certificados de residencia personalizados."""

    # Ruta del template PDF
    TEMPLATE_PATH = Path(__file__).parent / "Certificado de Residencia.pdf"

    # Posiciones donde se colocarán los datos (en mm desde la esquina inferior izquierda)
    # Estas coordenadas pueden necesitar ajuste según el diseño exacto del PDF
    FIELD_POSITIONS = {
        'full_name': (70, 161),       # Nombre completo
        'rut': (120, 175),            # RUT
        'address': (50, 190),        # Dirección
        'community_name': (40, 205), # Nombre de la comunidad
        'issue_date': (100, 120),     # Fecha de emisión
        'certificate_number': (450, 200), # Número de certificado
    }

    @staticmethod
    def _ensure_template_exists() -> bool:
        """
        Verificar que el template PDF existe.

        Returns:
            bool: True si el template existe
        """
        if not CertificateService.TEMPLATE_PATH.exists():
            logger.error(f"Template PDF no encontrado en: {CertificateService.TEMPLATE_PATH}")
            return False
        return True

    @staticmethod
    def _create_overlay_pdf(certificate_data: Dict[str, Any]) -> bytes:
        """
        Crear un PDF overlay con los datos del certificado.

        Args:
            certificate_data: Datos para el certificado

        Returns:
            bytes: PDF overlay como bytes
        """
        # Crear buffer en memoria
        buffer = io.BytesIO()

        # Crear canvas con tamaño A4
        c = canvas.Canvas(buffer, pagesize=A4)
        width, height = A4

        # Configurar fuente con tamaño más grande
        c.setFont("Helvetica", 16)
        c.setFillColor(black)

        # Agregar datos en las posiciones especificadas
        for field, position in CertificateService.FIELD_POSITIONS.items():
            if field in certificate_data and certificate_data[field]:
                x_mm, y_mm = position
                # Convertir mm a puntos (1 mm = 2.834645669 puntos)
                x = x_mm * 2.834645669
                y = height - (y_mm * 2.834645669)  # Invertir Y porque PDF usa origen en esquina inferior

                text = str(certificate_data[field])
                c.drawString(x, y, text)
                logger.debug(f"Added {field}: {text} at position ({x}, {y})")

        # Finalizar PDF
        c.save()

        # Obtener bytes del buffer
        buffer.seek(0)
        return buffer.getvalue()

    @staticmethod
    def generate_certificate(
        full_name: str,
        rut: str,
        address: str,
        community_name: str,
        certificate_number: Optional[str] = None,
        issue_date: Optional[datetime] = None
    ) -> bytes:
        """
        Generar certificado de residencia personalizado.

        Args:
            full_name: Nombre completo del residente
            rut: RUT del residente
            address: Dirección del residente
            community_name: Nombre de la comunidad
            certificate_number: Número del certificado (opcional)
            issue_date: Fecha de emisión (opcional, por defecto hoy)

        Returns:
            bytes: PDF del certificado generado

        Raises:
            FileNotFoundError: Si no se encuentra el template
            Exception: Si hay error en la generación
        """
        try:
            # Verificar que el template existe
            if not CertificateService._ensure_template_exists():
                raise FileNotFoundError("Template PDF no encontrado")

            # Preparar datos del certificado
            if issue_date is None:
                issue_date = datetime.now()

            if certificate_number is None:
                # Generar número de certificado basado en timestamp
                certificate_number = f"CR-{issue_date.strftime('%Y%m%d')}-{issue_date.strftime('%H%M%S')}"

            certificate_data = {
                'full_name': full_name,
                'rut': rut,
                'address': address,
                'community_name': community_name,
                'issue_date': issue_date.strftime('%d de %B de %Y'),
                'certificate_number': certificate_number
            }

            logger.info(f"Generating certificate for {full_name} (RUT: {rut})")

            # Leer template PDF
            with open(CertificateService.TEMPLATE_PATH, 'rb') as template_file:
                template_reader = PdfReader(template_file)

                # Crear overlay con los datos
                overlay_bytes = CertificateService._create_overlay_pdf(certificate_data)
                overlay_reader = PdfReader(io.BytesIO(overlay_bytes))

                # Crear writer para el resultado final
                writer = PdfWriter()

                # Combinar template con overlay
                for page_num in range(len(template_reader.pages)):
                    template_page = template_reader.pages[page_num]

                    # Si hay página de overlay correspondiente, combinarla
                    if page_num < len(overlay_reader.pages):
                        overlay_page = overlay_reader.pages[page_num]
                        template_page.merge_page(overlay_page)

                    writer.add_page(template_page)

                # Generar PDF final
                output_buffer = io.BytesIO()
                writer.write(output_buffer)
                output_buffer.seek(0)

                result_bytes = output_buffer.getvalue()

                logger.info(f"✅ Certificate generated successfully for {full_name}")
                logger.debug(f"   📄 Certificate number: {certificate_number}")
                logger.debug(f"   📅 Issue date: {certificate_data['issue_date']}")
                logger.debug(f"   📊 PDF size: {len(result_bytes)} bytes")

                return result_bytes

        except Exception as e:
            logger.error(f"❌ Error generating certificate for {full_name}: {e}")
            raise

    @staticmethod
    def save_certificate_to_file(
        certificate_bytes: bytes,
        filename: str,
        directory: Optional[str] = None
    ) -> str:
        """
        Guardar certificado en archivo.

        Args:
            certificate_bytes: Bytes del certificado PDF
            filename: Nombre del archivo
            directory: Directorio donde guardar (opcional)

        Returns:
            str: Ruta completa del archivo guardado
        """
        try:
            if directory is None:
                directory = settings.files.upload_directory

            # Crear directorio si no existe
            os.makedirs(directory, exist_ok=True)

            # Asegurar extensión .pdf
            if not filename.endswith('.pdf'):
                filename += '.pdf'

            file_path = os.path.join(directory, filename)

            # Guardar archivo
            with open(file_path, 'wb') as f:
                f.write(certificate_bytes)

            logger.info(f"✅ Certificate saved to: {file_path}")
            return file_path

        except Exception as e:
            logger.error(f"❌ Error saving certificate to file: {e}")
            raise

    @staticmethod
    def generate_certificate_for_resident(
        user_data: Dict[str, Any],
        community_data: Dict[str, Any],
        save_to_file: bool = False
    ) -> Dict[str, Any]:
        """
        Generar certificado para un residente específico.

        Args:
            user_data: Datos del usuario (full_name, rut, address)
            community_data: Datos de la comunidad (name)
            save_to_file: Si guardar el certificado en archivo

        Returns:
            Dict con información del certificado generado
        """
        try:
            # Generar certificado
            certificate_bytes = CertificateService.generate_certificate(
                full_name=user_data['full_name'],
                rut=user_data['rut'],
                address=user_data['address'],
                community_name=community_data['name']
            )

            # Generar información del certificado
            issue_date = datetime.now()
            certificate_number = f"CR-{issue_date.strftime('%Y%m%d')}-{issue_date.strftime('%H%M%S')}"

            result = {
                'certificate_bytes': certificate_bytes,
                'certificate_number': certificate_number,
                'issue_date': issue_date,
                'resident_name': user_data['full_name'],
                'resident_rut': user_data['rut'],
                'community_name': community_data['name'],
                'file_size': len(certificate_bytes)
            }

            # Guardar en archivo si se solicita
            if save_to_file:
                filename = f"certificado_residencia_{user_data['rut'].replace('.', '').replace('-', '')}_{issue_date.strftime('%Y%m%d_%H%M%S')}"
                file_path = CertificateService.save_certificate_to_file(
                    certificate_bytes, filename
                )
                result['file_path'] = file_path

            return result

        except Exception as e:
            logger.error(f"❌ Error generating certificate for resident: {e}")
            raise

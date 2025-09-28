from datetime import datetime
import re

import pytz
from sqlalchemy import text, Connection
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.logging import get_logger
from src.database.session import get_transaction_session


logger = get_logger(__name__)

# Chile timezone
CHILE_TZ = pytz.timezone('America/Santiago')


def now_chile() -> datetime:
    """
    Get current datetime in Chile timezone.

    Returns:
        Current datetime with Chile timezone
    """
    return datetime.now(CHILE_TZ)


class DatabaseSetup:
    """Utilities for database configuration."""

    @staticmethod
    def get_extensions_sql() -> list[str]:
        """
        Return SQL commands to create necessary PostgreSQL extensions.

        Returns:
            List of SQL commands to create extensions
        """
        return [
            'CREATE EXTENSION IF NOT EXISTS "uuid-ossp"',
            'CREATE EXTENSION IF NOT EXISTS "btree_gist"', 
            'CREATE EXTENSION IF NOT EXISTS "citext"'
        ]

    @staticmethod
    async def setup_extensions_async(session: AsyncSession) -> None:
        """
        Configure necessary extensions in the database asynchronously.

        Args:
            session: Async database session
        """
        extensions_sql = DatabaseSetup.get_extensions_sql()
        for sql_command in extensions_sql:
            await session.execute(text(sql_command))
        await session.commit()

    @staticmethod
    def setup_extensions_sync(connection: Connection) -> None:
        """
        Configure necessary extensions in the database synchronously.
        Usado por Alembic durante las migraciones.

        Args:
            connection: Database connection
        """
        extensions_sql = DatabaseSetup.get_extensions_sql()
        for sql_command in extensions_sql:
            connection.execute(text(sql_command))
        connection.commit()

    @staticmethod
    async def initialize() -> None:
        """
        Inicializar configuración completa de la base de datos.
        """
        try:
            async with get_transaction_session() as session:
                logger.info("🔧 Configurando extensiones de PostgreSQL...")
                await DatabaseSetup.setup_extensions_async(session)

                logger.info("✅ Configuración de base de datos completada")
        except Exception as e:
            logger.error(f"❌ Error en inicialización de base de datos: {e}")
            raise


class ValidationUtils:
    """Utilidades para validación de datos chilenos."""

    @staticmethod
    def validate_email(email: str) -> tuple[bool, str]:
        """
        Validar formato de email.

        Args:
            email: Email a validar

        Returns:
            tuple[bool, str]: (es_válido, mensaje_error)
        """
        if not email or not email.strip():
            return False, "El email es requerido"

        email = email.strip().lower()

        # Regex básico para email
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'

        if not re.match(email_pattern, email):
            return False, "El formato del email no es válido"

        if len(email) > 254:
            return False, "El email es demasiado largo"

        return True, ""

    @staticmethod
    def validate_full_name(full_name: str) -> tuple[bool, str]:
        """
        Validar nombre completo.

        Args:
            full_name: Nombre completo a validar

        Returns:
            tuple[bool, str]: (es_válido, mensaje_error)
        """
        if not full_name or not full_name.strip():
            return False, "El nombre completo es requerido"

        full_name = full_name.strip()

        if len(full_name) < 2:
            return False, "El nombre debe tener al menos 2 caracteres"

        if len(full_name) > 100:
            return False, "El nombre es demasiado largo (máximo 100 caracteres)"

        # Verificar que contenga al menos dos palabras (nombre y apellido)
        words = full_name.split()
        if len(words) < 2:
            return False, "Debe incluir al menos nombre y apellido"

        # Verificar que solo contenga letras, espacios, acentos y algunos caracteres especiales
        name_pattern = r'^[a-zA-ZáéíóúÁÉÍÓÚñÑüÜ\s\'-]+$'
        if not re.match(name_pattern, full_name):
            return False, "El nombre solo puede contener letras, espacios, acentos y guiones"

        return True, ""

    @staticmethod
    def validate_address(address: str) -> tuple[bool, str]:
        """
        Validar dirección chilena.

        Args:
            address: Dirección a validar

        Returns:
            tuple[bool, str]: (es_válido, mensaje_error)
        """
        if not address or not address.strip():
            return False, "La dirección es requerida"

        address = address.strip()

        if len(address) < 10:
            return False, "La dirección debe tener al menos 10 caracteres"

        if len(address) > 200:
            return False, "La dirección es demasiado larga (máximo 200 caracteres)"

        # Verificar que contenga al menos un número (número de casa/departamento)
        if not re.search(r'\d', address):
            return False, "La dirección debe incluir un número"

        # Verificar caracteres válidos para direcciones chilenas
        address_pattern = r'^[a-zA-ZáéíóúÁÉÍÓÚñÑüÜ0-9\s\.,#\-/°]+$'
        if not re.match(address_pattern, address):
            return False, "La dirección contiene caracteres no válidos"

        return True, ""


class RutChile:
    """Validador de RUT chileno mejorado."""
    
    def __init__(self, rut_input: str):
        """
        Inicializar validador de RUT.

        Args:
            rut_input: RUT a validar (puede incluir puntos y guión)
        """
        self.original_input = rut_input
        self.rut = ""
        self.is_valid = False
        self.error_message = ""

        self._validate_rut()

    def _clean_rut(self, rut_input: str) -> str:
        """
        Limpiar RUT removiendo puntos y espacios, manteniendo solo números y guión.

        Args:
            rut_input: RUT de entrada

        Returns:
            str: RUT limpio
        """
        if not rut_input:
            return ""

        # Convertir a minúsculas y remover espacios
        rut_clean = rut_input.lower().strip()

        # Remover puntos y espacios, mantener números, K y guión
        rut_clean = re.sub(r'[^\d\-k]', '', rut_clean)

        return rut_clean

    def _validate_rut(self) -> None:
        """Validar el RUT completo."""
        try:
            if not self.original_input or not self.original_input.strip():
                self.error_message = "El RUT es requerido"
                return

            # Limpiar RUT
            clean_rut = self._clean_rut(self.original_input)

            if not clean_rut:
                self.error_message = "El RUT no tiene un formato válido"
                return

            # Verificar que tenga guión
            if '-' not in clean_rut:
                self.error_message = "El RUT debe incluir el guión separador"
                return

            # Separar número y dígito verificador
            parts = clean_rut.split('-')
            if len(parts) != 2:
                self.error_message = "El RUT debe tener el formato: número-dígito"
                return

            number_part = parts[0]
            check_digit = parts[1]

            # Validar parte numérica
            if not number_part.isdigit():
                self.error_message = "La parte numérica del RUT solo debe contener dígitos"
                return

            if len(number_part) < 7 or len(number_part) > 8:
                self.error_message = "El RUT debe tener entre 7 y 8 dígitos"
                return

            # Validar dígito verificador
            if len(check_digit) != 1 or (not check_digit.isdigit() and check_digit != 'k'):
                self.error_message = "El dígito verificador debe ser un número del 0-9 o 'k'"
                return

            # Calcular dígito verificador
            calculated_digit = self._calculate_check_digit(number_part)

            # Comparar dígitos
            if str(calculated_digit).lower() == check_digit.lower():
                self.rut = f"{number_part}-{check_digit.upper()}"
                self.is_valid = True
            else:
                self.error_message = f"El dígito verificador no es correcto. Debería ser: {calculated_digit}"

        except Exception as e:
            self.error_message = f"Error al validar RUT: {str(e)}"

    def _calculate_check_digit(self, number: str) -> str:
        """
        Calcular dígito verificador del RUT.

        Args:
            number: Parte numérica del RUT

        Returns:
            str: Dígito verificador calculado
        """
        # Invertir el número para calcular desde la derecha
        reversed_number = number[::-1]

        # Multiplicadores cíclicos
        multipliers = [2, 3, 4, 5, 6, 7]
        total = 0

        for i, digit in enumerate(reversed_number):
            multiplier = multipliers[i % len(multipliers)]
            total += int(digit) * multiplier

        # Calcular resto y dígito verificador
        remainder = total % 11
        check_digit = 11 - remainder

        if check_digit == 11:
            return "0"
        elif check_digit == 10:
            return "K"
        else:
            return str(check_digit)

    @staticmethod
    def validate_rut(rut_input: str) -> tuple[bool, str, str]:
        """
        Método estático para validar RUT.

        Args:
            rut_input: RUT a validar

        Returns:
            tuple[bool, str, str]: (es_válido, rut_formateado, mensaje_error)
        """
        validator = RutChile(rut_input)
        return validator.is_valid, validator.rut, validator.error_message

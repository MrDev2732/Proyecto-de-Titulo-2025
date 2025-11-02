"""
Servicio de cifrado para datos sensibles.

Proporciona funciones para cifrar y descifrar datos sensibles como tokens OAuth.
Utiliza Fernet (AES 128 en modo CBC con HMAC SHA256) para cifrado simétrico seguro.
"""

import base64
import hashlib
from typing import Optional

from cryptography.fernet import Fernet

from src.core.config import settings
from src.core.logging import get_logger

logger = get_logger(__name__)


class EncryptionService:
    """Servicio de cifrado para datos sensibles."""

    def __init__(self):
        """Inicializar el servicio de cifrado."""
        # Derivar una clave de 32 bytes del secret_key usando SHA256
        key_bytes = hashlib.sha256(settings.api.secret_key.encode()).digest()
        # Fernet requiere una clave de 32 bytes codificada en base64
        fernet_key = base64.urlsafe_b64encode(key_bytes)
        self._fernet = Fernet(fernet_key)

    def encrypt(self, data: str) -> bytes:
        """
        Cifrar una cadena de texto.

        Args:
            data: Texto a cifrar

        Returns:
            bytes: Datos cifrados

        Raises:
            Exception: Si ocurre un error durante el cifrado
        """
        try:
            if not data:
                return b''

            encrypted_data = self._fernet.encrypt(data.encode('utf-8'))
            logger.debug("Datos cifrados exitosamente")
            return encrypted_data

        except Exception as e:
            logger.error(f"Error al cifrar datos: {str(e)}")
            raise

    def decrypt(self, encrypted_data: bytes) -> str:
        """
        Descifrar datos cifrados.

        Args:
            encrypted_data: Datos cifrados

        Returns:
            str: Texto descifrado

        Raises:
            Exception: Si ocurre un error durante el descifrado
        """
        try:
            if not encrypted_data:
                return ''

            decrypted_data = self._fernet.decrypt(encrypted_data)
            logger.debug("Datos descifrados exitosamente")
            return decrypted_data.decode('utf-8')

        except Exception as e:
            logger.error(f"Error al descifrar datos: {str(e)}")
            raise

    def encrypt_token(self, token: Optional[str]) -> Optional[bytes]:
        """
        Cifrar un token OAuth.

        Args:
            token: Token a cifrar (puede ser None)

        Returns:
            bytes: Token cifrado o None si el token era None
        """
        if token is None:
            return None

        return self.encrypt(token)

    def decrypt_token(self, encrypted_token: Optional[bytes]) -> Optional[str]:
        """
        Descifrar un token OAuth.

        Args:
            encrypted_token: Token cifrado (puede ser None)

        Returns:
            str: Token descifrado o None si el token cifrado era None
        """
        if encrypted_token is None:
            return None

        return self.decrypt(encrypted_token)


# Instancia global del servicio de cifrado
_encryption_service: Optional[EncryptionService] = None


def get_encryption_service() -> EncryptionService:
    """
    Obtener la instancia del servicio de cifrado (singleton).

    Returns:
        EncryptionService: Instancia del servicio de cifrado
    """
    global _encryption_service

    if _encryption_service is None:
        _encryption_service = EncryptionService()

    return _encryption_service

"""
Triggers SQL para el sistema de autenticación
Funciones y triggers para alertas automáticas y vistas operativas.
"""

from src.database.triggers.auth_triggers import AuthenticationTriggers

__all__ = [
    "AuthenticationTriggers"
]

"""
Triggers SQL para el sistema de autenticación y comunidades
Funciones y triggers para alertas automáticas y vistas operativas.
"""

from src.database.triggers.auth_triggers import AuthenticationTriggers
from src.database.triggers.community_triggers import (
    LIMIT_MODERATORS_FUNCTION,
    DROP_LIMIT_MODERATORS_TRIGGER,
    CREATE_LIMIT_MODERATORS_TRIGGER,
    LOGIN_GATING_VIEW,
    CAN_USER_LOGIN_FUNCTION,
    CAN_OAUTH_LOGIN_FUNCTION,
    DROP_LOGIN_FUNCTIONS,
    DROP_MODERATOR_TRIGGER_FUNCTION
)

__all__ = [
    "AuthenticationTriggers",
    "LIMIT_MODERATORS_FUNCTION",
    "DROP_LIMIT_MODERATORS_TRIGGER",
    "CREATE_LIMIT_MODERATORS_TRIGGER",
    "LOGIN_GATING_VIEW",
    "CAN_USER_LOGIN_FUNCTION",
    "CAN_OAUTH_LOGIN_FUNCTION",
    "DROP_LOGIN_FUNCTIONS",
    "DROP_MODERATOR_TRIGGER_FUNCTION"
]

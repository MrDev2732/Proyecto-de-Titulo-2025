"""
Módulo de servicios de email.
"""

from src.services.email.service import EmailService
from src.services.email.templates import *

__all__ = [
    'EmailService',
    'EmailType',
    'EmailTemplates',
    'WELCOME_EMAIL',
    'REGISTRATION_APPROVED_EMAIL',
    'REGISTRATION_REJECTED_EMAIL',
    'TEST_EMAIL'
]

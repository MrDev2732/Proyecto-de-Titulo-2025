"""add phone and notification preferences

Revision ID: b1a2c3d4e5f6
Revises: a3f9e1b8c4d2
Create Date: 2025-11-19 02:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b1a2c3d4e5f6'
down_revision: Union[str, None] = 'a3f9e1b8c4d2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Agregar columnas a la tabla users
    op.execute("""
        ALTER TABLE sistema_unidad_territorial.users 
        ADD COLUMN IF NOT EXISTS phone_number TEXT,
        ADD COLUMN IF NOT EXISTS email_notifications_enabled BOOLEAN NOT NULL DEFAULT true,
        ADD COLUMN IF NOT EXISTS whatsapp_notifications_enabled BOOLEAN NOT NULL DEFAULT false;
    """)

    # Agregar comentarios a las columnas de users
    op.execute("""
        COMMENT ON COLUMN sistema_unidad_territorial.users.phone_number 
        IS 'User''s phone number for WhatsApp notifications';
    """)
    op.execute("""
        COMMENT ON COLUMN sistema_unidad_territorial.users.email_notifications_enabled 
        IS 'Whether user wants to receive email notifications';
    """)
    op.execute("""
        COMMENT ON COLUMN sistema_unidad_territorial.users.whatsapp_notifications_enabled 
        IS 'Whether user wants to receive WhatsApp notifications';
    """)

    # Agregar columnas a la tabla registration_requests
    op.execute("""
        ALTER TABLE sistema_unidad_territorial.registration_requests 
        ADD COLUMN IF NOT EXISTS phone_number TEXT,
        ADD COLUMN IF NOT EXISTS email_notifications_enabled BOOLEAN NOT NULL DEFAULT true,
        ADD COLUMN IF NOT EXISTS whatsapp_notifications_enabled BOOLEAN NOT NULL DEFAULT false;
    """)

    # Agregar comentarios a las columnas de registration_requests
    op.execute("""
        COMMENT ON COLUMN sistema_unidad_territorial.registration_requests.phone_number 
        IS 'Applicant phone number for WhatsApp notifications';
    """)
    op.execute("""
        COMMENT ON COLUMN sistema_unidad_territorial.registration_requests.email_notifications_enabled 
        IS 'Whether applicant wants email notifications';
    """)
    op.execute("""
        COMMENT ON COLUMN sistema_unidad_territorial.registration_requests.whatsapp_notifications_enabled 
        IS 'Whether applicant wants WhatsApp notifications';
    """)


def downgrade() -> None:
    # Eliminar columnas de registration_requests
    op.execute("""
        ALTER TABLE sistema_unidad_territorial.registration_requests 
        DROP COLUMN IF EXISTS whatsapp_notifications_enabled,
        DROP COLUMN IF EXISTS email_notifications_enabled,
        DROP COLUMN IF EXISTS phone_number;
    """)

    # Eliminar columnas de users
    op.execute("""
        ALTER TABLE sistema_unidad_territorial.users 
        DROP COLUMN IF EXISTS whatsapp_notifications_enabled,
        DROP COLUMN IF EXISTS email_notifications_enabled,
        DROP COLUMN IF EXISTS phone_number;
    """)

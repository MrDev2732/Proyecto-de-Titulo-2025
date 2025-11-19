"""add expired status to reservations

Revision ID: a3f9e1b8c4d2
Revises: de8f2bb2da24
Create Date: 2025-11-19 00:45:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a3f9e1b8c4d2'
down_revision: Union[str, Sequence[str], None] = 'de8f2bb2da24'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Agregar el estado EXPIRED al constraint de la tabla reservations.

    Esto permite que las reservas que ya pasaron su fecha de fin puedan
    ser marcadas automáticamente como expiradas.
    """
    # Eliminar el constraint existente
    op.execute("""
        ALTER TABLE sistema_unidad_territorial.reservations 
        DROP CONSTRAINT IF EXISTS ck_reservation_status;
    """)

    # Crear el nuevo constraint incluyendo EXPIRED
    op.execute("""
        ALTER TABLE sistema_unidad_territorial.reservations 
        ADD CONSTRAINT ck_reservation_status 
        CHECK (status IN ('PENDING', 'CONFIRMED', 'CANCELLED', 'EXPIRED'));
    """)


def downgrade() -> None:
    """
    Revertir el constraint al estado anterior (sin EXPIRED).
    
    NOTA: Si hay reservas con estado EXPIRED, esta migración fallará.
    Deberás actualizar esas reservas manualmente antes de hacer downgrade.
    """
    # Eliminar el constraint actual
    op.execute("""
        ALTER TABLE sistema_unidad_territorial.reservations 
        DROP CONSTRAINT IF EXISTS ck_reservation_status;
    """)

    # Restaurar el constraint sin EXPIRED
    op.execute("""
        ALTER TABLE sistema_unidad_territorial.reservations 
        ADD CONSTRAINT ck_reservation_status 
        CHECK (status IN ('PENDING', 'CONFIRMED', 'CANCELLED'));
    """)

"""fix_project_status_constraint

Revision ID: da976fa03a89
Revises: 4f3e8b2d1a9c
Create Date: 2025-11-07 08:41:00.234727

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'da976fa03a89'
down_revision: Union[str, Sequence[str], None] = '4f3e8b2d1a9c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - Fix project status constraint."""
    # Eliminar el constraint incorrecto
    op.drop_constraint('ck_project_status', 'projects', schema='sistema_unidad_territorial', type_='check')

    # Crear el constraint correcto con los valores string apropiados
    op.create_check_constraint(
        'ck_project_status',
        'projects',
        "status IN ('PENDING', 'IN_PROGRESS', 'COMPLETED', 'REJECTED')",
        schema='sistema_unidad_territorial'
    )


def downgrade() -> None:
    """Downgrade schema - Revert to incorrect constraint (not recommended)."""
    # Eliminar el constraint correcto
    op.drop_constraint('ck_project_status', 'projects', schema='sistema_unidad_territorial', type_='check')

    # Recrear el constraint incorrecto (solo para reversión, no se recomienda usar)
    op.create_check_constraint(
        'ck_project_status',
        'projects',
        "status IN ('ProjectStatus.PENDING', 'ProjectStatus.IN_PROGRESS', 'ProjectStatus.COMPLETED', 'ProjectStatus.REJECTED')",
        schema='sistema_unidad_territorial'
    )

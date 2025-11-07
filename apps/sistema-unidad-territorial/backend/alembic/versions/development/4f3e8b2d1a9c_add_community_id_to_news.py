"""Add community_id to news

Revision ID: 4f3e8b2d1a9c
Revises: 021b6a7948ca
Create Date: 2025-11-07 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '4f3e8b2d1a9c'
down_revision: Union[str, Sequence[str], None] = '021b6a7948ca'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add community_id column to news table."""
    # Agregar la columna community_id a la tabla news
    op.add_column(
        'news',
        sa.Column(
            'community_id',
            postgresql.UUID(as_uuid=True),
            nullable=True,
            comment='Community ID to which this news belongs'
        ),
        schema='sistema_unidad_territorial'
    )

    # Agregar foreign key constraint
    op.create_foreign_key(
        'fk_news_community_id',
        'news',
        'communities',
        ['community_id'],
        ['id'],
        source_schema='sistema_unidad_territorial',
        referent_schema='sistema_unidad_territorial',
        ondelete='CASCADE'
    )

    # Crear índice compuesto para optimizar consultas por comunidad
    op.create_index(
        'idx_news_community_active',
        'news',
        ['community_id', 'visible_from', 'visible_until'],
        unique=False,
        schema='sistema_unidad_territorial'
    )

    # Nota: Antes de hacer la columna NOT NULL, deberás ejecutar un script
    # para asignar community_id a las noticias existentes.
    # Luego puedes hacer:
    # op.alter_column('news', 'community_id', nullable=False, schema='sistema_unidad_territorial')


def downgrade() -> None:
    """Remove community_id column from news table."""
    # Eliminar índice
    op.drop_index(
        'idx_news_community_active',
        table_name='news',
        schema='sistema_unidad_territorial'
    )

    # Eliminar foreign key
    op.drop_constraint(
        'fk_news_community_id',
        'news',
        type_='foreignkey',
        schema='sistema_unidad_territorial'
    )

    # Eliminar columna
    op.drop_column(
        'news',
        'community_id',
        schema='sistema_unidad_territorial'
    )


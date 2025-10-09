"""Add password reset tokens table

Revision ID: a71c9f3e52bd
Revises: 
Create Date: 2025-10-01 14:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'a71c9f3e52bd'
down_revision: Union[str, Sequence[str], None] = '84d203af796a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create password_reset_tokens table."""
    # Crear tabla password_reset_tokens
    op.create_table(
        'password_reset_tokens',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('code', sa.String(length=6), nullable=False),
        sa.Column('token', sa.String(length=64), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('used_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_used', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('ip_address', postgresql.INET(), nullable=True),
        sa.Column('user_agent', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        # Foreign key constraint
        sa.ForeignKeyConstraint(['user_id'], ['sistema_unidad_territorial.users.id'], ondelete='CASCADE'),
        # Primary key
        sa.PrimaryKeyConstraint('id'),
        # Unique constraints
        sa.UniqueConstraint('code'),
        sa.UniqueConstraint('token'),
        # Schema
        schema='sistema_unidad_territorial'
    )
    # Crear índices
    op.create_index(
        'idx_password_reset_code', 
        'password_reset_tokens', 
        ['code'], 
        unique=False, 
        schema='sistema_unidad_territorial'
    )
    op.create_index(
        'idx_password_reset_token', 
        'password_reset_tokens', 
        ['token'], 
        unique=False, 
        schema='sistema_unidad_territorial'
    )
    op.create_index(
        'idx_password_reset_expires', 
        'password_reset_tokens', 
        ['expires_at'], 
        unique=False, 
        schema='sistema_unidad_territorial'
    )
    op.create_index(
        'idx_password_reset_user', 
        'password_reset_tokens', 
        ['user_id', 'created_at'], 
        unique=False, 
        schema='sistema_unidad_territorial'
    )
    op.create_index(
        'idx_password_reset_validation', 
        'password_reset_tokens', 
        ['code', 'is_used', 'expires_at'], 
        unique=False, 
        schema='sistema_unidad_territorial'
    )


def downgrade() -> None:
    """Drop password_reset_tokens table."""

    # Eliminar índices
    op.drop_index('idx_password_reset_validation', table_name='password_reset_tokens', schema='sistema_unidad_territorial')
    op.drop_index('idx_password_reset_user', table_name='password_reset_tokens', schema='sistema_unidad_territorial')
    op.drop_index('idx_password_reset_expires', table_name='password_reset_tokens', schema='sistema_unidad_territorial')
    op.drop_index('idx_password_reset_token', table_name='password_reset_tokens', schema='sistema_unidad_territorial')
    op.drop_index('idx_password_reset_code', table_name='password_reset_tokens', schema='sistema_unidad_territorial')

    # Eliminar tabla
    op.drop_table('password_reset_tokens', schema='sistema_unidad_territorial')

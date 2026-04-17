"""add id to amistades and fix enum values

Revision ID: a1b2c3d4e5f6
Revises: 6e5f12242cd2
Create Date: 2026-04-17 17:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = '6e5f12242cd2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema: drop and recreate amistades with an integer id primary key."""
    op.execute("DROP TABLE IF EXISTS amistades CASCADE")
    op.execute("DROP TYPE IF EXISTS estado_amistad_enum CASCADE")

    estado_amistad_enum = postgresql.ENUM('PENDIENTE', 'ACEPTADA', 'RECHAZADA', name='estado_amistad_enum')
    estado_amistad_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        'amistades',
        sa.Column('id', sa.Integer(), sa.Identity(always=False), nullable=False),
        sa.Column('user_1', sa.String(length=50), nullable=False),
        sa.Column('user_2', sa.String(length=50), nullable=False),
        sa.Column(
            'estado',
            postgresql.ENUM('PENDIENTE', 'ACEPTADA', 'RECHAZADA', name='estado_amistad_enum', create_type=False),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(['user_1'], ['usuarios.username'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_2'], ['usuarios.username'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )


def downgrade() -> None:
    """Downgrade schema: restore the original composite-primary-key amistades table."""
    op.drop_table('amistades')
    op.execute("DROP TYPE IF EXISTS estado_amistad_enum CASCADE")

    estado_amistad_enum = postgresql.ENUM('PENDIENTE', 'ACEPTADA', 'RECHAZADA', name='estado_amistad_enum')
    estado_amistad_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        'amistades',
        sa.Column('user_1', sa.String(length=50), nullable=False),
        sa.Column('user_2', sa.String(length=50), nullable=False),
        sa.Column(
            'estado',
            sa.Enum('PENDIENTE', 'ACEPTADA', 'RECHAZADA', name='estado_amistad_enum', create_type=False),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(['user_1'], ['usuarios.username'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_2'], ['usuarios.username'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('user_1', 'user_2'),
    )

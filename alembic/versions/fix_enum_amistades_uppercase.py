"""fix enum amistades uppercase

Revision ID: fix_enum_amistades_uppercase
Revises: add_id_amistades_v2
Create Date: 2026-04-17 19:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = 'fix_enum_amistades_uppercase'
down_revision = 'add_id_amistades_v2'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("DROP TABLE IF EXISTS amistades CASCADE")
    op.execute("DROP TYPE IF EXISTS estado_amistad_enum CASCADE")

    estado_amistad_enum = postgresql.ENUM('PENDIENTE', 'ACEPTADA', 'RECHAZADA', name='estado_amistad_enum')
    estado_amistad_enum.create(op.get_bind(), checkfirst=True)

    op.create_table('amistades',
        sa.Column('id', sa.Integer(), sa.Identity(always=False), nullable=False),
        sa.Column('user_1', sa.String(length=50), nullable=False),
        sa.Column('user_2', sa.String(length=50), nullable=False),
        sa.Column('estado', postgresql.ENUM('PENDIENTE', 'ACEPTADA', 'RECHAZADA', name='estado_amistad_enum', create_type=False), nullable=False),
        sa.ForeignKeyConstraint(['user_1'], ['usuarios.username'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_2'], ['usuarios.username'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade():
    op.drop_table('amistades')
    op.execute("DROP TYPE IF EXISTS estado_amistad_enum CASCADE")

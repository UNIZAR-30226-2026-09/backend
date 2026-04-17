"""add id amistades v2

Revision ID: add_id_amistades_v2
Revises: 6e5f12242cd2
Create Date: 2024-04-17 18:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'add_id_amistades_v2'
down_revision = '6e5f12242cd2'
branch_labels = None
depends_on = None

def upgrade():
    # 1. Limpieza total por si quedan restos
    op.execute("DROP TABLE IF EXISTS amistades CASCADE")
    op.execute("DROP TYPE IF EXISTS estado_amistad_enum CASCADE")
    
    # 2. Recreamos el tipo ENUM con valores en minúscula (deben coincidir con EstadoAmistad.value)
    estado_amistad_enum = postgresql.ENUM('pendiente', 'aceptada', 'rechazada', name='estado_amistad_enum')
    estado_amistad_enum.create(op.get_bind())

    # 3. Creamos la tabla con ID SERIAL
    op.create_table('amistades',
        sa.Column('id', sa.Integer(), sa.Identity(always=False), nullable=False),
        sa.Column('user_1', sa.String(length=50), nullable=False),
        sa.Column('user_2', sa.String(length=50), nullable=False),
        sa.Column('estado', sa.Enum('pendiente', 'aceptada', 'rechazada', name='estado_amistad_enum', create_type=False), nullable=False),
        sa.ForeignKeyConstraint(['user_1'], ['usuarios.username'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_2'], ['usuarios.username'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

def downgrade():
    op.drop_table('amistades')
    op.execute("DROP TYPE IF EXISTS estado_amistad_enum CASCADE")

"""rename_stats_comarca_region

Revision ID: a20eebff6477
Revises: f37f12c57e10
Create Date: 2026-05-02 23:47:36.530415

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'a20eebff6477'
down_revision: Union[str, Sequence[str], None] = 'f37f12c57e10'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Añadimos las nuevas columnas con defaults seguros
    op.add_column('estadisticas', sa.Column('num_comarcas_conquistadas', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('estadisticas', sa.Column('conquistas_por_comarca', sa.JSON(), nullable=False, server_default='{}'))

    # Migramos los datos existentes
    op.execute("UPDATE estadisticas SET num_comarcas_conquistadas = num_regiones_conquistadas")
    op.execute("UPDATE estadisticas SET conquistas_por_comarca = conquistas_por_region")

    # num_regiones_conquistadas ahora cuenta regiones completas — reseteamos a 0
    op.execute("UPDATE estadisticas SET num_regiones_conquistadas = 0")

    # Eliminamos las columnas antiguas
    op.drop_column('estadisticas', 'num_continentes_conquistados')
    op.drop_column('estadisticas', 'conquistas_por_region')


def downgrade() -> None:
    op.add_column('estadisticas', sa.Column('conquistas_por_region', postgresql.JSON(astext_type=sa.Text()), server_default=sa.text("'{}'::json"), autoincrement=False, nullable=False))
    op.add_column('estadisticas', sa.Column('num_continentes_conquistados', sa.INTEGER(), server_default='0', autoincrement=False, nullable=False))

    op.execute("UPDATE estadisticas SET conquistas_por_region = conquistas_por_comarca")
    op.execute("UPDATE estadisticas SET num_regiones_conquistadas = num_comarcas_conquistadas")

    op.drop_column('estadisticas', 'conquistas_por_comarca')
    op.drop_column('estadisticas', 'num_comarcas_conquistadas')

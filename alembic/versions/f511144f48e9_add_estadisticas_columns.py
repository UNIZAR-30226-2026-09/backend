"""add_estadisticas_columns

Revision ID: f511144f48e9
Revises: fix_enum_amistades_uppercase
Create Date: 2026-04-22 12:44:42.916100

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f511144f48e9'
down_revision: Union[str, Sequence[str], None] = 'fix_enum_amistades_uppercase'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    conn = op.get_bind()

    existing_cols = {row[0] for row in conn.execute(
        sa.text("SELECT column_name FROM information_schema.columns WHERE table_name = 'estadisticas'")
    )}
    existing_constraints = {row[0] for row in conn.execute(
        sa.text("SELECT conname FROM pg_constraint WHERE conrelid = 'estadisticas'::regclass")
    )}

    if 'num_regiones_conquistadas' not in existing_cols:
        op.add_column('estadisticas', sa.Column('num_regiones_conquistadas', sa.Integer(), nullable=False, server_default='0'))
    if 'check_regiones_positivas' not in existing_constraints:
        op.create_check_constraint('check_regiones_positivas', 'estadisticas', 'num_regiones_conquistadas >= 0')

    if 'num_soldados_matados' not in existing_cols:
        op.add_column('estadisticas', sa.Column('num_soldados_matados', sa.Integer(), nullable=False, server_default='0'))
    if 'check_tropas_positivas' not in existing_constraints:
        op.create_check_constraint('check_tropas_positivas', 'estadisticas', 'num_soldados_matados >= 0')

    if 'conquistas_por_region' not in existing_cols:
        op.add_column('estadisticas', sa.Column('conquistas_por_region', sa.JSON(), nullable=False, server_default='{}'))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('estadisticas', 'conquistas_por_region')
    op.drop_constraint('check_tropas_positivas', 'estadisticas')
    op.drop_column('estadisticas', 'num_soldados_matados')
    op.drop_constraint('check_regiones_positivas', 'estadisticas')
    op.drop_column('estadisticas', 'num_regiones_conquistadas')

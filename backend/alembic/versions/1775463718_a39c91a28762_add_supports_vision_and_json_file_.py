# DATA-LOSSY DOWNGRADE
# Downgrade converts file_path from JSONB array back to VARCHAR,
# keeping only the first element. Multi-image submissions will lose
# all paths except the first.

"""add_supports_vision_and_json_file_path

Revision ID: a39c91a28762
Revises: 6bafd916a45d
Create Date: 2026-04-06 18:01:58.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a39c91a28762'
down_revision: Union[str, Sequence[str], None] = '6bafd916a45d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'model_configs',
        sa.Column('supports_vision', sa.Boolean(), nullable=False, server_default='false'),
    )

    op.execute(
        "ALTER TABLE submissions "
        "ALTER COLUMN file_path TYPE JSONB "
        "USING jsonb_build_array(file_path)"
    )


def downgrade() -> None:
    op.execute(
        "ALTER TABLE submissions "
        "ALTER COLUMN file_path TYPE VARCHAR "
        "USING file_path->>0"
    )

    op.drop_column('model_configs', 'supports_vision')

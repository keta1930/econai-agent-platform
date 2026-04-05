"""replace_suggestion_with_feedback

Revision ID: a1b2c3d4e5f6
Revises: 6bafd916a45d
Create Date: 2026-04-06 08:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "6bafd916a45d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_column("submissions", "suggestion")
    op.add_column(
        "submissions",
        sa.Column("feedback", sa.JSON(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("submissions", "feedback")
    op.add_column(
        "submissions",
        sa.Column("suggestion", sa.Text(), nullable=True),
    )

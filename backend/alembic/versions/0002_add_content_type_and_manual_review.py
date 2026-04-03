"""add content_type and manual_review status

Revision ID: 0002_content_type
Revises: 0001_multitenancy
Create Date: 2026-04-03
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0002_content_type"
down_revision: Union[str, None] = "0001_multitenancy"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add content_type column with default for existing rows
    op.add_column(
        "submissions",
        sa.Column("content_type", sa.String(), nullable=False, server_default="file"),
    )

    # Drop old status CHECK and recreate with manual_review
    op.drop_constraint("ck_submissions_status", "submissions", type_="check")
    op.execute(
        "ALTER TABLE submissions ADD CONSTRAINT ck_submissions_status "
        "CHECK (status IN ('pending', 'grading', 'completed', 'failed', 'manual_review'))"
    )

    # Add content_type CHECK
    op.execute(
        "ALTER TABLE submissions ADD CONSTRAINT ck_submissions_content_type "
        "CHECK (content_type IN ('text', 'file', 'image'))"
    )


def downgrade() -> None:
    op.drop_constraint("ck_submissions_content_type", "submissions", type_="check")

    op.drop_constraint("ck_submissions_status", "submissions", type_="check")
    op.execute(
        "ALTER TABLE submissions ADD CONSTRAINT ck_submissions_status "
        "CHECK (status IN ('pending', 'grading', 'completed', 'failed'))"
    )

    op.drop_column("submissions", "content_type")

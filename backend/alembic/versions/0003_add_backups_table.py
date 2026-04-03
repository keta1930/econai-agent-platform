"""add backups table

Revision ID: 0003_backups
Revises: 0002_content_type
Create Date: 2026-04-03
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0003_backups"
down_revision: Union[str, None] = "0002_content_type"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "backups",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("admin_id", sa.Integer(), nullable=False),
        sa.Column("display_name", sa.String(), nullable=False),
        sa.Column("object_key", sa.String(), nullable=False),
        sa.Column("size", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["admin_id"],
            ["users.id"],
            name=op.f("fk_backups_admin_id_users"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_backups")),
        sa.UniqueConstraint("object_key", name=op.f("uq_backups_object_key")),
    )


def downgrade() -> None:
    op.drop_table("backups")

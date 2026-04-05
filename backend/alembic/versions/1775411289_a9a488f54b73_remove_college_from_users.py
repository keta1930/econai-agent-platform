"""remove_college_from_users

Revision ID: a9a488f54b73
Revises: 0fb1d73aaf55
Create Date: 2026-04-06 01:48:09.833127

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a9a488f54b73'
down_revision: Union[str, Sequence[str], None] = '0fb1d73aaf55'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.drop_constraint('ck_users_college', 'users', type_='check')
    op.drop_column('users', 'college')


def downgrade() -> None:
    """Downgrade schema."""
    op.add_column('users', sa.Column('college', sa.VARCHAR(), autoincrement=False, nullable=True))
    op.create_check_constraint(
        'ck_users_college', 'users',
        "college IS NULL OR college IN ('lingnan', 'physics')",
    )

"""add post_all_clear

Revision ID: 9c1a4e38fd52
Revises: 628236fca495
Create Date: 2026-04-21 16:25:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "9c1a4e38fd52"
down_revision: Union[str, Sequence[str], None] = "628236fca495"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add post_all_clear column; existing rows default to True."""
    op.add_column(
        "repo_configs",
        sa.Column("post_all_clear", sa.Boolean(), nullable=True, server_default=sa.true()),
    )


def downgrade() -> None:
    op.drop_column("repo_configs", "post_all_clear")

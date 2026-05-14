"""add memo to inspection result

Revision ID: e2dfe32c5350
Revises: f6601c6de141
Create Date: 2026-05-14 17:34:00.481887

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e2dfe32c5350'
down_revision: Union[str, Sequence[str], None] = 'f6601c6de141'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "inspection_result",
        sa.Column("memo", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("inspection_result", "memo")

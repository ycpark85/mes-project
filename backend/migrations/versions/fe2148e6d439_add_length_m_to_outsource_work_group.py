"""add length_m to outsource work group

Revision ID: fe2148e6d439
Revises: 28c5157a03b5
Create Date: 2026-04-23 11:02:40.558386

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'fe2148e6d439'
down_revision: Union[str, Sequence[str], None] = '28c5157a03b5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "outsource_work_group",
        sa.Column("length_m", sa.Numeric(18, 2), nullable=True),
    )

def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("outsource_work_group", "length_m")
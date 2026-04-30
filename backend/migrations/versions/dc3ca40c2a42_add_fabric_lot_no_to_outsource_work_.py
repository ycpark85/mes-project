"""add fabric_lot_no to outsource_work_group

Revision ID: dc3ca40c2a42
Revises: f281ce31f7bc
Create Date: 2026-04-30 10:14:12.766776

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'dc3ca40c2a42'
down_revision: Union[str, Sequence[str], None] = 'f281ce31f7bc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "outsource_work_group",
        sa.Column("fabric_lot_no", sa.String(length=100), nullable=True),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("outsource_work_group", "fabric_lot_no")

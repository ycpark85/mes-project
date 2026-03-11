"""add one in_progress per lot constraint

Revision ID: 35e5bd18d677
Revises: 97821b941323
Create Date: 2026-02-09 14:50:26.643022

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '35e5bd18d677'
down_revision: Union[str, Sequence[str], None] = '97821b941323'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_index(
        "ux_lot_step__one_in_progress_per_lot",
        "lot_step",
        ["lot_id"],
        unique=True,
        postgresql_where=sa.text("status = 'IN_PROGRESS'"),
    )



def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        "ux_lot_step__one_in_progress_per_lot",
        table_name="lot_step",
    )
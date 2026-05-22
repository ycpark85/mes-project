"""add is printed product snapshot to shipment coa

Revision ID: ba6f7cdb0fd3
Revises: d28fa97d3247
Create Date: 2026-05-22 11:11:43.089437

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ba6f7cdb0fd3'
down_revision: Union[str, Sequence[str], None] = 'd28fa97d3247'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "shipment_coa",
        sa.Column(
            "is_printed_product_snapshot",
            sa.Boolean(),
            nullable=True,
        ),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("shipment_coa", "is_printed_product_snapshot")

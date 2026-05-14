"""add initial stock movement type

Revision ID: f6601c6de141
Revises: 41a256ced8b2
Create Date: 2026-05-13 16:53:28.296076

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f6601c6de141'
down_revision: Union[str, Sequence[str], None] = '41a256ced8b2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.drop_constraint(
        "ck_product_inventory_movement__movement_type",
        "product_inventory_movement",
        type_="check",
    )

    op.create_check_constraint(
        "ck_product_inventory_movement__movement_type",
        "product_inventory_movement",
        "movement_type IN ('INITIAL_STOCK','INSPECTION_IN','SHIP_OUT','ADJUST_IN','ADJUST_OUT')",
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint(
        "ck_product_inventory_movement__movement_type",
        "product_inventory_movement",
        type_="check",
    )

    op.create_check_constraint(
        "ck_product_inventory_movement__movement_type",
        "product_inventory_movement",
        "movement_type IN ('INSPECTION_IN','SHIP_OUT','ADJUST_IN','ADJUST_OUT')",
    )

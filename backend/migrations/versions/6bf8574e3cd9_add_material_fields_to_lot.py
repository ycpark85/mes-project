"""add material fields to lot

Revision ID: 6bf8574e3cd9
Revises: be7f8b6b21a5
Create Date: 2026-03-24 13:55:12.103165

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6bf8574e3cd9'
down_revision: Union[str, Sequence[str], None] = 'be7f8b6b21a5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "lot",
        sa.Column("material_lot_no", sa.String(length=100), nullable=True),
    )
    op.add_column(
        "lot",
        sa.Column("material_used_qty", sa.Numeric(18, 3), nullable=True),
    )
    op.add_column(
        "lot",
        sa.Column("material_uom", sa.String(length=20), nullable=True),
    )

    op.create_index(
        "ix_lot__material_lot_no",
        "lot",
        ["material_lot_no"],
        unique=False,
    )

    op.create_check_constraint(
        "ck_lot__material_used_qty_gt_0",
        "lot",
        "material_used_qty IS NULL OR material_used_qty > 0",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_lot__material_used_qty_gt_0",
        "lot",
        type_="check",
    )

    op.drop_index(
        "ix_lot__material_lot_no",
        table_name="lot",
    )

    op.drop_column("lot", "material_uom")
    op.drop_column("lot", "material_used_qty")
    op.drop_column("lot", "material_lot_no")

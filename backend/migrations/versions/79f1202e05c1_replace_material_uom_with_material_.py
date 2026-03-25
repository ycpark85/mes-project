"""replace material_uom with material_sheet_count on lot

Revision ID: 79f1202e05c1
Revises: 6bf8574e3cd9
Create Date: 2026-03-25 11:53:14.255156

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '79f1202e05c1'
down_revision: Union[str, Sequence[str], None] = '6bf8574e3cd9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "lot",
        sa.Column("material_sheet_count", sa.BigInteger(), nullable=True),
    )

    op.create_check_constraint(
        "ck_lot__material_sheet_count_gt_0",
        "lot",
        "material_sheet_count IS NULL OR material_sheet_count > 0",
    )

    op.drop_column("lot", "material_uom")


def downgrade() -> None:
    """Downgrade schema."""
    op.add_column(
        "lot",
        sa.Column("material_sheet_count", sa.BigInteger(), nullable=True),
    )

    op.create_check_constraint(
        "ck_lot__material_sheet_count_gt_0",
        "lot",
        "material_sheet_count IS NULL OR material_sheet_count > 0",
    )

    op.drop_column("lot", "material_uom")

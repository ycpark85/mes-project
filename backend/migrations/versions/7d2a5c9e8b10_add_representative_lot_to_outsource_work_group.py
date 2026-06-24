"""add representative lot to outsource work group

Revision ID: 7d2a5c9e8b10
Revises: 2b7c9f4d1a62
Create Date: 2026-06-23 15:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "7d2a5c9e8b10"
down_revision: Union[str, Sequence[str], None] = "2b7c9f4d1a62"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "outsource_work_group",
        sa.Column("representative_lot_id", sa.BigInteger(), nullable=True),
    )
    op.create_index(
        "ix_outsource_work_group__representative_lot_id",
        "outsource_work_group",
        ["representative_lot_id"],
    )
    op.create_foreign_key(
        "fk_outsource_work_group__representative_lot_id__lot",
        "outsource_work_group",
        "lot",
        ["representative_lot_id"],
        ["lot_id"],
        ondelete="RESTRICT",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_outsource_work_group__representative_lot_id__lot",
        "outsource_work_group",
        type_="foreignkey",
    )
    op.drop_index(
        "ix_outsource_work_group__representative_lot_id",
        table_name="outsource_work_group",
    )
    op.drop_column("outsource_work_group", "representative_lot_id")

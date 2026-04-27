"""add bohyun work group result columns

Revision ID: d2104f9becd5
Revises: fe2148e6d439
Create Date: 2026-04-27 16:35:33.321518

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd2104f9becd5'
down_revision: Union[str, Sequence[str], None] = 'fe2148e6d439'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "outsource_work_group",
        sa.Column("status", sa.String(length=30), nullable=True),
    )
    op.add_column(
        "outsource_work_group",
        sa.Column("vendor_received_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "outsource_work_group",
        sa.Column("work_done_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "outsource_work_group",
        sa.Column("shipped_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "outsource_work_group",
        sa.Column("work_done_sheet_qty", sa.BigInteger(), nullable=True),
    )
    op.add_column(
        "outsource_work_group",
        sa.Column("outsource_processing_fee", sa.Numeric(18, 2), nullable=True),
    )
    op.add_column(
        "outsource_work_group",
        sa.Column("work_done_remark", sa.Text(), nullable=True),
    )

    op.add_column(
        "outsource_work_group_item",
        sa.Column("actual_output_qty", sa.BigInteger(), nullable=True),
    )

    op.create_check_constraint(
        "ck_outsource_work_group__status",
        "outsource_work_group",
        "status IS NULL OR status IN ('VENDOR_RECEIVED', 'WORK_DONE', 'SHIPPED')",
    )
    op.create_check_constraint(
        "ck_outsource_work_group__work_done_sheet_qty_ge_0",
        "outsource_work_group",
        "work_done_sheet_qty IS NULL OR work_done_sheet_qty >= 0",
    )
    op.create_check_constraint(
        "ck_outsource_work_group__outsource_processing_fee_ge_0",
        "outsource_work_group",
        "outsource_processing_fee IS NULL OR outsource_processing_fee >= 0",
    )
    op.create_check_constraint(
        "ck_outsource_work_group_item__actual_output_qty_ge_0",
        "outsource_work_group_item",
        "actual_output_qty IS NULL OR actual_output_qty >= 0",
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint(
        "ck_outsource_work_group_item__actual_output_qty_ge_0",
        "outsource_work_group_item",
        type_="check",
    )
    op.drop_constraint(
        "ck_outsource_work_group__outsource_processing_fee_ge_0",
        "outsource_work_group",
        type_="check",
    )
    op.drop_constraint(
        "ck_outsource_work_group__work_done_sheet_qty_ge_0",
        "outsource_work_group",
        type_="check",
    )
    op.drop_constraint(
        "ck_outsource_work_group__status",
        "outsource_work_group",
        type_="check",
    )

    op.drop_column("outsource_work_group_item", "actual_output_qty")

    op.drop_column("outsource_work_group", "work_done_remark")
    op.drop_column("outsource_work_group", "outsource_processing_fee")
    op.drop_column("outsource_work_group", "work_done_sheet_qty")
    op.drop_column("outsource_work_group", "shipped_at")
    op.drop_column("outsource_work_group", "work_done_at")
    op.drop_column("outsource_work_group", "vendor_received_at")
    op.drop_column("outsource_work_group", "status")

"""add outsource processing costs

Revision ID: 2b7c9f4d1a62
Revises: c4f1a2b3d5e6
Create Date: 2026-06-22 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "2b7c9f4d1a62"
down_revision: Union[str, Sequence[str], None] = "c4f1a2b3d5e6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "outsource_processing_cost_group",
        sa.Column("outsource_processing_cost_group_id", sa.BigInteger(), nullable=False),
        sa.Column("cost_group_no", sa.String(length=40), nullable=False),
        sa.Column("settlement_month", sa.Date(), nullable=False),
        sa.Column("process_type", sa.String(length=20), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("standard_amount", sa.Numeric(18, 2), nullable=True),
        sa.Column("standard_memo", sa.Text(), nullable=True),
        sa.Column("actual_amount", sa.Numeric(18, 2), nullable=True),
        sa.Column("actual_billing_month", sa.Date(), nullable=True),
        sa.Column("actual_memo", sa.Text(), nullable=True),
        sa.Column("remark", sa.Text(), nullable=True),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("canceled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "process_type IN ('CUT','PRINT','DIECUT')",
            name="ck_outsource_processing_cost_group__process_type",
        ),
        sa.CheckConstraint(
            "status IN ('DRAFT','CLOSED','CANCELED')",
            name="ck_outsource_processing_cost_group__status",
        ),
        sa.CheckConstraint(
            "standard_amount IS NULL OR standard_amount >= 0",
            name="ck_outsource_processing_cost_group__standard_amount_ge_0",
        ),
        sa.CheckConstraint(
            "actual_amount IS NULL OR actual_amount >= 0",
            name="ck_outsource_processing_cost_group__actual_amount_ge_0",
        ),
        sa.PrimaryKeyConstraint("outsource_processing_cost_group_id"),
        sa.UniqueConstraint("cost_group_no"),
    )
    op.create_index(
        "ix_outsource_processing_cost_group__cost_group_no",
        "outsource_processing_cost_group",
        ["cost_group_no"],
    )
    op.create_index(
        "ix_outsource_processing_cost_group__process_status",
        "outsource_processing_cost_group",
        ["process_type", "status"],
    )
    op.create_index(
        "ix_outsource_processing_cost_group__settlement_month",
        "outsource_processing_cost_group",
        ["settlement_month"],
    )

    op.create_table(
        "outsource_processing_cost_work_group",
        sa.Column("outsource_processing_cost_work_group_id", sa.BigInteger(), nullable=False),
        sa.Column("outsource_processing_cost_group_id", sa.BigInteger(), nullable=False),
        sa.Column("outsource_work_group_id", sa.BigInteger(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["outsource_processing_cost_group_id"],
            ["outsource_processing_cost_group.outsource_processing_cost_group_id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["outsource_work_group_id"],
            ["outsource_work_group.outsource_work_group_id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("outsource_processing_cost_work_group_id"),
        sa.UniqueConstraint(
            "outsource_processing_cost_group_id",
            "outsource_work_group_id",
            name="uq_outsource_processing_cost_work_group__group_work_group",
        ),
    )
    op.create_index(
        "ix_outsource_processing_cost_work_group__cost_group_id",
        "outsource_processing_cost_work_group",
        ["outsource_processing_cost_group_id"],
    )
    op.create_index(
        "ix_outsource_processing_cost_work_group__work_group_id",
        "outsource_processing_cost_work_group",
        ["outsource_work_group_id"],
    )

    op.create_table(
        "outsource_processing_cost_allocation",
        sa.Column("outsource_processing_cost_allocation_id", sa.BigInteger(), nullable=False),
        sa.Column("outsource_processing_cost_group_id", sa.BigInteger(), nullable=False),
        sa.Column("outsource_work_group_id", sa.BigInteger(), nullable=True),
        sa.Column("outsource_work_group_item_id", sa.BigInteger(), nullable=True),
        sa.Column("lot_id", sa.BigInteger(), nullable=False),
        sa.Column("lot_no_snapshot", sa.String(length=20), nullable=False),
        sa.Column("product_code_snapshot", sa.String(length=60), nullable=True),
        sa.Column("product_name_snapshot", sa.String(length=200), nullable=True),
        sa.Column("product_spec_snapshot", sa.String(length=100), nullable=True),
        sa.Column("panel_width_mm_snapshot", sa.Integer(), nullable=True),
        sa.Column("panel_length_mm_snapshot", sa.Integer(), nullable=True),
        sa.Column("cuts_per_sheet_snapshot", sa.Integer(), nullable=True),
        sa.Column("sheet_qty_snapshot", sa.BigInteger(), nullable=True),
        sa.Column("instruction_output_qty_snapshot", sa.BigInteger(), nullable=True),
        sa.Column("basis_type", sa.String(length=20), nullable=False),
        sa.Column("basis_value", sa.Numeric(20, 6), nullable=False),
        sa.Column("basis_area_sqm", sa.Numeric(20, 6), nullable=True),
        sa.Column("allocation_ratio", sa.Numeric(18, 8), nullable=False),
        sa.Column("standard_allocated_amount", sa.Numeric(18, 2), nullable=True),
        sa.Column("actual_allocated_amount", sa.Numeric(18, 2), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "basis_type IN ('QUANTITY','AREA')",
            name="ck_outsource_processing_cost_allocation__basis_type",
        ),
        sa.CheckConstraint(
            "basis_value >= 0",
            name="ck_outsource_processing_cost_allocation__basis_value_ge_0",
        ),
        sa.CheckConstraint(
            "allocation_ratio >= 0",
            name="ck_outsource_processing_cost_allocation__allocation_ratio_ge_0",
        ),
        sa.CheckConstraint(
            "standard_allocated_amount IS NULL OR standard_allocated_amount >= 0",
            name="ck_outsource_processing_cost_allocation__standard_amount_ge_0",
        ),
        sa.CheckConstraint(
            "actual_allocated_amount IS NULL OR actual_allocated_amount >= 0",
            name="ck_outsource_processing_cost_allocation__actual_amount_ge_0",
        ),
        sa.ForeignKeyConstraint(
            ["outsource_processing_cost_group_id"],
            ["outsource_processing_cost_group.outsource_processing_cost_group_id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["outsource_work_group_id"],
            ["outsource_work_group.outsource_work_group_id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["outsource_work_group_item_id"],
            ["outsource_work_group_item.outsource_work_group_item_id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(["lot_id"], ["lot.lot_id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("outsource_processing_cost_allocation_id"),
    )
    op.create_index(
        "ix_outsource_processing_cost_allocation__cost_group_id",
        "outsource_processing_cost_allocation",
        ["outsource_processing_cost_group_id"],
    )
    op.create_index(
        "ix_outsource_processing_cost_allocation__lot_id",
        "outsource_processing_cost_allocation",
        ["lot_id"],
    )
    op.create_index(
        "ix_outsource_processing_cost_allocation__work_group_item_id",
        "outsource_processing_cost_allocation",
        ["outsource_work_group_item_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_outsource_processing_cost_allocation__work_group_item_id",
        table_name="outsource_processing_cost_allocation",
    )
    op.drop_index(
        "ix_outsource_processing_cost_allocation__lot_id",
        table_name="outsource_processing_cost_allocation",
    )
    op.drop_index(
        "ix_outsource_processing_cost_allocation__cost_group_id",
        table_name="outsource_processing_cost_allocation",
    )
    op.drop_table("outsource_processing_cost_allocation")

    op.drop_index(
        "ix_outsource_processing_cost_work_group__work_group_id",
        table_name="outsource_processing_cost_work_group",
    )
    op.drop_index(
        "ix_outsource_processing_cost_work_group__cost_group_id",
        table_name="outsource_processing_cost_work_group",
    )
    op.drop_table("outsource_processing_cost_work_group")

    op.drop_index(
        "ix_outsource_processing_cost_group__settlement_month",
        table_name="outsource_processing_cost_group",
    )
    op.drop_index(
        "ix_outsource_processing_cost_group__process_status",
        table_name="outsource_processing_cost_group",
    )
    op.drop_index(
        "ix_outsource_processing_cost_group__cost_group_no",
        table_name="outsource_processing_cost_group",
    )
    op.drop_table("outsource_processing_cost_group")

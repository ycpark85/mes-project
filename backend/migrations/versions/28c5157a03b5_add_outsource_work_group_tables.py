"""add outsource work group tables

Revision ID: 28c5157a03b5
Revises: 0c9eba3551b6
Create Date: 2026-04-22 17:33:40.923000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "28c5157a03b5"
down_revision: Union[str, Sequence[str], None] = "0c9eba3551b6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "outsource_work_group",
        sa.Column("outsource_work_group_id", sa.BigInteger(), nullable=False),
        sa.Column("outsource_work_instruction_id", sa.BigInteger(), nullable=False),
        sa.Column("group_seq", sa.Integer(), nullable=False),
        sa.Column("process_type", sa.String(length=20), nullable=False),
        sa.Column("is_bundle", sa.Boolean(), nullable=False),
        sa.Column("sheet_qty", sa.BigInteger(), nullable=False),
        sa.Column("sheet_cut_count", sa.Integer(), nullable=False),
        sa.Column("remark", sa.Text(), nullable=True),
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
            name="ck_outsource_work_group__process_type",
        ),
        sa.CheckConstraint(
            "sheet_cut_count > 0",
            name="ck_outsource_work_group__sheet_cut_count_gt_0",
        ),
        sa.CheckConstraint(
            "sheet_qty > 0",
            name="ck_outsource_work_group__sheet_qty_gt_0",
        ),
        sa.ForeignKeyConstraint(
            ["outsource_work_instruction_id"],
            ["outsource_work_instruction.outsource_work_instruction_id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("outsource_work_group_id"),
    )
    op.create_index(
        "ix_outsource_work_group__instruction_id",
        "outsource_work_group",
        ["outsource_work_instruction_id"],
        unique=False,
    )
    op.create_index(
        "ix_outsource_work_group__process_type",
        "outsource_work_group",
        ["process_type"],
        unique=False,
    )

    op.create_table(
        "outsource_purchase_order_group",
        sa.Column("outsource_purchase_order_group_id", sa.BigInteger(), nullable=False),
        sa.Column("outsource_purchase_order_id", sa.BigInteger(), nullable=False),
        sa.Column("outsource_work_group_id", sa.BigInteger(), nullable=False),
        sa.Column("item_seq", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=True),
        sa.Column("vendor_received_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("work_done_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("shipped_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("remark", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "status IS NULL OR status IN ('VENDOR_RECEIVED','WORK_DONE','SHIPPED')",
            name="ck_outsource_purchase_order_group__status",
        ),
        sa.ForeignKeyConstraint(
            ["outsource_purchase_order_id"],
            ["outsource_purchase_order.outsource_purchase_order_id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["outsource_work_group_id"],
            ["outsource_work_group.outsource_work_group_id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("outsource_purchase_order_group_id"),
    )
    op.create_index(
        "ix_outsource_purchase_order_group__purchase_order_id",
        "outsource_purchase_order_group",
        ["outsource_purchase_order_id"],
        unique=False,
    )
    op.create_index(
        "ix_outsource_purchase_order_group__status",
        "outsource_purchase_order_group",
        ["status"],
        unique=False,
    )
    op.create_index(
        "ix_outsource_purchase_order_group__work_group_id",
        "outsource_purchase_order_group",
        ["outsource_work_group_id"],
        unique=False,
    )

    op.create_table(
        "outsource_work_group_item",
        sa.Column("outsource_work_group_item_id", sa.BigInteger(), nullable=False),
        sa.Column("outsource_work_group_id", sa.BigInteger(), nullable=False),
        sa.Column("lot_id", sa.BigInteger(), nullable=False),
        sa.Column("cuts_per_sheet", sa.Integer(), nullable=False),
        sa.Column("expected_output_qty", sa.BigInteger(), nullable=True),
        sa.Column("remark", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "cuts_per_sheet > 0",
            name="ck_outsource_work_group_item__cuts_per_sheet_gt_0",
        ),
        sa.CheckConstraint(
            "expected_output_qty IS NULL OR expected_output_qty >= 0",
            name="ck_outsource_work_group_item__expected_output_qty_ge_0",
        ),
        sa.ForeignKeyConstraint(
            ["lot_id"],
            ["lot.lot_id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["outsource_work_group_id"],
            ["outsource_work_group.outsource_work_group_id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("outsource_work_group_item_id"),
    )
    op.create_index(
        "ix_outsource_work_group_item__lot_id",
        "outsource_work_group_item",
        ["lot_id"],
        unique=False,
    )
    op.create_index(
        "ix_outsource_work_group_item__work_group_id",
        "outsource_work_group_item",
        ["outsource_work_group_id"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        "ix_outsource_work_group_item__work_group_id",
        table_name="outsource_work_group_item",
    )
    op.drop_index(
        "ix_outsource_work_group_item__lot_id",
        table_name="outsource_work_group_item",
    )
    op.drop_table("outsource_work_group_item")

    op.drop_index(
        "ix_outsource_purchase_order_group__work_group_id",
        table_name="outsource_purchase_order_group",
    )
    op.drop_index(
        "ix_outsource_purchase_order_group__status",
        table_name="outsource_purchase_order_group",
    )
    op.drop_index(
        "ix_outsource_purchase_order_group__purchase_order_id",
        table_name="outsource_purchase_order_group",
    )
    op.drop_table("outsource_purchase_order_group")

    op.drop_index(
        "ix_outsource_work_group__process_type",
        table_name="outsource_work_group",
    )
    op.drop_index(
        "ix_outsource_work_group__instruction_id",
        table_name="outsource_work_group",
    )
    op.drop_table("outsource_work_group")
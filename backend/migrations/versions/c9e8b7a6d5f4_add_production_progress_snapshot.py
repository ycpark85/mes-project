"""add production progress snapshot

Revision ID: c9e8b7a6d5f4
Revises: b8e1c4d9a732
Create Date: 2026-06-25 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c9e8b7a6d5f4"
down_revision: Union[str, Sequence[str], None] = "b8e1c4d9a732"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "production_progress_snapshot",
        sa.Column("production_progress_snapshot_id", sa.BigInteger(), nullable=False),
        sa.Column("order_line_id", sa.BigInteger(), nullable=False),
        sa.Column("order_no", sa.String(length=40), nullable=False),
        sa.Column("line_no", sa.Integer(), nullable=False),
        sa.Column("due_date", sa.Date(), nullable=False),
        sa.Column("partner_id", sa.BigInteger(), nullable=False),
        sa.Column("partner_name", sa.String(length=200), nullable=False),
        sa.Column("product_id", sa.BigInteger(), nullable=False),
        sa.Column("product_code", sa.String(length=80), nullable=False),
        sa.Column("product_name", sa.String(length=200), nullable=False),
        sa.Column("order_qty", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("available_inventory_qty", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("production_qty", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("work_type", sa.String(length=20), nullable=False),
        sa.Column("current_process", sa.String(length=40), nullable=False),
        sa.Column("current_process_order", sa.Integer(), nullable=False),
        sa.Column("progress_rate", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("lot_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("target_lot_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("completed_lot_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("lot_nos_text", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "current_process IN ('LOT_CREATED','OUTSOURCE_ORDERED','DIECUT_RECEIVED','OUTSOURCE_DONE','INSPECTION_WAITING','INSPECTION_IN_PROGRESS','COMPLETED')",
            name="ck_production_progress_snapshot__current_process",
        ),
        sa.CheckConstraint(
            "current_process_order BETWEEN 1 AND 7",
            name="ck_production_progress_snapshot__process_order",
        ),
        sa.CheckConstraint(
            "order_qty >= 0 AND available_inventory_qty >= 0 AND production_qty >= 0",
            name="ck_production_progress_snapshot__quantities_nonnegative",
        ),
        sa.CheckConstraint(
            "progress_rate BETWEEN 0 AND 100",
            name="ck_production_progress_snapshot__progress_rate",
        ),
        sa.CheckConstraint(
            "status IN ('IN_PROGRESS','COMPLETED')",
            name="ck_production_progress_snapshot__status",
        ),
        sa.CheckConstraint(
            "work_type IN ('BASIC','REWORK')",
            name="ck_production_progress_snapshot__work_type",
        ),
        sa.ForeignKeyConstraint(
            ["order_line_id"],
            ["order_line.order_line_id"],
            name="fk_production_progress_snapshot__order_line_id",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["partner_id"],
            ["partner.partner_id"],
            name="fk_production_progress_snapshot__partner_id",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["product_id"],
            ["product.product_id"],
            name="fk_production_progress_snapshot__product_id",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint(
            "production_progress_snapshot_id",
            name="pk_production_progress_snapshot",
        ),
        sa.UniqueConstraint(
            "order_line_id",
            name="uq_production_progress_snapshot__order_line_id",
        ),
    )
    op.create_index(
        "ix_production_progress_snapshot__process_status",
        "production_progress_snapshot",
        ["current_process", "status"],
    )
    op.create_index(
        "ix_production_progress_snapshot__product_status_due",
        "production_progress_snapshot",
        ["product_id", "status", "due_date"],
    )
    op.create_index(
        "ix_production_progress_snapshot__partner_status_due",
        "production_progress_snapshot",
        ["partner_id", "status", "due_date"],
    )
    op.create_index(
        "ix_production_progress_snapshot__status_due",
        "production_progress_snapshot",
        ["status", "due_date"],
    )
    op.create_index(
        "ix_production_progress_snapshot__updated_at",
        "production_progress_snapshot",
        ["updated_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_production_progress_snapshot__updated_at",
        table_name="production_progress_snapshot",
    )
    op.drop_index(
        "ix_production_progress_snapshot__status_due",
        table_name="production_progress_snapshot",
    )
    op.drop_index(
        "ix_production_progress_snapshot__partner_status_due",
        table_name="production_progress_snapshot",
    )
    op.drop_index(
        "ix_production_progress_snapshot__product_status_due",
        table_name="production_progress_snapshot",
    )
    op.drop_index(
        "ix_production_progress_snapshot__process_status",
        table_name="production_progress_snapshot",
    )
    op.drop_table("production_progress_snapshot")

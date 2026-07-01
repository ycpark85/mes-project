"""add outsource work cancel state

Revision ID: 6c2e9f4a1b7d
Revises: 4b6d2e7f9a10
Create Date: 2026-06-29 14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "6c2e9f4a1b7d"
down_revision: Union[str, Sequence[str], None] = "4b6d2e7f9a10"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "outsource_work_instruction_item",
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
    )
    op.drop_constraint(
        "uq_outsource_work_instruction_item__process_type__lot_id",
        "outsource_work_instruction_item",
        type_="unique",
    )
    op.create_index(
        "uq_owi_item__active_process_lot",
        "outsource_work_instruction_item",
        ["process_type", "lot_id"],
        unique=True,
        postgresql_where=sa.text("is_active = true"),
    )

    op.drop_constraint(
        "ck_outsource_work_group__status",
        "outsource_work_group",
        type_="check",
    )
    op.create_check_constraint(
        "ck_outsource_work_group__status",
        "outsource_work_group",
        "status IS NULL OR status IN ('VENDOR_RECEIVED','WORK_DONE','SHIPPED','CANCELED')",
    )
    op.add_column(
        "outsource_work_group",
        sa.Column("canceled_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "outsource_work_group",
        sa.Column("canceled_reason", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("outsource_work_group", "canceled_reason")
    op.drop_column("outsource_work_group", "canceled_at")
    op.drop_constraint(
        "ck_outsource_work_group__status",
        "outsource_work_group",
        type_="check",
    )
    op.create_check_constraint(
        "ck_outsource_work_group__status",
        "outsource_work_group",
        "status IS NULL OR status IN ('VENDOR_RECEIVED','WORK_DONE','SHIPPED')",
    )
    op.drop_index(
        "uq_owi_item__active_process_lot",
        table_name="outsource_work_instruction_item",
    )
    op.create_unique_constraint(
        "uq_outsource_work_instruction_item__process_type__lot_id",
        "outsource_work_instruction_item",
        ["process_type", "lot_id"],
    )
    op.drop_column("outsource_work_instruction_item", "is_active")

"""add outsource raw material allocation

Revision ID: 4b6d2e7f9a10
Revises: 3f5c8a1b9d20
Create Date: 2026-06-29 10:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "4b6d2e7f9a10"
down_revision: Union[str, Sequence[str], None] = "3f5c8a1b9d20"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "outsource_work_group_raw_material_allocation",
        sa.Column(
            "outsource_work_group_raw_material_allocation_id",
            sa.BigInteger(),
            nullable=False,
        ),
        sa.Column("outsource_work_group_id", sa.BigInteger(), nullable=False),
        sa.Column("raw_material_id", sa.BigInteger(), nullable=False),
        sa.Column("raw_material_location_id", sa.BigInteger(), nullable=False),
        sa.Column("raw_material_inventory_lot_id", sa.BigInteger(), nullable=True),
        sa.Column("raw_material_inventory_movement_id", sa.BigInteger(), nullable=True),
        sa.Column("lot_no", sa.String(length=100), nullable=False),
        sa.Column("qty", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column("unit_cost_snapshot", sa.Numeric(precision=18, scale=4), nullable=True),
        sa.Column("amount_snapshot", sa.Numeric(precision=18, scale=2), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("memo", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "amount_snapshot IS NULL OR amount_snapshot >= 0",
            name="ck_owg_rm_alloc__amount_snapshot_ge_0",
        ),
        sa.CheckConstraint(
            "qty > 0",
            name="ck_owg_rm_alloc__qty_gt_0",
        ),
        sa.CheckConstraint(
            "status IN ('CONSUMED','REVERSED')",
            name="ck_owg_rm_alloc__status",
        ),
        sa.ForeignKeyConstraint(
            ["outsource_work_group_id"],
            ["outsource_work_group.outsource_work_group_id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["raw_material_id"],
            ["raw_material.raw_material_id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["raw_material_location_id"],
            ["raw_material_location.raw_material_location_id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["raw_material_inventory_lot_id"],
            ["raw_material_inventory_lot.raw_material_inventory_lot_id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["raw_material_inventory_movement_id"],
            ["raw_material_inventory_movement.raw_material_inventory_movement_id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("outsource_work_group_raw_material_allocation_id"),
    )
    op.create_index(
        "ix_owg_raw_material_allocation__inventory_lot_id",
        "outsource_work_group_raw_material_allocation",
        ["raw_material_inventory_lot_id"],
        unique=False,
    )
    op.create_index(
        "ix_owg_raw_material_allocation__location_id",
        "outsource_work_group_raw_material_allocation",
        ["raw_material_location_id"],
        unique=False,
    )
    op.create_index(
        "ix_owg_raw_material_allocation__material_id",
        "outsource_work_group_raw_material_allocation",
        ["raw_material_id"],
        unique=False,
    )
    op.create_index(
        "ix_owg_raw_material_allocation__movement_id",
        "outsource_work_group_raw_material_allocation",
        ["raw_material_inventory_movement_id"],
        unique=False,
    )
    op.create_index(
        "ix_owg_raw_material_allocation__work_group_id",
        "outsource_work_group_raw_material_allocation",
        ["outsource_work_group_id"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        "ix_owg_raw_material_allocation__work_group_id",
        table_name="outsource_work_group_raw_material_allocation",
    )
    op.drop_index(
        "ix_owg_raw_material_allocation__movement_id",
        table_name="outsource_work_group_raw_material_allocation",
    )
    op.drop_index(
        "ix_owg_raw_material_allocation__material_id",
        table_name="outsource_work_group_raw_material_allocation",
    )
    op.drop_index(
        "ix_owg_raw_material_allocation__location_id",
        table_name="outsource_work_group_raw_material_allocation",
    )
    op.drop_index(
        "ix_owg_raw_material_allocation__inventory_lot_id",
        table_name="outsource_work_group_raw_material_allocation",
    )
    op.drop_table("outsource_work_group_raw_material_allocation")

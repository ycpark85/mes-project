"""add self-use sheet locations and outsource work source

Revision ID: 5cf6b7c8d9e0
Revises: 4bf5a6b7c8d9
Create Date: 2026-07-16 18:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "5cf6b7c8d9e0"
down_revision: Union[str, Sequence[str], None] = "4bf5a6b7c8d9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "self_use_sheet_inventory_balance",
        sa.Column("self_use_sheet_inventory_balance_id", sa.BigInteger(), primary_key=True),
        sa.Column("self_use_sheet_inventory_lot_id", sa.BigInteger(), nullable=False),
        sa.Column("raw_material_location_id", sa.BigInteger(), nullable=False),
        sa.Column("current_qty", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("current_qty >= 0", name="ck_self_use_sheet_inv_balance__qty_ge_0"),
        sa.ForeignKeyConstraint(
            ["self_use_sheet_inventory_lot_id"],
            ["self_use_sheet_inventory_lot.self_use_sheet_inventory_lot_id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["raw_material_location_id"],
            ["raw_material_location.raw_material_location_id"],
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint(
            "self_use_sheet_inventory_lot_id",
            "raw_material_location_id",
            name="uq_self_use_sheet_inv_balance__lot_location",
        ),
    )
    op.create_index("ix_self_use_sheet_inv_balance__lot_id", "self_use_sheet_inventory_balance", ["self_use_sheet_inventory_lot_id"])
    op.create_index("ix_self_use_sheet_inv_balance__location_id", "self_use_sheet_inventory_balance", ["raw_material_location_id"])

    op.add_column("self_use_sheet_inventory_movement", sa.Column("raw_material_location_id", sa.BigInteger(), nullable=True))
    op.add_column("self_use_sheet_inventory_movement", sa.Column("counterpart_location_id", sa.BigInteger(), nullable=True))
    op.add_column("self_use_sheet_inventory_movement", sa.Column("location_balance_after", sa.BigInteger(), nullable=True))
    op.add_column("self_use_sheet_inventory_movement", sa.Column("source_type", sa.String(length=60), nullable=True))
    op.add_column("self_use_sheet_inventory_movement", sa.Column("source_id", sa.BigInteger(), nullable=True))
    op.add_column("self_use_sheet_inventory_movement", sa.Column("transfer_key", sa.String(length=80), nullable=True))

    op.execute(
        """
        INSERT INTO self_use_sheet_inventory_balance (
            self_use_sheet_inventory_lot_id, raw_material_location_id, current_qty
        )
        SELECT lot.self_use_sheet_inventory_lot_id, source.source_location_id, lot.current_qty
        FROM self_use_sheet_inventory_lot lot
        JOIN LATERAL (
            SELECT allocation.source_location_id
            FROM self_use_sheet_raw_material_allocation allocation
            WHERE allocation.self_use_sheet_job_id = lot.self_use_sheet_job_id
            ORDER BY allocation.self_use_sheet_raw_material_allocation_id
            LIMIT 1
        ) source ON TRUE
        """
    )
    op.execute(
        """
        UPDATE self_use_sheet_inventory_movement movement
        SET raw_material_location_id = balance.raw_material_location_id,
            location_balance_after = movement.balance_after
        FROM self_use_sheet_inventory_balance balance
        WHERE balance.self_use_sheet_inventory_lot_id = movement.self_use_sheet_inventory_lot_id
        """
    )
    op.alter_column("self_use_sheet_inventory_movement", "raw_material_location_id", nullable=False)
    op.alter_column("self_use_sheet_inventory_movement", "location_balance_after", nullable=False)
    op.create_foreign_key(
        "fk_self_use_sheet_inv_movement__location_id",
        "self_use_sheet_inventory_movement",
        "raw_material_location",
        ["raw_material_location_id"],
        ["raw_material_location_id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_self_use_sheet_inv_movement__counterpart_location_id",
        "self_use_sheet_inventory_movement",
        "raw_material_location",
        ["counterpart_location_id"],
        ["raw_material_location_id"],
        ondelete="RESTRICT",
    )
    op.create_index("ix_self_use_sheet_inv_movement__location_id", "self_use_sheet_inventory_movement", ["raw_material_location_id"])
    op.drop_constraint("ck_self_use_sheet_inv_movement__movement_type", "self_use_sheet_inventory_movement", type_="check")
    op.create_check_constraint(
        "ck_self_use_sheet_inv_movement__movement_type",
        "self_use_sheet_inventory_movement",
        "movement_type IN ('PRODUCE_IN','USE_OUT','USE_REVERSE','CANCEL_OUT','TRANSFER_OUT','TRANSFER_IN','WORK_USE_OUT','WORK_USE_REVERSE')",
    )

    op.add_column("outsource_work_group", sa.Column("input_source_type", sa.String(length=30), nullable=False, server_default="RAW_MATERIAL"))
    op.add_column("outsource_work_group", sa.Column("cut_skipped_reason", sa.String(length=40), nullable=True))
    op.create_check_constraint(
        "ck_outsource_work_group__input_source_type",
        "outsource_work_group",
        "input_source_type IN ('RAW_MATERIAL','SELF_USE_SHEET')",
    )
    op.create_check_constraint(
        "ck_outsource_work_group__self_use_sheet_skip_reason",
        "outsource_work_group",
        "input_source_type <> 'SELF_USE_SHEET' OR cut_skipped_reason = 'SELF_USE_SHEET'",
    )

    op.drop_constraint("ck_outsource_work_instruction__process_type", "outsource_work_instruction", type_="check")
    op.create_check_constraint(
        "ck_outsource_work_instruction__process_type",
        "outsource_work_instruction",
        "process_type IN ('CUT','PRINT','DIECUT')",
    )

    op.create_table(
        "outsource_work_group_self_use_sheet_allocation",
        sa.Column("outsource_work_group_self_use_sheet_allocation_id", sa.BigInteger(), primary_key=True),
        sa.Column("outsource_work_group_id", sa.BigInteger(), nullable=False),
        sa.Column("self_use_sheet_inventory_lot_id", sa.BigInteger(), nullable=False),
        sa.Column("source_location_id", sa.BigInteger(), nullable=False),
        sa.Column("sheet_lot_no", sa.String(length=50), nullable=False),
        sa.Column("qty", sa.BigInteger(), nullable=False),
        sa.Column("unit_cost_snapshot", sa.Numeric(18, 4), nullable=False),
        sa.Column("amount_snapshot", sa.Numeric(18, 2), nullable=False),
        sa.Column("inventory_movement_id", sa.BigInteger(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="CONSUMED"),
        sa.Column("memo", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("qty > 0", name="ck_owg_self_use_sheet_alloc__qty_gt_0"),
        sa.CheckConstraint("unit_cost_snapshot >= 0", name="ck_owg_self_use_sheet_alloc__unit_cost_ge_0"),
        sa.CheckConstraint("amount_snapshot >= 0", name="ck_owg_self_use_sheet_alloc__amount_ge_0"),
        sa.CheckConstraint("status IN ('CONSUMED','REVERSED')", name="ck_owg_self_use_sheet_alloc__status"),
        sa.ForeignKeyConstraint(["outsource_work_group_id"], ["outsource_work_group.outsource_work_group_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["self_use_sheet_inventory_lot_id"], ["self_use_sheet_inventory_lot.self_use_sheet_inventory_lot_id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["source_location_id"], ["raw_material_location.raw_material_location_id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["inventory_movement_id"], ["self_use_sheet_inventory_movement.self_use_sheet_inventory_movement_id"], ondelete="SET NULL"),
    )
    op.create_index("ix_owg_self_use_sheet_alloc__group_id", "outsource_work_group_self_use_sheet_allocation", ["outsource_work_group_id"])
    op.create_index("ix_owg_self_use_sheet_alloc__lot_id", "outsource_work_group_self_use_sheet_allocation", ["self_use_sheet_inventory_lot_id"])
    op.create_index("ix_owg_self_use_sheet_alloc__movement_id", "outsource_work_group_self_use_sheet_allocation", ["inventory_movement_id"])

    op.create_table(
        "outsource_work_group_self_use_sheet_source_snapshot",
        sa.Column("outsource_work_group_self_use_sheet_source_snapshot_id", sa.BigInteger(), primary_key=True),
        sa.Column("self_use_sheet_allocation_id", sa.BigInteger(), nullable=False),
        sa.Column("self_use_sheet_raw_material_allocation_id", sa.BigInteger(), nullable=True),
        sa.Column("original_inventory_lot_id", sa.BigInteger(), nullable=True),
        sa.Column("raw_material_id", sa.BigInteger(), nullable=False),
        sa.Column("raw_material_code_snapshot", sa.String(length=100), nullable=False),
        sa.Column("raw_material_name_snapshot", sa.String(length=200), nullable=False),
        sa.Column("raw_material_lot_no_snapshot", sa.String(length=100), nullable=False),
        sa.Column("source_location_name_snapshot", sa.String(length=200), nullable=False),
        sa.Column("actual_consumed_qty_snapshot", sa.Numeric(18, 2), nullable=False),
        sa.Column("unit_cost_snapshot", sa.Numeric(18, 4), nullable=False),
        sa.Column("amount_snapshot", sa.Numeric(18, 2), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["self_use_sheet_allocation_id"], ["outsource_work_group_self_use_sheet_allocation.outsource_work_group_self_use_sheet_allocation_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["self_use_sheet_raw_material_allocation_id"], ["self_use_sheet_raw_material_allocation.self_use_sheet_raw_material_allocation_id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["original_inventory_lot_id"], ["raw_material_inventory_lot.raw_material_inventory_lot_id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["raw_material_id"], ["raw_material.raw_material_id"], ondelete="RESTRICT"),
    )
    op.create_index("ix_owg_self_use_sheet_source__allocation_id", "outsource_work_group_self_use_sheet_source_snapshot", ["self_use_sheet_allocation_id"])
    op.create_index("ix_owg_self_use_sheet_source__raw_lot_id", "outsource_work_group_self_use_sheet_source_snapshot", ["original_inventory_lot_id"])


def downgrade() -> None:
    op.drop_index("ix_owg_self_use_sheet_source__raw_lot_id", table_name="outsource_work_group_self_use_sheet_source_snapshot")
    op.drop_index("ix_owg_self_use_sheet_source__allocation_id", table_name="outsource_work_group_self_use_sheet_source_snapshot")
    op.drop_table("outsource_work_group_self_use_sheet_source_snapshot")
    op.drop_index("ix_owg_self_use_sheet_alloc__movement_id", table_name="outsource_work_group_self_use_sheet_allocation")
    op.drop_index("ix_owg_self_use_sheet_alloc__lot_id", table_name="outsource_work_group_self_use_sheet_allocation")
    op.drop_index("ix_owg_self_use_sheet_alloc__group_id", table_name="outsource_work_group_self_use_sheet_allocation")
    op.drop_table("outsource_work_group_self_use_sheet_allocation")

    op.drop_constraint("ck_outsource_work_instruction__process_type", "outsource_work_instruction", type_="check")
    op.create_check_constraint(
        "ck_outsource_work_instruction__process_type",
        "outsource_work_instruction",
        "process_type IN ('CUT','PRINT')",
    )
    op.drop_constraint("ck_outsource_work_group__self_use_sheet_skip_reason", "outsource_work_group", type_="check")
    op.drop_constraint("ck_outsource_work_group__input_source_type", "outsource_work_group", type_="check")
    op.drop_column("outsource_work_group", "cut_skipped_reason")
    op.drop_column("outsource_work_group", "input_source_type")

    op.drop_constraint("ck_self_use_sheet_inv_movement__movement_type", "self_use_sheet_inventory_movement", type_="check")
    op.create_check_constraint(
        "ck_self_use_sheet_inv_movement__movement_type",
        "self_use_sheet_inventory_movement",
        "movement_type IN ('PRODUCE_IN','USE_OUT','USE_REVERSE','CANCEL_OUT')",
    )
    op.drop_index("ix_self_use_sheet_inv_movement__location_id", table_name="self_use_sheet_inventory_movement")
    op.drop_constraint("fk_self_use_sheet_inv_movement__counterpart_location_id", "self_use_sheet_inventory_movement", type_="foreignkey")
    op.drop_constraint("fk_self_use_sheet_inv_movement__location_id", "self_use_sheet_inventory_movement", type_="foreignkey")
    op.drop_column("self_use_sheet_inventory_movement", "transfer_key")
    op.drop_column("self_use_sheet_inventory_movement", "source_id")
    op.drop_column("self_use_sheet_inventory_movement", "source_type")
    op.drop_column("self_use_sheet_inventory_movement", "location_balance_after")
    op.drop_column("self_use_sheet_inventory_movement", "counterpart_location_id")
    op.drop_column("self_use_sheet_inventory_movement", "raw_material_location_id")
    op.drop_index("ix_self_use_sheet_inv_balance__location_id", table_name="self_use_sheet_inventory_balance")
    op.drop_index("ix_self_use_sheet_inv_balance__lot_id", table_name="self_use_sheet_inventory_balance")
    op.drop_table("self_use_sheet_inventory_balance")

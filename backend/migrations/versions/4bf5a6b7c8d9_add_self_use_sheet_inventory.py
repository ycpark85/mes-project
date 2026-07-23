"""add self-use sheet processing and inventory

Revision ID: 4bf5a6b7c8d9
Revises: 3ae4f5a6b7c8
Create Date: 2026-07-16 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "4bf5a6b7c8d9"
down_revision: Union[str, Sequence[str], None] = "3ae4f5a6b7c8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "self_use_sheet_job",
        sa.Column("self_use_sheet_job_id", sa.BigInteger(), primary_key=True),
        sa.Column("use_no", sa.String(length=40), nullable=False),
        sa.Column("purpose_type", sa.String(length=30), nullable=False),
        sa.Column("execution_type", sa.String(length=20), nullable=False),
        sa.Column("partner_id", sa.BigInteger(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="DRAFT"),
        sa.Column("cut_width_mm", sa.Numeric(18, 2), nullable=False),
        sa.Column("cut_length_mm", sa.Numeric(18, 2), nullable=False),
        sa.Column("planned_output_qty", sa.BigInteger(), nullable=False),
        sa.Column("expected_processing_fee", sa.Numeric(18, 2), nullable=False, server_default="0"),
        sa.Column("actual_processing_fee", sa.Numeric(18, 2), nullable=True),
        sa.Column("actual_input_qty", sa.Numeric(18, 2), nullable=True),
        sa.Column("produced_qty", sa.BigInteger(), nullable=True),
        sa.Column("scrap_qty", sa.BigInteger(), nullable=True),
        sa.Column("memo", sa.Text(), nullable=True),
        sa.Column("cancel_reason", sa.Text(), nullable=True),
        sa.Column("created_by", sa.String(length=100), nullable=False),
        sa.Column("started_by", sa.String(length=100), nullable=True),
        sa.Column("completed_by", sa.String(length=100), nullable=True),
        sa.Column("canceled_by", sa.String(length=100), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("canceled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint(
            "purpose_type IN ('PRINT_SETUP','SAMPLE','TEST_RND','OTHER')",
            name="ck_self_use_sheet_job__purpose_type",
        ),
        sa.CheckConstraint(
            "purpose_type <> 'OTHER' OR NULLIF(TRIM(memo), '') IS NOT NULL",
            name="ck_self_use_sheet_job__other_memo_required",
        ),
        sa.CheckConstraint(
            "execution_type IN ('INTERNAL','OUTSOURCE')",
            name="ck_self_use_sheet_job__execution_type",
        ),
        sa.CheckConstraint(
            "status IN ('DRAFT','IN_PROGRESS','COMPLETED','CANCELED')",
            name="ck_self_use_sheet_job__status",
        ),
        sa.CheckConstraint(
            "execution_type <> 'OUTSOURCE' OR partner_id IS NOT NULL",
            name="ck_self_use_sheet_job__outsource_partner_required",
        ),
        sa.CheckConstraint("cut_width_mm > 0", name="ck_self_use_sheet_job__cut_width_gt_0"),
        sa.CheckConstraint("cut_length_mm > 0", name="ck_self_use_sheet_job__cut_length_gt_0"),
        sa.CheckConstraint("planned_output_qty > 0", name="ck_self_use_sheet_job__planned_output_qty_gt_0"),
        sa.CheckConstraint("expected_processing_fee >= 0", name="ck_self_use_sheet_job__expected_fee_ge_0"),
        sa.CheckConstraint(
            "actual_processing_fee IS NULL OR actual_processing_fee >= 0",
            name="ck_self_use_sheet_job__actual_fee_ge_0",
        ),
        sa.CheckConstraint(
            "actual_input_qty IS NULL OR actual_input_qty > 0",
            name="ck_self_use_sheet_job__actual_input_qty_gt_0",
        ),
        sa.CheckConstraint("produced_qty IS NULL OR produced_qty > 0", name="ck_self_use_sheet_job__produced_qty_gt_0"),
        sa.CheckConstraint("scrap_qty IS NULL OR scrap_qty >= 0", name="ck_self_use_sheet_job__scrap_qty_ge_0"),
        sa.CheckConstraint("version >= 1", name="ck_self_use_sheet_job__version_positive"),
        sa.CheckConstraint(
            "status <> 'IN_PROGRESS' OR (started_at IS NOT NULL AND started_by IS NOT NULL)",
            name="ck_self_use_sheet_job__in_progress_audit_required",
        ),
        sa.CheckConstraint(
            "status <> 'COMPLETED' OR (actual_processing_fee IS NOT NULL AND actual_input_qty IS NOT NULL AND produced_qty IS NOT NULL AND completed_at IS NOT NULL AND completed_by IS NOT NULL)",
            name="ck_self_use_sheet_job__completion_required",
        ),
        sa.CheckConstraint(
            "status <> 'CANCELED' OR (canceled_at IS NOT NULL AND canceled_by IS NOT NULL AND NULLIF(TRIM(cancel_reason), '') IS NOT NULL)",
            name="ck_self_use_sheet_job__cancel_audit_required",
        ),
        sa.ForeignKeyConstraint(["partner_id"], ["partner.partner_id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("use_no", name="uq_self_use_sheet_job__use_no"),
    )
    op.create_index("ix_self_use_sheet_job__status", "self_use_sheet_job", ["status"])
    op.create_index("ix_self_use_sheet_job__purpose_type", "self_use_sheet_job", ["purpose_type"])
    op.create_index("ix_self_use_sheet_job__partner_id", "self_use_sheet_job", ["partner_id"])
    op.create_index("ix_self_use_sheet_job__created_at", "self_use_sheet_job", ["created_at"])

    op.create_table(
        "self_use_sheet_raw_material_allocation",
        sa.Column("self_use_sheet_raw_material_allocation_id", sa.BigInteger(), primary_key=True),
        sa.Column("self_use_sheet_job_id", sa.BigInteger(), nullable=False),
        sa.Column("raw_material_id", sa.BigInteger(), nullable=False),
        sa.Column("source_location_id", sa.BigInteger(), nullable=False),
        sa.Column("original_inventory_lot_id", sa.BigInteger(), nullable=True),
        sa.Column("processing_inventory_lot_id", sa.BigInteger(), nullable=True),
        sa.Column("lot_no", sa.String(length=100), nullable=False),
        sa.Column("planned_qty", sa.Numeric(18, 2), nullable=False),
        sa.Column("actual_consumed_qty", sa.Numeric(18, 2), nullable=True),
        sa.Column("returned_qty", sa.Numeric(18, 2), nullable=False, server_default="0"),
        sa.Column("unit_cost_snapshot", sa.Numeric(18, 4), nullable=True),
        sa.Column("amount_snapshot", sa.Numeric(18, 2), nullable=True),
        sa.Column("issue_movement_id", sa.BigInteger(), nullable=True),
        sa.Column("dispatch_transfer_key", sa.String(length=80), nullable=True),
        sa.Column("return_transfer_key", sa.String(length=80), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="PLANNED"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("planned_qty > 0", name="ck_self_use_sheet_rm_alloc__planned_qty_gt_0"),
        sa.CheckConstraint(
            "actual_consumed_qty IS NULL OR actual_consumed_qty > 0",
            name="ck_self_use_sheet_rm_alloc__actual_qty_gt_0",
        ),
        sa.CheckConstraint("returned_qty >= 0", name="ck_self_use_sheet_rm_alloc__returned_qty_ge_0"),
        sa.CheckConstraint(
            "status IN ('PLANNED','ISSUED','CONSUMED','REVERSED')",
            name="ck_self_use_sheet_rm_alloc__status",
        ),
        sa.CheckConstraint(
            "status <> 'CONSUMED' OR (actual_consumed_qty IS NOT NULL AND actual_consumed_qty + returned_qty = planned_qty)",
            name="ck_self_use_sheet_rm_alloc__consumed_qty_reconciled",
        ),
        sa.ForeignKeyConstraint(
            ["self_use_sheet_job_id"],
            ["self_use_sheet_job.self_use_sheet_job_id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(["raw_material_id"], ["raw_material.raw_material_id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["source_location_id"],
            ["raw_material_location.raw_material_location_id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["original_inventory_lot_id"],
            ["raw_material_inventory_lot.raw_material_inventory_lot_id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["processing_inventory_lot_id"],
            ["raw_material_inventory_lot.raw_material_inventory_lot_id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["issue_movement_id"],
            ["raw_material_inventory_movement.raw_material_inventory_movement_id"],
            ondelete="SET NULL",
        ),
    )
    op.create_index("ix_self_use_sheet_rm_alloc__job_id", "self_use_sheet_raw_material_allocation", ["self_use_sheet_job_id"])
    op.create_index("ix_self_use_sheet_rm_alloc__material_id", "self_use_sheet_raw_material_allocation", ["raw_material_id"])
    op.create_index("ix_self_use_sheet_rm_alloc__original_lot_id", "self_use_sheet_raw_material_allocation", ["original_inventory_lot_id"])
    op.create_index("ix_self_use_sheet_rm_alloc__processing_lot_id", "self_use_sheet_raw_material_allocation", ["processing_inventory_lot_id"])

    op.create_table(
        "self_use_sheet_inventory_lot",
        sa.Column("self_use_sheet_inventory_lot_id", sa.BigInteger(), primary_key=True),
        sa.Column("self_use_sheet_job_id", sa.BigInteger(), nullable=False),
        sa.Column("raw_material_id", sa.BigInteger(), nullable=False),
        sa.Column("sheet_lot_no", sa.String(length=50), nullable=False),
        sa.Column("source_lot_summary", sa.Text(), nullable=False),
        sa.Column("cut_width_mm", sa.Numeric(18, 2), nullable=False),
        sa.Column("cut_length_mm", sa.Numeric(18, 2), nullable=False),
        sa.Column("initial_qty", sa.BigInteger(), nullable=False),
        sa.Column("current_qty", sa.BigInteger(), nullable=False),
        sa.Column("material_amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("processing_fee", sa.Numeric(18, 2), nullable=False),
        sa.Column("total_cost", sa.Numeric(18, 2), nullable=False),
        sa.Column("unit_cost", sa.Numeric(18, 4), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="AVAILABLE"),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("initial_qty > 0", name="ck_self_use_sheet_inventory_lot__initial_qty_gt_0"),
        sa.CheckConstraint("current_qty >= 0", name="ck_self_use_sheet_inventory_lot__current_qty_ge_0"),
        sa.CheckConstraint("current_qty <= initial_qty", name="ck_self_use_sheet_inventory_lot__current_qty_le_initial"),
        sa.CheckConstraint("material_amount >= 0", name="ck_self_use_sheet_inventory_lot__material_amount_ge_0"),
        sa.CheckConstraint("processing_fee >= 0", name="ck_self_use_sheet_inventory_lot__processing_fee_ge_0"),
        sa.CheckConstraint("total_cost >= 0", name="ck_self_use_sheet_inventory_lot__total_cost_ge_0"),
        sa.CheckConstraint("unit_cost >= 0", name="ck_self_use_sheet_inventory_lot__unit_cost_ge_0"),
        sa.CheckConstraint(
            "status IN ('AVAILABLE','DEPLETED','CANCELED')",
            name="ck_self_use_sheet_inventory_lot__status",
        ),
        sa.CheckConstraint("version >= 1", name="ck_self_use_sheet_inventory_lot__version_positive"),
        sa.ForeignKeyConstraint(
            ["self_use_sheet_job_id"],
            ["self_use_sheet_job.self_use_sheet_job_id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(["raw_material_id"], ["raw_material.raw_material_id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("self_use_sheet_job_id", name="uq_self_use_sheet_inventory_lot__job_id"),
        sa.UniqueConstraint("sheet_lot_no", name="uq_self_use_sheet_inventory_lot__lot_no"),
    )
    op.create_index("ix_self_use_sheet_inventory_lot__material_id", "self_use_sheet_inventory_lot", ["raw_material_id"])
    op.create_index("ix_self_use_sheet_inventory_lot__status", "self_use_sheet_inventory_lot", ["status"])
    op.create_index("ix_self_use_sheet_inventory_lot__completed_at", "self_use_sheet_inventory_lot", ["completed_at"])

    op.create_table(
        "self_use_sheet_inventory_movement",
        sa.Column("self_use_sheet_inventory_movement_id", sa.BigInteger(), primary_key=True),
        sa.Column("self_use_sheet_inventory_lot_id", sa.BigInteger(), nullable=False),
        sa.Column("movement_type", sa.String(length=20), nullable=False),
        sa.Column("qty", sa.BigInteger(), nullable=False),
        sa.Column("balance_after", sa.BigInteger(), nullable=False),
        sa.Column("purpose_type", sa.String(length=30), nullable=True),
        sa.Column("unit_cost_snapshot", sa.Numeric(18, 4), nullable=False),
        sa.Column("amount_snapshot", sa.Numeric(18, 2), nullable=False),
        sa.Column("source_movement_id", sa.BigInteger(), nullable=True),
        sa.Column("memo", sa.Text(), nullable=True),
        sa.Column("created_by", sa.String(length=100), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint(
            "movement_type IN ('PRODUCE_IN','USE_OUT','USE_REVERSE','CANCEL_OUT')",
            name="ck_self_use_sheet_inv_movement__movement_type",
        ),
        sa.CheckConstraint("qty <> 0", name="ck_self_use_sheet_inv_movement__qty_not_zero"),
        sa.CheckConstraint("balance_after >= 0", name="ck_self_use_sheet_inv_movement__balance_ge_0"),
        sa.CheckConstraint("amount_snapshot >= 0", name="ck_self_use_sheet_inv_movement__amount_ge_0"),
        sa.CheckConstraint(
            "purpose_type IS NULL OR purpose_type IN ('PRINT_SETUP','SAMPLE','TEST_RND','OTHER')",
            name="ck_self_use_sheet_inv_movement__purpose_type",
        ),
        sa.ForeignKeyConstraint(
            ["self_use_sheet_inventory_lot_id"],
            ["self_use_sheet_inventory_lot.self_use_sheet_inventory_lot_id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["source_movement_id"],
            ["self_use_sheet_inventory_movement.self_use_sheet_inventory_movement_id"],
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint("source_movement_id", name="uq_self_use_sheet_inv_movement__source_movement_id"),
    )
    op.create_index("ix_self_use_sheet_inv_movement__lot_id", "self_use_sheet_inventory_movement", ["self_use_sheet_inventory_lot_id"])
    op.create_index("ix_self_use_sheet_inv_movement__created_at", "self_use_sheet_inventory_movement", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_self_use_sheet_inv_movement__created_at", table_name="self_use_sheet_inventory_movement")
    op.drop_index("ix_self_use_sheet_inv_movement__lot_id", table_name="self_use_sheet_inventory_movement")
    op.drop_table("self_use_sheet_inventory_movement")
    op.drop_index("ix_self_use_sheet_inventory_lot__completed_at", table_name="self_use_sheet_inventory_lot")
    op.drop_index("ix_self_use_sheet_inventory_lot__status", table_name="self_use_sheet_inventory_lot")
    op.drop_index("ix_self_use_sheet_inventory_lot__material_id", table_name="self_use_sheet_inventory_lot")
    op.drop_table("self_use_sheet_inventory_lot")
    op.drop_index("ix_self_use_sheet_rm_alloc__processing_lot_id", table_name="self_use_sheet_raw_material_allocation")
    op.drop_index("ix_self_use_sheet_rm_alloc__original_lot_id", table_name="self_use_sheet_raw_material_allocation")
    op.drop_index("ix_self_use_sheet_rm_alloc__material_id", table_name="self_use_sheet_raw_material_allocation")
    op.drop_index("ix_self_use_sheet_rm_alloc__job_id", table_name="self_use_sheet_raw_material_allocation")
    op.drop_table("self_use_sheet_raw_material_allocation")
    op.drop_index("ix_self_use_sheet_job__created_at", table_name="self_use_sheet_job")
    op.drop_index("ix_self_use_sheet_job__partner_id", table_name="self_use_sheet_job")
    op.drop_index("ix_self_use_sheet_job__purpose_type", table_name="self_use_sheet_job")
    op.drop_index("ix_self_use_sheet_job__status", table_name="self_use_sheet_job")
    op.drop_table("self_use_sheet_job")

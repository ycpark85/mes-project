"""add raw material inventory

Revision ID: 3f5c8a1b9d20
Revises: c9e8b7a6d5f4
Create Date: 2026-06-26 11:30:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "3f5c8a1b9d20"
down_revision: Union[str, None] = "c9e8b7a6d5f4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "raw_material",
        sa.Column("raw_material_id", sa.BigInteger(), nullable=False),
        sa.Column("material_code", sa.String(length=60), nullable=False),
        sa.Column("material_name", sa.String(length=200), nullable=False),
        sa.Column("material_spec", sa.String(length=100), nullable=True),
        sa.Column("width_mm", sa.BigInteger(), nullable=True),
        sa.Column("material_type", sa.String(length=100), nullable=True),
        sa.Column("uom", sa.String(length=10), nullable=False),
        sa.Column("standard_unit_cost", sa.Numeric(18, 4), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("memo", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("standard_unit_cost IS NULL OR standard_unit_cost >= 0", name="ck_raw_material__standard_unit_cost_ge_0"),
        sa.PrimaryKeyConstraint("raw_material_id"),
        sa.UniqueConstraint("material_code", name="uq_raw_material__material_code"),
    )
    op.create_index("ix_raw_material__is_active", "raw_material", ["is_active"])
    op.create_index("ix_raw_material__material_name", "raw_material", ["material_name"])

    op.create_table(
        "raw_material_location",
        sa.Column("raw_material_location_id", sa.BigInteger(), nullable=False),
        sa.Column("location_code", sa.String(length=60), nullable=False),
        sa.Column("location_name", sa.String(length=200), nullable=False),
        sa.Column("location_type", sa.String(length=30), nullable=False),
        sa.Column("partner_id", sa.BigInteger(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("memo", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "location_type IN ('INTERNAL_WAREHOUSE','OUTSOURCE_VENDOR','OTHER')",
            name="ck_raw_material_location__location_type",
        ),
        sa.ForeignKeyConstraint(["partner_id"], ["partner.partner_id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("raw_material_location_id"),
        sa.UniqueConstraint("location_code", name="uq_raw_material_location__location_code"),
    )
    op.create_index("ix_raw_material_location__is_active", "raw_material_location", ["is_active"])
    op.create_index("ix_raw_material_location__partner_id", "raw_material_location", ["partner_id"])

    op.create_table(
        "raw_material_inventory",
        sa.Column("raw_material_inventory_id", sa.BigInteger(), nullable=False),
        sa.Column("raw_material_id", sa.BigInteger(), nullable=False),
        sa.Column("raw_material_location_id", sa.BigInteger(), nullable=False),
        sa.Column("current_qty", sa.Numeric(18, 2), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["raw_material_id"], ["raw_material.raw_material_id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["raw_material_location_id"], ["raw_material_location.raw_material_location_id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("raw_material_inventory_id"),
        sa.UniqueConstraint("raw_material_id", "raw_material_location_id", name="uq_raw_material_inventory__material_location"),
    )
    op.create_index("ix_raw_material_inventory__location_id", "raw_material_inventory", ["raw_material_location_id"])
    op.create_index("ix_raw_material_inventory__material_id", "raw_material_inventory", ["raw_material_id"])

    op.create_table(
        "raw_material_inventory_lot",
        sa.Column("raw_material_inventory_lot_id", sa.BigInteger(), nullable=False),
        sa.Column("raw_material_id", sa.BigInteger(), nullable=False),
        sa.Column("raw_material_location_id", sa.BigInteger(), nullable=False),
        sa.Column("lot_no", sa.String(length=100), nullable=False),
        sa.Column("current_qty", sa.Numeric(18, 2), nullable=False),
        sa.Column("unit_cost", sa.Numeric(18, 4), nullable=True),
        sa.Column("received_at", sa.Date(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["raw_material_id"], ["raw_material.raw_material_id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["raw_material_location_id"], ["raw_material_location.raw_material_location_id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("raw_material_inventory_lot_id"),
        sa.UniqueConstraint(
            "raw_material_id",
            "raw_material_location_id",
            "lot_no",
            name="uq_raw_material_inventory_lot__material_location_lot",
        ),
    )
    op.create_index("ix_raw_material_inventory_lot__location_id", "raw_material_inventory_lot", ["raw_material_location_id"])
    op.create_index("ix_raw_material_inventory_lot__lot_no", "raw_material_inventory_lot", ["lot_no"])
    op.create_index("ix_raw_material_inventory_lot__material_id", "raw_material_inventory_lot", ["raw_material_id"])

    op.create_table(
        "raw_material_inventory_movement",
        sa.Column("raw_material_inventory_movement_id", sa.BigInteger(), nullable=False),
        sa.Column("raw_material_id", sa.BigInteger(), nullable=False),
        sa.Column("raw_material_location_id", sa.BigInteger(), nullable=False),
        sa.Column("raw_material_inventory_lot_id", sa.BigInteger(), nullable=True),
        sa.Column("lot_no", sa.String(length=100), nullable=True),
        sa.Column("movement_type", sa.String(length=30), nullable=False),
        sa.Column("qty", sa.Numeric(18, 2), nullable=False),
        sa.Column("balance_after", sa.Numeric(18, 2), nullable=False),
        sa.Column("unit_cost_snapshot", sa.Numeric(18, 4), nullable=True),
        sa.Column("amount_snapshot", sa.Numeric(18, 2), nullable=True),
        sa.Column("source_type", sa.String(length=50), nullable=True),
        sa.Column("source_id", sa.BigInteger(), nullable=True),
        sa.Column("transfer_key", sa.String(length=80), nullable=True),
        sa.Column("memo", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "movement_type IN ('INBOUND','TRANSFER_OUT','TRANSFER_IN','ADJUST_IN','ADJUST_OUT','CONSUME_OUT','CONSUME_REVERSE')",
            name="ck_raw_material_inventory_movement__movement_type",
        ),
        sa.CheckConstraint("qty <> 0", name="ck_raw_material_inventory_movement__qty_not_zero"),
        sa.CheckConstraint(
            "amount_snapshot IS NULL OR amount_snapshot >= 0",
            name="ck_raw_material_inventory_movement__amount_snapshot_ge_0",
        ),
        sa.ForeignKeyConstraint(["raw_material_id"], ["raw_material.raw_material_id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["raw_material_location_id"], ["raw_material_location.raw_material_location_id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["raw_material_inventory_lot_id"],
            ["raw_material_inventory_lot.raw_material_inventory_lot_id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("raw_material_inventory_movement_id"),
    )
    op.create_index("ix_raw_material_inventory_movement__created_at", "raw_material_inventory_movement", ["created_at"])
    op.create_index("ix_raw_material_inventory_movement__location_id", "raw_material_inventory_movement", ["raw_material_location_id"])
    op.create_index("ix_raw_material_inventory_movement__lot_id", "raw_material_inventory_movement", ["raw_material_inventory_lot_id"])
    op.create_index("ix_raw_material_inventory_movement__material_id", "raw_material_inventory_movement", ["raw_material_id"])
    op.create_index("ix_raw_material_inventory_movement__transfer_key", "raw_material_inventory_movement", ["transfer_key"])


def downgrade() -> None:
    op.drop_index("ix_raw_material_inventory_movement__transfer_key", table_name="raw_material_inventory_movement")
    op.drop_index("ix_raw_material_inventory_movement__material_id", table_name="raw_material_inventory_movement")
    op.drop_index("ix_raw_material_inventory_movement__lot_id", table_name="raw_material_inventory_movement")
    op.drop_index("ix_raw_material_inventory_movement__location_id", table_name="raw_material_inventory_movement")
    op.drop_index("ix_raw_material_inventory_movement__created_at", table_name="raw_material_inventory_movement")
    op.drop_table("raw_material_inventory_movement")
    op.drop_index("ix_raw_material_inventory_lot__material_id", table_name="raw_material_inventory_lot")
    op.drop_index("ix_raw_material_inventory_lot__lot_no", table_name="raw_material_inventory_lot")
    op.drop_index("ix_raw_material_inventory_lot__location_id", table_name="raw_material_inventory_lot")
    op.drop_table("raw_material_inventory_lot")
    op.drop_index("ix_raw_material_inventory__material_id", table_name="raw_material_inventory")
    op.drop_index("ix_raw_material_inventory__location_id", table_name="raw_material_inventory")
    op.drop_table("raw_material_inventory")
    op.drop_index("ix_raw_material_location__partner_id", table_name="raw_material_location")
    op.drop_index("ix_raw_material_location__is_active", table_name="raw_material_location")
    op.drop_table("raw_material_location")
    op.drop_index("ix_raw_material__material_name", table_name="raw_material")
    op.drop_index("ix_raw_material__is_active", table_name="raw_material")
    op.drop_table("raw_material")

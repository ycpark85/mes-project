"""add core query indexes

Revision ID: 9ac4f7d2b6e1
Revises: 8f4c2b1a9d30
Create Date: 2026-06-02 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "9ac4f7d2b6e1"
down_revision: Union[str, Sequence[str], None] = "8f4c2b1a9d30"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(
        "ix_order_line__active_status_due",
        "order_line",
        ["is_active", "status", "due_date", "order_no", "line_no"],
    )
    op.create_index("ix_lot__parent_lot_id", "lot", ["parent_lot_id"])
    op.create_index(
        "ix_lot__order_line_created",
        "lot",
        ["order_line_id", "created_date", "lot_id"],
    )
    op.create_index("ix_lot_step__lot_status", "lot_step", ["lot_id", "status"])
    op.create_index(
        "ix_inspection_schedule__status_date",
        "inspection_schedule",
        ["status", "inspection_date"],
    )
    op.create_index(
        "ix_product_inventory_lot__product_created",
        "product_inventory_lot",
        ["product_id", "created_at", "product_inventory_lot_id"],
    )
    op.create_index(
        "ix_product_inventory_movement__order_line_type",
        "product_inventory_movement",
        ["order_line_id", "movement_type"],
    )
    op.create_index(
        "ix_product_inventory_movement__product_type_created",
        "product_inventory_movement",
        ["product_id", "movement_type", "created_at"],
    )
    op.create_index(
        "ix_shipment_line__status_created",
        "shipment_line",
        ["status", "created_at", "shipment_line_id"],
    )
    op.create_index(
        "ix_shipment_line__inventory_lot_source_status",
        "shipment_line",
        ["product_inventory_lot_id", "source_type", "status"],
    )
    op.create_index(
        "ix_shipment_line__order_line_source_status_result",
        "shipment_line",
        ["order_line_id", "source_type", "status", "inspection_result_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_shipment_line__order_line_source_status_result",
        table_name="shipment_line",
    )
    op.drop_index(
        "ix_shipment_line__inventory_lot_source_status",
        table_name="shipment_line",
    )
    op.drop_index("ix_shipment_line__status_created", table_name="shipment_line")
    op.drop_index(
        "ix_product_inventory_movement__product_type_created",
        table_name="product_inventory_movement",
    )
    op.drop_index(
        "ix_product_inventory_movement__order_line_type",
        table_name="product_inventory_movement",
    )
    op.drop_index(
        "ix_product_inventory_lot__product_created",
        table_name="product_inventory_lot",
    )
    op.drop_index(
        "ix_inspection_schedule__status_date",
        table_name="inspection_schedule",
    )
    op.drop_index("ix_lot_step__lot_status", table_name="lot_step")
    op.drop_index("ix_lot__order_line_created", table_name="lot")
    op.drop_index("ix_lot__parent_lot_id", table_name="lot")
    op.drop_index("ix_order_line__active_status_due", table_name="order_line")

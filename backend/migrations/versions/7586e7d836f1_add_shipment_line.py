"""add_shipment_line

Revision ID: 7586e7d836f1
Revises: 305c5f337ab3
Create Date: 2026-05-19 14:25:09.527264

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7586e7d836f1'
down_revision: Union[str, Sequence[str], None] = '305c5f337ab3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "shipment_line",
        sa.Column("shipment_line_id", sa.BigInteger(), nullable=False),
        sa.Column("order_line_id", sa.BigInteger(), nullable=False),
        sa.Column("product_id", sa.BigInteger(), nullable=False),
        sa.Column("lot_id", sa.BigInteger(), nullable=True),
        sa.Column("inspection_result_id", sa.BigInteger(), nullable=True),
        sa.Column("source_type", sa.String(length=30), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("ship_qty", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("shipped_qty", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("memo", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("shipped_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["order_line_id"], ["order_line.order_line_id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["product_id"], ["product.product_id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["lot_id"], ["lot.lot_id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["inspection_result_id"], ["inspection_result.inspection_result_id"], ondelete="SET NULL"),
        sa.CheckConstraint("status IN ('WAITING','DONE','CANCELED')", name="ck_shipment_line__status"),
        sa.CheckConstraint("source_type IN ('STOCK','INSPECTION_RESULT')", name="ck_shipment_line__source_type"),
        sa.CheckConstraint("ship_qty >= 0", name="ck_shipment_line__ship_qty"),
        sa.CheckConstraint("shipped_qty >= 0", name="ck_shipment_line__shipped_qty"),
        sa.PrimaryKeyConstraint("shipment_line_id"),
    )

    op.create_index("ix_shipment_line__order_line_id", "shipment_line", ["order_line_id"])
    op.create_index("ix_shipment_line__product_id", "shipment_line", ["product_id"])
    op.create_index("ix_shipment_line__lot_id", "shipment_line", ["lot_id"])
    op.create_index("ix_shipment_line__inspection_result_id", "shipment_line", ["inspection_result_id"])
    op.create_index("ix_shipment_line__status", "shipment_line", ["status"])
    op.create_index("ix_shipment_line__created_at", "shipment_line", ["created_at"])

    op.alter_column("shipment_line", "ship_qty", server_default=None)
    op.alter_column("shipment_line", "shipped_qty", server_default=None)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_shipment_line__created_at", table_name="shipment_line")
    op.drop_index("ix_shipment_line__status", table_name="shipment_line")
    op.drop_index("ix_shipment_line__inspection_result_id", table_name="shipment_line")
    op.drop_index("ix_shipment_line__lot_id", table_name="shipment_line")
    op.drop_index("ix_shipment_line__product_id", table_name="shipment_line")
    op.drop_index("ix_shipment_line__order_line_id", table_name="shipment_line")
    op.drop_table("shipment_line")

"""add product inventory lot

Revision ID: 8f4c2b1a9d30
Revises: 637b687acbfc
Create Date: 2026-06-01 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "8f4c2b1a9d30"
down_revision: Union[str, Sequence[str], None] = "637b687acbfc"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "product_inventory_lot",
        sa.Column("product_inventory_lot_id", sa.BigInteger(), nullable=False),
        sa.Column("product_id", sa.BigInteger(), nullable=False),
        sa.Column("lot_no", sa.String(length=100), nullable=False),
        sa.Column("current_qty", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["product_id"], ["product.product_id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("product_inventory_lot_id"),
        sa.UniqueConstraint("product_id", "lot_no", name="uq_product_inventory_lot__product_id__lot_no"),
    )
    op.create_index("ix_product_inventory_lot__product_id", "product_inventory_lot", ["product_id"])
    op.create_index("ix_product_inventory_lot__lot_no", "product_inventory_lot", ["lot_no"])

    op.add_column(
        "product_inventory_movement",
        sa.Column("product_inventory_lot_id", sa.BigInteger(), nullable=True),
    )
    op.add_column(
        "product_inventory_movement",
        sa.Column("stock_lot_no", sa.String(length=100), nullable=True),
    )
    op.create_foreign_key(
        "fk_product_inventory_movement__product_inventory_lot_id",
        "product_inventory_movement",
        "product_inventory_lot",
        ["product_inventory_lot_id"],
        ["product_inventory_lot_id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_product_inventory_movement__product_inventory_lot_id",
        "product_inventory_movement",
        ["product_inventory_lot_id"],
    )
    op.create_index(
        "ix_product_inventory_movement__stock_lot_no",
        "product_inventory_movement",
        ["stock_lot_no"],
    )

    op.add_column(
        "shipment_line",
        sa.Column("product_inventory_lot_id", sa.BigInteger(), nullable=True),
    )
    op.add_column(
        "shipment_line",
        sa.Column("stock_lot_no", sa.String(length=100), nullable=True),
    )
    op.create_foreign_key(
        "fk_shipment_line__product_inventory_lot_id",
        "shipment_line",
        "product_inventory_lot",
        ["product_inventory_lot_id"],
        ["product_inventory_lot_id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_shipment_line__product_inventory_lot_id",
        "shipment_line",
        ["product_inventory_lot_id"],
    )
    op.create_index("ix_shipment_line__stock_lot_no", "shipment_line", ["stock_lot_no"])

    op.alter_column("product_inventory_lot", "current_qty", server_default=None)


def downgrade() -> None:
    op.drop_index("ix_shipment_line__stock_lot_no", table_name="shipment_line")
    op.drop_index("ix_shipment_line__product_inventory_lot_id", table_name="shipment_line")
    op.drop_constraint(
        "fk_shipment_line__product_inventory_lot_id",
        "shipment_line",
        type_="foreignkey",
    )
    op.drop_column("shipment_line", "stock_lot_no")
    op.drop_column("shipment_line", "product_inventory_lot_id")

    op.drop_index("ix_product_inventory_movement__stock_lot_no", table_name="product_inventory_movement")
    op.drop_index(
        "ix_product_inventory_movement__product_inventory_lot_id",
        table_name="product_inventory_movement",
    )
    op.drop_constraint(
        "fk_product_inventory_movement__product_inventory_lot_id",
        "product_inventory_movement",
        type_="foreignkey",
    )
    op.drop_column("product_inventory_movement", "stock_lot_no")
    op.drop_column("product_inventory_movement", "product_inventory_lot_id")

    op.drop_index("ix_product_inventory_lot__lot_no", table_name="product_inventory_lot")
    op.drop_index("ix_product_inventory_lot__product_id", table_name="product_inventory_lot")
    op.drop_table("product_inventory_lot")

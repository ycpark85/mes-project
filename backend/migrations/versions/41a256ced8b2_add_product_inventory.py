"""add product inventory

Revision ID: 41a256ced8b2
Revises: bc324b82e3e2
Create Date: 2026-05-13 12:38:04.418216

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '41a256ced8b2'
down_revision: Union[str, Sequence[str], None] = 'bc324b82e3e2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "product_inventory",
        sa.Column("product_inventory_id", sa.BigInteger(), nullable=False),
        sa.Column("product_id", sa.BigInteger(), nullable=False),
        sa.Column("current_qty", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["product_id"], ["product.product_id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("product_inventory_id"),
        sa.UniqueConstraint("product_id", name="uq_product_inventory__product_id"),
    )

    op.create_table(
        "product_inventory_movement",
        sa.Column("inventory_movement_id", sa.BigInteger(), nullable=False),
        sa.Column("product_id", sa.BigInteger(), nullable=False),
        sa.Column("movement_type", sa.String(length=30), nullable=False),
        sa.Column("qty", sa.BigInteger(), nullable=False),
        sa.Column("balance_after", sa.BigInteger(), nullable=False),
        sa.Column("source_type", sa.String(length=50), nullable=True),
        sa.Column("source_id", sa.BigInteger(), nullable=True),
        sa.Column("order_line_id", sa.BigInteger(), nullable=True),
        sa.Column("inspection_schedule_id", sa.BigInteger(), nullable=True),
        sa.Column("inspection_result_id", sa.BigInteger(), nullable=True),
        sa.Column("memo", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "movement_type IN ('INSPECTION_IN','SHIP_OUT','ADJUST_IN','ADJUST_OUT')",
            name="ck_product_inventory_movement__movement_type",
        ),
        sa.CheckConstraint(
            "qty <> 0",
            name="ck_product_inventory_movement__qty_not_zero",
        ),
        sa.ForeignKeyConstraint(["product_id"], ["product.product_id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["order_line_id"], ["order_line.order_line_id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["inspection_schedule_id"], ["inspection_schedule.inspection_schedule_id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["inspection_result_id"], ["inspection_result.inspection_result_id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("inventory_movement_id"),
    )

    op.create_index(
        "ix_product_inventory_movement__product_id",
        "product_inventory_movement",
        ["product_id"],
        unique=False,
    )
    op.create_index(
        "ix_product_inventory_movement__order_line_id",
        "product_inventory_movement",
        ["order_line_id"],
        unique=False,
    )
    op.create_index(
        "ix_product_inventory_movement__inspection_result_id",
        "product_inventory_movement",
        ["inspection_result_id"],
        unique=False,
    )
    op.create_index(
        "ix_product_inventory_movement__created_at",
        "product_inventory_movement",
        ["created_at"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_product_inventory_movement__created_at", table_name="product_inventory_movement")
    op.drop_index("ix_product_inventory_movement__inspection_result_id", table_name="product_inventory_movement")
    op.drop_index("ix_product_inventory_movement__order_line_id", table_name="product_inventory_movement")
    op.drop_index("ix_product_inventory_movement__product_id", table_name="product_inventory_movement")
    op.drop_table("product_inventory_movement")
    op.drop_table("product_inventory")
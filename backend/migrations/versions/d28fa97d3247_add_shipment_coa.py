"""add shipment coa

Revision ID: d28fa97d3247
Revises: 78577439f6e0
Create Date: 2026-05-22 10:22:24.760433

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd28fa97d3247'
down_revision: Union[str, Sequence[str], None] = '78577439f6e0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "shipment_coa",
        sa.Column("shipment_coa_id", sa.BigInteger(), nullable=False),
        sa.Column("order_line_id", sa.BigInteger(), nullable=False),
        sa.Column("product_id", sa.BigInteger(), nullable=False),
        sa.Column("product_name_snapshot", sa.String(length=200), nullable=False),
        sa.Column("product_spec_snapshot", sa.String(length=100), nullable=False),
        sa.Column("material_snapshot", sa.String(length=100), nullable=False),
        sa.Column("partner_name_snapshot", sa.String(length=200), nullable=False),
        sa.Column("lot_nos_snapshot", sa.Text(), nullable=False),
        sa.Column("stock_lot_nos_snapshot", sa.Text(), nullable=True),
        sa.Column("production_lot_nos_snapshot", sa.Text(), nullable=True),
        sa.Column("quantity_snapshot", sa.BigInteger(), nullable=False),
        sa.Column("inspection_date_snapshot", sa.Date(), nullable=False),
        sa.Column(
            "issued_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("memo", sa.Text(), nullable=True),
        sa.CheckConstraint(
            "quantity_snapshot >= 0",
            name="ck_shipment_coa__quantity_snapshot",
        ),
        sa.ForeignKeyConstraint(
            ["order_line_id"],
            ["order_line.order_line_id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["product_id"],
            ["product.product_id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("shipment_coa_id"),
        sa.UniqueConstraint("order_line_id", name="uq_shipment_coa__order_line"),
    )

    op.create_index(
        "ix_shipment_coa__order_line_id",
        "shipment_coa",
        ["order_line_id"],
    )
    op.create_index(
        "ix_shipment_coa__product_id",
        "shipment_coa",
        ["product_id"],
    )
    op.create_index(
        "ix_shipment_coa__issued_at",
        "shipment_coa",
        ["issued_at"],
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_shipment_coa__issued_at", table_name="shipment_coa")
    op.drop_index("ix_shipment_coa__product_id", table_name="shipment_coa")
    op.drop_index("ix_shipment_coa__order_line_id", table_name="shipment_coa")
    op.drop_table("shipment_coa")
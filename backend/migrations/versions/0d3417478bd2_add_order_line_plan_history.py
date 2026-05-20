"""add_order_line_plan_history

Revision ID: 0d3417478bd2
Revises: 7586e7d836f1
Create Date: 2026-05-20 10:51:04.572608

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0d3417478bd2'
down_revision: Union[str, Sequence[str], None] = '7586e7d836f1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "order_line_plan_history",
        sa.Column("plan_history_id", sa.BigInteger(), nullable=False),
        sa.Column("order_line_id", sa.BigInteger(), nullable=False),
        sa.Column("plan_type", sa.String(length=40), nullable=False),
        sa.Column("ship_target_qty", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("available_inventory_qty", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("stock_ship_qty", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("production_qty", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_short_close", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("memo", sa.Text(), nullable=True),
        sa.Column("created_by", sa.String(length=80), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(
            ["order_line_id"],
            ["order_line.order_line_id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("plan_history_id"),
    )

    op.create_index(
        "ix_order_line_plan_history__created_at",
        "order_line_plan_history",
        ["created_at"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        "ix_order_line_plan_history__created_at",
        table_name="order_line_plan_history",
    )

    op.drop_table("order_line_plan_history")
"""add_order_line_fulfillment_plan_fields

Revision ID: 305c5f337ab3
Revises: e2dfe32c5350
Create Date: 2026-05-18 14:07:57.745863

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '305c5f337ab3'
down_revision: Union[str, Sequence[str], None] = 'e2dfe32c5350'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "order_line",
        sa.Column("fulfillment_mode", sa.String(length=24), nullable=True),
    )
    op.add_column(
        "order_line",
        sa.Column("production_policy", sa.String(length=24), nullable=True),
    )
    op.add_column(
        "order_line",
        sa.Column(
            "extra_production_qty",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )
    op.add_column(
        "order_line",
        sa.Column(
            "decision_made",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.add_column(
        "order_line",
        sa.Column("decision_made_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "order_line",
        sa.Column("decision_made_by", sa.String(length=100), nullable=True),
    )

    op.alter_column("order_line", "extra_production_qty", server_default=None)
    op.alter_column("order_line", "decision_made", server_default=None)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("order_line", "decision_made_by")
    op.drop_column("order_line", "decision_made_at")
    op.drop_column("order_line", "decision_made")
    op.drop_column("order_line", "extra_production_qty")
    op.drop_column("order_line", "production_policy")
    op.drop_column("order_line", "fulfillment_mode")
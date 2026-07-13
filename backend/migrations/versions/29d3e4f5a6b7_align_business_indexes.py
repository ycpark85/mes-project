"""align business indexes with query and integrity models

Revision ID: 29d3e4f5a6b7
Revises: 18c2d3e4f5a6
Create Date: 2026-07-14 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "29d3e4f5a6b7"
down_revision: Union[str, Sequence[str], None] = "18c2d3e4f5a6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


OLD_CREATED_AT_INDEX = "ix_order_line_plan_history__created_at"
LATEST_HISTORY_INDEX = "ix_order_line_plan_history__order_line_latest"


def upgrade() -> None:
    op.drop_index(
        OLD_CREATED_AT_INDEX,
        table_name="order_line_plan_history",
    )
    op.create_index(
        LATEST_HISTORY_INDEX,
        "order_line_plan_history",
        [
            "order_line_id",
            sa.text("created_at DESC"),
            sa.text("plan_history_id DESC"),
        ],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        LATEST_HISTORY_INDEX,
        table_name="order_line_plan_history",
    )
    op.create_index(
        OLD_CREATED_AT_INDEX,
        "order_line_plan_history",
        ["created_at"],
        unique=False,
    )

"""add discard qty to inspection result

Revision ID: c4f1a2b3d5e6
Revises: 9ac4f7d2b6e1
Create Date: 2026-06-15 12:45:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "c4f1a2b3d5e6"
down_revision: Union[str, Sequence[str], None] = "9ac4f7d2b6e1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "inspection_result",
        sa.Column(
            "discard_qty",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )
    op.create_check_constraint(
        "ck_inspection_result__discard_qty",
        "inspection_result",
        "discard_qty >= 0",
    )
    op.alter_column("inspection_result", "discard_qty", server_default=None)


def downgrade() -> None:
    op.drop_constraint(
        "ck_inspection_result__discard_qty",
        "inspection_result",
        type_="check",
    )
    op.drop_column("inspection_result", "discard_qty")

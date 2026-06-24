"""add uninspected qty to inspection result

Revision ID: b8e1c4d9a732
Revises: 7d2a5c9e8b10
Create Date: 2026-06-24 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b8e1c4d9a732"
down_revision: Union[str, Sequence[str], None] = "7d2a5c9e8b10"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "inspection_result",
        sa.Column(
            "uninspected_qty",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )
    op.create_check_constraint(
        "ck_inspection_result__uninspected_qty",
        "inspection_result",
        "uninspected_qty >= 0",
    )
    op.alter_column("inspection_result", "uninspected_qty", server_default=None)


def downgrade() -> None:
    op.drop_constraint(
        "ck_inspection_result__uninspected_qty",
        "inspection_result",
        type_="check",
    )
    op.drop_column("inspection_result", "uninspected_qty")

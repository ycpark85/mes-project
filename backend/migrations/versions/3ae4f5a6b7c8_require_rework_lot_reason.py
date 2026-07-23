"""require a reason for rework lots

Revision ID: 3ae4f5a6b7c8
Revises: 29d3e4f5a6b7
Create Date: 2026-07-14 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "3ae4f5a6b7c8"
down_revision: Union[str, Sequence[str], None] = "29d3e4f5a6b7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


CONSTRAINT_NAME = "ck_lot__rework_memo_required"


def upgrade() -> None:
    connection = op.get_bind()
    invalid_count = connection.execute(
        sa.text(
            """
            SELECT COUNT(*)
            FROM lot
            WHERE parent_lot_id IS NOT NULL
              AND NULLIF(TRIM(memo), '') IS NULL
            """
        )
    ).scalar_one()

    if int(invalid_count or 0) > 0:
        raise RuntimeError(
            "Rework LOT rows without a reason exist. "
            "Fill lot.memo before applying this migration."
        )

    op.create_check_constraint(
        CONSTRAINT_NAME,
        "lot",
        "parent_lot_id IS NULL OR NULLIF(TRIM(memo), '') IS NOT NULL",
    )


def downgrade() -> None:
    op.drop_constraint(CONSTRAINT_NAME, "lot", type_="check")

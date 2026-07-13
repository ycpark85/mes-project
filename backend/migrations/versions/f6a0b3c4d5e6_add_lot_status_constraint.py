"""add lot status constraint

Revision ID: f6a0b3c4d5e6
Revises: e5f9a2b3c4d5
Create Date: 2026-07-13 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


revision: str = "f6a0b3c4d5e6"
down_revision: Union[str, Sequence[str], None] = "e5f9a2b3c4d5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


CONSTRAINT_NAME = "ck_lot__status_enum"
STATUS_CHECK = (
    "status IN "
    "('WAITING','RECEIVED','IN_PROGRESS','PARTIAL_DONE','DONE','CANCELED')"
)


def upgrade() -> None:
    op.create_check_constraint(
        CONSTRAINT_NAME,
        "lot",
        STATUS_CHECK,
        postgresql_not_valid=True,
    )
    op.execute(f"ALTER TABLE lot VALIDATE CONSTRAINT {CONSTRAINT_NAME}")


def downgrade() -> None:
    op.drop_constraint(CONSTRAINT_NAME, "lot", type_="check")

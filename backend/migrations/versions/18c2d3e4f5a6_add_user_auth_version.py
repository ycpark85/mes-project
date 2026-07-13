"""add user authentication version

Revision ID: 18c2d3e4f5a6
Revises: 07b1c4d5e6f7
Create Date: 2026-07-13 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "18c2d3e4f5a6"
down_revision: Union[str, Sequence[str], None] = "07b1c4d5e6f7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "auth_version",
            sa.Integer(),
            server_default="1",
            nullable=False,
        ),
    )
    op.create_check_constraint(
        "ck_users__auth_version_positive",
        "users",
        "auth_version >= 1",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_users__auth_version_positive",
        "users",
        type_="check",
    )
    op.drop_column("users", "auth_version")

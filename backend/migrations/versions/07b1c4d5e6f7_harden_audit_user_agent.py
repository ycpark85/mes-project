"""harden audit user agent storage

Revision ID: 07b1c4d5e6f7
Revises: f6a0b3c4d5e6
Create Date: 2026-07-13 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "07b1c4d5e6f7"
down_revision: Union[str, Sequence[str], None] = "f6a0b3c4d5e6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


AUDIT_TABLES = ("auth_audit_logs", "vendor_portal_audit_log")


def upgrade() -> None:
    for table_name in AUDIT_TABLES:
        op.alter_column(
            table_name,
            "user_agent",
            existing_type=sa.String(length=500),
            type_=sa.Text(),
            existing_nullable=True,
        )
        op.add_column(
            table_name,
            sa.Column(
                "user_agent_truncated",
                sa.Boolean(),
                server_default=sa.false(),
                nullable=False,
            ),
        )


def downgrade() -> None:
    for table_name in reversed(AUDIT_TABLES):
        op.drop_column(table_name, "user_agent_truncated")
        op.execute(
            sa.text(
                f"UPDATE {table_name} "
                "SET user_agent = left(user_agent, 500) "
                "WHERE length(user_agent) > 500"
            )
        )
        op.alter_column(
            table_name,
            "user_agent",
            existing_type=sa.Text(),
            type_=sa.String(length=500),
            existing_nullable=True,
            postgresql_using="user_agent::varchar(500)",
        )

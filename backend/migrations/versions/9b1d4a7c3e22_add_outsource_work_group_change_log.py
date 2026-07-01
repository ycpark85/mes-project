"""add outsource work group change log

Revision ID: 9b1d4a7c3e22
Revises: 6c2e9f4a1b7d
Create Date: 2026-06-29 16:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "9b1d4a7c3e22"
down_revision: Union[str, Sequence[str], None] = "6c2e9f4a1b7d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "outsource_work_group_change_log",
        sa.Column("outsource_work_group_change_log_id", sa.BigInteger(), nullable=False),
        sa.Column("outsource_work_group_id", sa.BigInteger(), nullable=False),
        sa.Column("action_type", sa.String(length=30), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("before_data", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("after_data", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_by", sa.String(length=100), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["outsource_work_group_id"],
            ["outsource_work_group.outsource_work_group_id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("outsource_work_group_change_log_id"),
    )
    op.create_index(
        "ix_owg_change_log__work_group_id",
        "outsource_work_group_change_log",
        ["outsource_work_group_id"],
    )
    op.create_index(
        "ix_owg_change_log__created_at",
        "outsource_work_group_change_log",
        ["created_at"],
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        "ix_owg_change_log__created_at",
        table_name="outsource_work_group_change_log",
    )
    op.drop_index(
        "ix_owg_change_log__work_group_id",
        table_name="outsource_work_group_change_log",
    )
    op.drop_table("outsource_work_group_change_log")

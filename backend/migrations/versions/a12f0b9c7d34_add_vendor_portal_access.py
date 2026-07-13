"""add vendor portal access

Revision ID: a12f0b9c7d34
Revises: 9b1d4a7c3e22
Create Date: 2026-07-01 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a12f0b9c7d34"
down_revision: Union[str, Sequence[str], None] = "9b1d4a7c3e22"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "vendor_user_access",
        sa.Column("vendor_user_access_id", sa.BigInteger(), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("partner_id", sa.BigInteger(), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.user_id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["partner_id"],
            ["partner.partner_id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("vendor_user_access_id"),
        sa.UniqueConstraint(
            "user_id",
            "partner_id",
            name="uq_vendor_user_access__user_partner",
        ),
    )
    op.create_index(
        "ix_vendor_user_access__user_id",
        "vendor_user_access",
        ["user_id"],
    )
    op.create_index(
        "ix_vendor_user_access__partner_id",
        "vendor_user_access",
        ["partner_id"],
    )
    op.create_index(
        "ix_vendor_user_access__is_active",
        "vendor_user_access",
        ["is_active"],
    )

    op.create_table(
        "vendor_portal_audit_log",
        sa.Column("vendor_portal_audit_log_id", sa.BigInteger(), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=True),
        sa.Column("partner_id", sa.BigInteger(), nullable=True),
        sa.Column("outsource_work_group_id", sa.BigInteger(), nullable=True),
        sa.Column("action_type", sa.String(length=50), nullable=False),
        sa.Column("before_status", sa.String(length=30), nullable=True),
        sa.Column("after_status", sa.String(length=30), nullable=True),
        sa.Column("request_ip", sa.String(length=100), nullable=True),
        sa.Column("user_agent", sa.String(length=500), nullable=True),
        sa.Column("remark", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.user_id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["partner_id"],
            ["partner.partner_id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["outsource_work_group_id"],
            ["outsource_work_group.outsource_work_group_id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("vendor_portal_audit_log_id"),
    )
    op.create_index(
        "ix_vendor_portal_audit_log__user_id",
        "vendor_portal_audit_log",
        ["user_id"],
    )
    op.create_index(
        "ix_vendor_portal_audit_log__partner_id",
        "vendor_portal_audit_log",
        ["partner_id"],
    )
    op.create_index(
        "ix_vendor_portal_audit_log__work_group_id",
        "vendor_portal_audit_log",
        ["outsource_work_group_id"],
    )
    op.create_index(
        "ix_vendor_portal_audit_log__action_type",
        "vendor_portal_audit_log",
        ["action_type"],
    )
    op.create_index(
        "ix_vendor_portal_audit_log__created_at",
        "vendor_portal_audit_log",
        ["created_at"],
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        "ix_vendor_portal_audit_log__created_at",
        table_name="vendor_portal_audit_log",
    )
    op.drop_index(
        "ix_vendor_portal_audit_log__action_type",
        table_name="vendor_portal_audit_log",
    )
    op.drop_index(
        "ix_vendor_portal_audit_log__work_group_id",
        table_name="vendor_portal_audit_log",
    )
    op.drop_index(
        "ix_vendor_portal_audit_log__partner_id",
        table_name="vendor_portal_audit_log",
    )
    op.drop_index(
        "ix_vendor_portal_audit_log__user_id",
        table_name="vendor_portal_audit_log",
    )
    op.drop_table("vendor_portal_audit_log")

    op.drop_index("ix_vendor_user_access__is_active", table_name="vendor_user_access")
    op.drop_index("ix_vendor_user_access__partner_id", table_name="vendor_user_access")
    op.drop_index("ix_vendor_user_access__user_id", table_name="vendor_user_access")
    op.drop_table("vendor_user_access")


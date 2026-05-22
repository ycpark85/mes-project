"""add auth audit logs

Revision ID: 637b687acbfc
Revises: 54a2b8480a89
Create Date: 2026-05-22 17:25:43.999638

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '637b687acbfc'
down_revision: Union[str, Sequence[str], None] = '54a2b8480a89'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "auth_audit_logs",
        sa.Column("auth_audit_log_id", sa.BigInteger(), nullable=False),
        sa.Column("event_type", sa.String(length=50), nullable=False),
        sa.Column("login_id", sa.String(length=50), nullable=True),
        sa.Column("user_id", sa.BigInteger(), nullable=True),
        sa.Column("success", sa.Boolean(), nullable=False),
        sa.Column("reason", sa.String(length=100), nullable=True),
        sa.Column("client_ip", sa.String(length=100), nullable=True),
        sa.Column("user_agent", sa.String(length=500), nullable=True),
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
        sa.PrimaryKeyConstraint("auth_audit_log_id"),
    )

    op.create_index(
        "ix_auth_audit_logs__event_type",
        "auth_audit_logs",
        ["event_type"],
        unique=False,
    )
    op.create_index(
        "ix_auth_audit_logs__login_id",
        "auth_audit_logs",
        ["login_id"],
        unique=False,
    )
    op.create_index(
        "ix_auth_audit_logs__user_id",
        "auth_audit_logs",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        "ix_auth_audit_logs__success",
        "auth_audit_logs",
        ["success"],
        unique=False,
    )
    op.create_index(
        "ix_auth_audit_logs__created_at",
        "auth_audit_logs",
        ["created_at"],
        unique=False,
    )

def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_auth_audit_logs__created_at", table_name="auth_audit_logs")
    op.drop_index("ix_auth_audit_logs__success", table_name="auth_audit_logs")
    op.drop_index("ix_auth_audit_logs__user_id", table_name="auth_audit_logs")
    op.drop_index("ix_auth_audit_logs__login_id", table_name="auth_audit_logs")
    op.drop_index("ix_auth_audit_logs__event_type", table_name="auth_audit_logs")
    op.drop_table("auth_audit_logs")

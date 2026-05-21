"""add loging

Revision ID: 78577439f6e0
Revises: 0d3417478bd2
Create Date: 2026-05-21 13:39:45.115831

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '78577439f6e0'
down_revision: Union[str, Sequence[str], None] = '0d3417478bd2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "users",
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("login_id", sa.String(length=50), nullable=False),
        sa.Column("user_name", sa.String(length=100), nullable=False),
        sa.Column("password_hash", sa.String(length=500), nullable=False),
        sa.Column("department", sa.String(length=100), nullable=True),
        sa.Column("position", sa.String(length=100), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.PrimaryKeyConstraint("user_id"),
        sa.UniqueConstraint("login_id", name="uq_users__login_id"),
    )

    op.create_index("ix_users__login_id", "users", ["login_id"], unique=False)
    op.create_index("ix_users__user_name", "users", ["user_name"], unique=False)
    op.create_index("ix_users__is_active", "users", ["is_active"], unique=False)

    op.create_table(
        "roles",
        sa.Column("role_id", sa.BigInteger(), nullable=False),
        sa.Column("role_code", sa.String(length=50), nullable=False),
        sa.Column("role_name", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_system", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
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
        sa.PrimaryKeyConstraint("role_id"),
        sa.UniqueConstraint("role_code", name="uq_roles__role_code"),
    )

    op.create_index("ix_roles__role_code", "roles", ["role_code"], unique=False)
    op.create_index("ix_roles__role_name", "roles", ["role_name"], unique=False)
    op.create_index("ix_roles__is_active", "roles", ["is_active"], unique=False)

    op.create_table(
        "permissions",
        sa.Column("permission_id", sa.BigInteger(), nullable=False),
        sa.Column("permission_code", sa.String(length=100), nullable=False),
        sa.Column("menu_code", sa.String(length=50), nullable=False),
        sa.Column("action_code", sa.String(length=50), nullable=False),
        sa.Column("permission_name", sa.String(length=200), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
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
        sa.PrimaryKeyConstraint("permission_id"),
        sa.UniqueConstraint("permission_code", name="uq_permissions__permission_code"),
    )

    op.create_index(
        "ix_permissions__permission_code",
        "permissions",
        ["permission_code"],
        unique=False,
    )
    op.create_index("ix_permissions__menu_code", "permissions", ["menu_code"], unique=False)
    op.create_index(
        "ix_permissions__action_code",
        "permissions",
        ["action_code"],
        unique=False,
    )
    op.create_index(
        "ix_permissions__is_active",
        "permissions",
        ["is_active"],
        unique=False,
    )

    op.create_table(
        "user_roles",
        sa.Column("user_role_id", sa.BigInteger(), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("role_id", sa.BigInteger(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.user_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["role_id"], ["roles.role_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_role_id"),
        sa.UniqueConstraint(
            "user_id",
            "role_id",
            name="uq_user_roles__user_id__role_id",
        ),
    )

    op.create_index("ix_user_roles__user_id", "user_roles", ["user_id"], unique=False)
    op.create_index("ix_user_roles__role_id", "user_roles", ["role_id"], unique=False)

    op.create_table(
        "role_permissions",
        sa.Column("role_permission_id", sa.BigInteger(), nullable=False),
        sa.Column("role_id", sa.BigInteger(), nullable=False),
        sa.Column("permission_id", sa.BigInteger(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["role_id"], ["roles.role_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["permission_id"],
            ["permissions.permission_id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("role_permission_id"),
        sa.UniqueConstraint(
            "role_id",
            "permission_id",
            name="uq_role_permissions__role_id__permission_id",
        ),
    )

    op.create_index(
        "ix_role_permissions__role_id",
        "role_permissions",
        ["role_id"],
        unique=False,
    )
    op.create_index(
        "ix_role_permissions__permission_id",
        "role_permissions",
        ["permission_id"],
        unique=False,
    )

    op.alter_column("users", "is_active", server_default=None)
    op.alter_column("roles", "is_system", server_default=None)
    op.alter_column("roles", "is_active", server_default=None)
    op.alter_column("permissions", "sort_order", server_default=None)
    op.alter_column("permissions", "is_active", server_default=None)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_role_permissions__permission_id", table_name="role_permissions")
    op.drop_index("ix_role_permissions__role_id", table_name="role_permissions")
    op.drop_table("role_permissions")

    op.drop_index("ix_user_roles__role_id", table_name="user_roles")
    op.drop_index("ix_user_roles__user_id", table_name="user_roles")
    op.drop_table("user_roles")

    op.drop_index("ix_permissions__is_active", table_name="permissions")
    op.drop_index("ix_permissions__action_code", table_name="permissions")
    op.drop_index("ix_permissions__menu_code", table_name="permissions")
    op.drop_index("ix_permissions__permission_code", table_name="permissions")
    op.drop_table("permissions")

    op.drop_index("ix_roles__is_active", table_name="roles")
    op.drop_index("ix_roles__role_name", table_name="roles")
    op.drop_index("ix_roles__role_code", table_name="roles")
    op.drop_table("roles")

    op.drop_index("ix_users__is_active", table_name="users")
    op.drop_index("ix_users__user_name", table_name="users")
    op.drop_index("ix_users__login_id", table_name="users")
    op.drop_table("users")
"""add outsource work instruction tables

Revision ID: 6b07fc7ca640
Revises: 79f1202e05c1
Create Date: 2026-04-13 12:09:37.661161

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "6b07fc7ca640"
down_revision: Union[str, Sequence[str], None] = "79f1202e05c1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "outsource_work_instruction",
        sa.Column("outsource_work_instruction_id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("instruction_no", sa.String(length=50), nullable=False),
        sa.Column("instruction_date", sa.Date(), nullable=False),
        sa.Column("process_type", sa.String(length=20), nullable=False),
        sa.Column("partner_id", sa.BigInteger(), nullable=False),
        sa.Column("is_bundle", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("memo", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["partner_id"], ["partner.partner_id"], name="fk_outsource_work_instruction_partner_id"),
        sa.UniqueConstraint("instruction_no", name="uq_outsource_work_instruction_instruction_no"),
    )
    op.create_index(
        "ix_outsource_work_instruction_instruction_date",
        "outsource_work_instruction",
        ["instruction_date"],
        unique=False,
    )
    op.create_index(
        "ix_outsource_work_instruction_process_type",
        "outsource_work_instruction",
        ["process_type"],
        unique=False,
    )
    op.create_index(
        "ix_outsource_work_instruction_partner_id",
        "outsource_work_instruction",
        ["partner_id"],
        unique=False,
    )

    op.create_table(
        "outsource_work_instruction_item",
        sa.Column("outsource_work_instruction_item_id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("outsource_work_instruction_id", sa.BigInteger(), nullable=False),
        sa.Column("lot_id", sa.BigInteger(), nullable=False),
        sa.Column("process_type", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(
            ["outsource_work_instruction_id"],
            ["outsource_work_instruction.outsource_work_instruction_id"],
            name="fk_outsource_work_instruction_item_instruction_id",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["lot_id"],
            ["lot.lot_id"],
            name="fk_outsource_work_instruction_item_lot_id",
        ),
    )
    op.create_index(
        "ix_outsource_work_instruction_item_instruction_id",
        "outsource_work_instruction_item",
        ["outsource_work_instruction_id"],
        unique=False,
    )
    op.create_index(
        "ix_outsource_work_instruction_item_lot_id",
        "outsource_work_instruction_item",
        ["lot_id"],
        unique=False,
    )
    op.create_index(
        "ix_outsource_work_instruction_item_process_type",
        "outsource_work_instruction_item",
        ["process_type"],
        unique=False,
    )

    op.create_table(
        "outsource_work_instruction_file",
        sa.Column("outsource_work_instruction_file_id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("outsource_work_instruction_id", sa.BigInteger(), nullable=False),
        sa.Column("file_name", sa.String(length=255), nullable=False),
        sa.Column("file_path", sa.Text(), nullable=False),
        sa.Column("content_type", sa.String(length=100), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(
            ["outsource_work_instruction_id"],
            ["outsource_work_instruction.outsource_work_instruction_id"],
            name="fk_outsource_work_instruction_file_instruction_id",
            ondelete="CASCADE",
        ),
    )
    op.create_index(
        "ix_outsource_work_instruction_file_instruction_id",
        "outsource_work_instruction_file",
        ["outsource_work_instruction_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_outsource_work_instruction_file_instruction_id", table_name="outsource_work_instruction_file")
    op.drop_table("outsource_work_instruction_file")

    op.drop_index("ix_outsource_work_instruction_item_process_type", table_name="outsource_work_instruction_item")
    op.drop_index("ix_outsource_work_instruction_item_lot_id", table_name="outsource_work_instruction_item")
    op.drop_index("ix_outsource_work_instruction_item_instruction_id", table_name="outsource_work_instruction_item")
    op.drop_table("outsource_work_instruction_item")

    op.drop_index("ix_outsource_work_instruction_partner_id", table_name="outsource_work_instruction")
    op.drop_index("ix_outsource_work_instruction_process_type", table_name="outsource_work_instruction")
    op.drop_index("ix_outsource_work_instruction_instruction_date", table_name="outsource_work_instruction")
    op.drop_table("outsource_work_instruction")
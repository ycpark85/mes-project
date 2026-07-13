"""add business search indexes

Revision ID: e5f9a2b3c4d5
Revises: d4e8f1a2b3c4
Create Date: 2026-07-13 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


revision: str = "e5f9a2b3c4d5"
down_revision: Union[str, Sequence[str], None] = "d4e8f1a2b3c4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


INDEXES = (
    ("ix_partner__name_trgm", "partner", "name"),
    ("ix_product__product_code_trgm", "product", "product_code"),
    ("ix_product__product_name_trgm", "product", "product_name"),
)


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")

    for index_name, table_name, column_name in INDEXES:
        op.create_index(
            index_name,
            table_name,
            [column_name],
            unique=False,
            postgresql_using="gin",
            postgresql_ops={column_name: "gin_trgm_ops"},
        )


def downgrade() -> None:
    for index_name, table_name, _column_name in reversed(INDEXES):
        op.drop_index(index_name, table_name=table_name, postgresql_using="gin")

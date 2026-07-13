"""add raw material lot search index

Revision ID: d4e8f1a2b3c4
Revises: a12f0b9c7d34
Create Date: 2026-07-13 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d4e8f1a2b3c4"
down_revision: Union[str, Sequence[str], None] = "a12f0b9c7d34"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


INDEX_NAME = "ix_raw_material_inventory_movement__lot_no_trgm"


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    op.create_index(
        INDEX_NAME,
        "raw_material_inventory_movement",
        ["lot_no"],
        unique=False,
        postgresql_using="gin",
        postgresql_ops={"lot_no": "gin_trgm_ops"},
        postgresql_where=sa.text("lot_no IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index(
        INDEX_NAME,
        table_name="raw_material_inventory_movement",
        postgresql_using="gin",
    )

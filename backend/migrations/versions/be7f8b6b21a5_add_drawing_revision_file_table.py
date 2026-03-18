"""add drawing_revision_file table

Revision ID: be7f8b6b21a5
Revises: d191e7ff2e9a
Create Date: 2026-03-17 15:03:17.147676

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'be7f8b6b21a5'
down_revision: Union[str, Sequence[str], None] = 'd191e7ff2e9a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "drawing_revision_file",
        sa.Column("revision_file_id", sa.BigInteger(), primary_key=True),
        sa.Column("revision_id", sa.BigInteger(), nullable=False),
        sa.Column("file_kind", sa.String(length=20), nullable=False),
        sa.Column("file_uri", sa.String(length=500), nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("content_type", sa.String(length=100), nullable=True),
        sa.Column("file_size", sa.BigInteger(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["revision_id"], ["drawing_revision.revision_id"], ondelete="CASCADE"),
        sa.UniqueConstraint("revision_id", "file_kind", name="uq_drawing_revision_file__revision_id__file_kind"),
    )
    op.create_index("ix_drawing_revision_file__revision_id", "drawing_revision_file", ["revision_id"])
    op.create_index("ix_drawing_revision_file__file_kind", "drawing_revision_file", ["file_kind"])



def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_drawing_revision_file__file_kind", table_name="drawing_revision_file")
    op.drop_index("ix_drawing_revision_file__revision_id", table_name="drawing_revision_file")
    op.drop_table("drawing_revision_file")

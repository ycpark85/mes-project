"""add form snapshot json to outsource purchase order

Revision ID: 0c9eba3551b6
Revises: 81070df6e48c
Create Date: 2026-04-21 13:53:32.623718

"""
from typing import Sequence, Union
from sqlalchemy.dialects import postgresql
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0c9eba3551b6'
down_revision: Union[str, Sequence[str], None] = '81070df6e48c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "outsource_purchase_order",
        sa.Column(
            "form_snapshot_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("outsource_purchase_order", "form_snapshot_json")
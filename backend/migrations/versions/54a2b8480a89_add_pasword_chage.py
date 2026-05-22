"""add pasword chage 

Revision ID: 54a2b8480a89
Revises: ba6f7cdb0fd3
Create Date: 2026-05-22 12:07:02.590267

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '54a2b8480a89'
down_revision: Union[str, Sequence[str], None] = 'ba6f7cdb0fd3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "users",
        sa.Column(
            "password_change_required",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("users", "password_change_required")

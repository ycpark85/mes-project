"""change outsource work group seq to string

Revision ID: f281ce31f7bc
Revises: a7104deb3963
Create Date: 2026-04-29 18:34:20.489931

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f281ce31f7bc'
down_revision: Union[str, Sequence[str], None] = 'a7104deb3963'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.alter_column(
        "outsource_work_group",
        "group_seq",
        existing_type=sa.Integer(),
        type_=sa.String(length=20),
        existing_nullable=False,
        postgresql_using="group_seq::text",
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.alter_column(
        "outsource_work_group",
        "group_seq",
        existing_type=sa.String(length=20),
        type_=sa.Integer(),
        existing_nullable=False,
        postgresql_using="group_seq::integer",
    )

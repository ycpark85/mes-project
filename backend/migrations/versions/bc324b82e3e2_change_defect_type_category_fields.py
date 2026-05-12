"""change defect type category fields

Revision ID: bc324b82e3e2
Revises: dc3ca40c2a42
Create Date: 2026-05-11 14:45:42.453745

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'bc324b82e3e2'
down_revision: Union[str, Sequence[str], None] = 'dc3ca40c2a42'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "defect_type",
        sa.Column("category1_name", sa.String(length=200), nullable=True),
    )
    op.add_column(
        "defect_type",
        sa.Column("category2_name", sa.String(length=200), nullable=True),
    )

    op.execute(
        """
        UPDATE defect_type
        SET
            category1_name = '미분류',
            category2_name = name
        WHERE category1_name IS NULL
           OR category2_name IS NULL
        """
    )

    op.alter_column("defect_type", "category1_name", nullable=False)
    op.alter_column("defect_type", "category2_name", nullable=False)

    op.create_index(
        op.f("ix_defect_type_category1_name"),
        "defect_type",
        ["category1_name"],
        unique=False,
    )
    op.create_index(
        op.f("ix_defect_type_category2_name"),
        "defect_type",
        ["category2_name"],
        unique=False,
    )

    op.drop_index(op.f("ix_defect_type_name"), table_name="defect_type")
    op.drop_column("defect_type", "name")


def downgrade() -> None:
    """Downgrade schema."""
    op.add_column(
        "defect_type",
        sa.Column("name", sa.String(length=200), nullable=True),
    )

    op.execute(
        """
        UPDATE defect_type
        SET name = category2_name
        WHERE name IS NULL
        """
    )

    op.alter_column("defect_type", "name", nullable=False)
    op.create_index(op.f("ix_defect_type_name"), "defect_type", ["name"], unique=False)

    op.drop_index(op.f("ix_defect_type_category2_name"), table_name="defect_type")
    op.drop_index(op.f("ix_defect_type_category1_name"), table_name="defect_type")

    op.drop_column("defect_type", "category2_name")
    op.drop_column("defect_type", "category1_name")

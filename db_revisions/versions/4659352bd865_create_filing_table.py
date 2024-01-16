"""create filing table

Revision ID: 4659352bd865
Revises: 5a775dd75356
Create Date: 2024-01-08 14:42:44.052389

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "4659352bd865"
down_revision: Union[str, None] = "5a775dd75356"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "filing",
        sa.Column("id", sa.INTEGER, primary_key=True, autoincrement=True),
        sa.Column("lei", sa.String, nullable=False),
        sa.Column("state", sa.Enum("FILING_STARTED", "FILING_IN_PROGRESS", "FILING_COMPLETE", name="filingstate")),
        sa.Column("institution_snapshot_id", sa.String, nullable=False),
        sa.Column("filing_period", sa.Integer),
        sa.ForeignKeyConstraint(
            ["filing_period"],
            ["filing_period.id"],
        ),
    )


def downgrade() -> None:
    op.drop_table("filing")

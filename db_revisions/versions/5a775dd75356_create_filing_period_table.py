"""create filing period table

Revision ID: 5a775dd75356
Revises:
Create Date: 2024-01-08 13:49:42.475381

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "5a775dd75356"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "filing_period",
        sa.Column("id", sa.INTEGER, primary_key=True, autoincrement=True),
        sa.Column("name", sa.String, nullable=False),
        sa.Column("start_period", sa.DateTime, nullable=False),
        sa.Column("end_period", sa.DateTime, nullable=False),
        sa.Column("due", sa.DateTime, nullable=False),
        sa.Column("filing_type", sa.Enum("ANNUAL", name="filingtype"), server_default="ANNUAL"),
    )


def downgrade() -> None:
    op.drop_table("filing_period")

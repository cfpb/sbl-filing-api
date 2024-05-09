"""create filing task table

Revision ID: 4ca961a003e1
Revises: f30c5c3c7a42
Create Date: 2024-01-30 12:59:15.720135

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "4ca961a003e1"
down_revision: Union[str, None] = "f30c5c3c7a42"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "filing_task",
        sa.Column("name", sa.String, primary_key=True),
        sa.Column("task_order", sa.INTEGER, nullable=False),
    )


def downgrade() -> None:
    op.drop_table("filing_task")

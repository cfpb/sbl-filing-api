"""create filing task state table

Revision ID: 4e8ae26c1a22
Revises: 4ca961a003e1
Create Date: 2024-01-30 13:02:52.041229

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "4e8ae26c1a22"
down_revision: Union[str, None] = "4ca961a003e1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "filing_task_state",
        sa.Column("filing", sa.INTEGER, primary_key=True),
        sa.Column("task_name", sa.String, primary_key=True),
        sa.Column(
            "state",
            sa.Enum(
                "NOT_STARTED",
                "IN_PROGRESS",
                "COMPLETED",
                name="filingtaskstate",
            ),
        ),
        sa.Column("user", sa.String, nullable=False),
        sa.Column("change_timestamp", sa.DateTime, nullable=False),
        sa.ForeignKeyConstraint(
            ["filing"],
            ["filing.id"],
        ),
        sa.ForeignKeyConstraint(
            ["task_name"],
            ["filing_task.name"],
        ),
    )


def downgrade() -> None:
    op.drop_table("filing_task_state")

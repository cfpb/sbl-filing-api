"""create filing task state table

Revision ID: 4e8ae26c1a22
Revises: 4ca961a003e1
Create Date: 2024-01-30 13:02:52.041229

"""
from typing import Sequence, Union

from alembic import op, context
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "4e8ae26c1a22"
down_revision: Union[str, None] = "4ca961a003e1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "filing_task_state",
        sa.Column("id", sa.INTEGER, autoincrement=True),
        sa.Column("filing_period", sa.String),
        sa.Column("lei", sa.String),
        sa.Column("task_name", sa.String),
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
        sa.PrimaryKeyConstraint("id", name="filing_task_state_pkey"),
        sa.ForeignKeyConstraint(
            ["filing_period", "lei"], ["filing.filing_period", "filing.lei"], name="filing_task_state_filing_fkey"
        ),
        sa.ForeignKeyConstraint(["task_name"], ["filing_task.name"], name="filing_task_state_filing_task_fkey"),
    )


def downgrade() -> None:
    op.drop_table("filing_task_state")
    if "sqlite" not in context.get_context().dialect.name:
        op.execute(sa.DDL("DROP TYPE filingtaskstate"))

"""Add filing state

Revision ID: 7fe49d38726b
Revises: 6ec12afa5b37
Create Date: 2024-12-30 13:05:01.303998

"""

from typing import Sequence, Union

from alembic import op, context
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "7fe49d38726b"
down_revision: Union[str, None] = "6ec12afa5b37"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

filing_state_enum = postgresql.ENUM(
    "OPEN",
    "CLOSED",
    name="filingstate",
    create_type=False,
)


def upgrade() -> None:
    filing_state_enum.create(op.get_bind(), checkfirst=True)
    op.add_column(
        "filing",
        sa.Column("state", filing_state_enum),
    )

    op.create_table(
        "filing_reopen",
        sa.Column("user_action", sa.INTEGER, primary_key=True, unique=True, nullable=False),
        sa.Column("filing", sa.Integer, nullable=False),
        sa.PrimaryKeyConstraint("user_action", name="filing_reopen_pkey"),
        sa.ForeignKeyConstraint(["user_action"], ["user_action.id"], name="filing_reopen_user_action_fkey"),
        sa.ForeignKeyConstraint(["filing"], ["filing.id"], name="filing_reopen_filing_fkey"),
    )


def downgrade() -> None:
    op.drop_column("filing", "state")
    op.drop_table("filing_reopen")

    if "sqlite" not in context.get_context().dialect.name:
        op.execute(sa.DDL("DROP TYPE filingstate"))

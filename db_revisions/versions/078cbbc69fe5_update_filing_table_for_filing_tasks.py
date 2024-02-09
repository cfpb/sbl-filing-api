"""update filing table for filing tasks

Revision ID: 078cbbc69fe5
Revises: 4e8ae26c1a22
Create Date: 2024-01-30 13:15:44.323900

"""
from typing import Sequence, Union

from alembic import op, context
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "078cbbc69fe5"
down_revision: Union[str, None] = "4e8ae26c1a22"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_column("filing", "state")
    if "sqlite" not in context.get_context().dialect.name:
        op.execute(sa.DDL("DROP TYPE filingstate"))


def downgrade() -> None:
    op.add_column(
        "filing",
        sa.Column(
            "state",
            sa.Enum(
                "FILING_STARTED",
                "FILING_INSTITUTION_APPROVED",
                "FILING_IN_PROGRESS",
                "FILING_COMPLETE",
                name="filingstate",
            ),
        ),
    )

"""update filing table for contact info

Revision ID: 8eaef8ce4c23
Revises: 31e39764e3c0
Create Date: 2024-02-27 02:02:51.151599

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "8eaef8ce4c23"
down_revision: Union[str, None] = "31e39764e3c0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_column("filing", "contact_info")


def downgrade() -> None:
    op.add_column(
        "filing",
        sa.Column("contact_info", sa.String),
    )

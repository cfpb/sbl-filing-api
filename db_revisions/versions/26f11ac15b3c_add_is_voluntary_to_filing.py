"""add is_voluntary to filing

Revision ID: 26f11ac15b3c
Revises: f4091e4ce218
Create Date: 2024-10-16 15:15:41.261646

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "26f11ac15b3c"
down_revision: Union[str, None] = "f4091e4ce218"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("filing") as batch_op:
        batch_op.add_column(sa.Column("is_voluntary", sa.Boolean, server_default=sa.text("false"), nullable=False))


def downgrade() -> None:
    op.drop_column("filing", "is_voluntary")

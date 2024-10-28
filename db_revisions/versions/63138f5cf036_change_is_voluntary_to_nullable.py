"""change is_voluntary to nullable

Revision ID: 63138f5cf036
Revises: 26f11ac15b3c
Create Date: 2024-10-28 14:22:58.391354

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "63138f5cf036"
down_revision: Union[str, None] = "26f11ac15b3c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("filing", schema=None) as batch_op:
        batch_op.alter_column("is_voluntary", nullable=True)

    conn = op.get_bind()
    conn.execute(
        sa.text(
            """
            UPDATE filing SET is_voluntary = null
        """
        )
    )


def downgrade() -> None:
    with op.batch_alter_table("filing", schema=None) as batch_op:
        batch_op.alter_column("is_voluntary", nullable=False)

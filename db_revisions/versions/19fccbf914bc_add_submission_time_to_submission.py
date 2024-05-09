"""add submission time to submission

Revision ID: 19fccbf914bc
Revises: 078cbbc69fe5
Create Date: 2024-02-06 15:50:28.836237

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "19fccbf914bc"
down_revision: Union[str, None] = "078cbbc69fe5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("submission") as batch_op:
        batch_op.add_column(sa.Column("submission_time", sa.DateTime(), server_default=sa.func.now(), nullable=False))


def downgrade() -> None:
    op.drop_column("submission", "submission_time")

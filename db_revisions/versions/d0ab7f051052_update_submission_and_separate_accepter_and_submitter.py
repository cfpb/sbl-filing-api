"""update submission and separate accepter and submitter

Revision ID: d0ab7f051052
Revises: 7a1b7eab0167
Create Date: 2024-03-27 15:58:16.294508

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "d0ab7f051052"
down_revision: Union[str, None] = "7a1b7eab0167"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_column("submission", "accepter")
    op.drop_column("submission", "submitter")


def downgrade() -> None:
    op.add_column("submission", sa.Column("accepter", sa.String, nullable=True))
    op.add_column("submission", sa.Column("submitter", sa.String, nullable=True))

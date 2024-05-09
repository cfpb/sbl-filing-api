"""add total records to submission

Revision ID: 7356a7d7036d
Revises: c7238487f08d
Create Date: 2024-05-07 11:02:46.846411

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "7356a7d7036d"
down_revision: Union[str, None] = "c7238487f08d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("submission") as batch_op:
        batch_op.add_column(sa.Column("total_records", sa.Integer, nullable=True))


def downgrade() -> None:
    op.drop_column("submission", "total_records")

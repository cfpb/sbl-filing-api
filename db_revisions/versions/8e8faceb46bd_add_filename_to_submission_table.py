"""add filename to submission table

Revision ID: 8e8faceb46bd
Revises: bbc51b08d22f
Create Date: 2024-03-06 10:43:59.261556

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "8e8faceb46bd"
down_revision: Union[str, None] = "bbc51b08d22f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("submission") as batch_op:
        batch_op.add_column(sa.Column("filename", sa.String, nullable=False))


def downgrade() -> None:
    op.drop_column("submission", "filename")

"""add extension to contactinfo

Revision ID: ba8234fe9eb5
Revises: 7356a7d7036d
Create Date: 2024-09-24 12:26:46.755693

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "ba8234fe9eb5"
down_revision: Union[str, None] = "7356a7d7036d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("contact_info") as batch_op:
        batch_op.add_column(sa.Column("phone_ext", sa.String(254), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("contact_info") as batch_op:
        batch_op.drop_column("phone_ext")

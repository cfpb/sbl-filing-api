"""add hq_address_street_3 and hq_address_street_4 to contact_info table

Revision ID: 2e81179924b5
Revises: ffd779216f6d
Create Date: 2024-04-08 23:41:54.305693

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "2e81179924b5"
down_revision: Union[str, None] = "ffd779216f6d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("contact_info") as batch_op:
        batch_op.add_column(sa.Column("hq_address_street_3", sa.String, nullable=True))
        batch_op.add_column(sa.Column("hq_address_street_4", sa.String, nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("contact_info") as batch_op:
        batch_op.drop_column("hq_address_street_3")
        batch_op.drop_column("hq_address_street_4")

"""Set character limit in contact info

Revision ID: 6babc6109a5a
Revises: ba8234fe9eb5
Create Date: 2024-10-07 16:33:18.213745

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "6babc6109a5a"
down_revision: Union[str, None] = "ba8234fe9eb5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("contact_info", schema=None) as batch_op:
        batch_op.alter_column("first_name", type_=sa.String(255), nullable=False)
        batch_op.alter_column("last_name", type_=sa.String(255), nullable=False)
        batch_op.alter_column("hq_address_street_1", type_=sa.String(255), nullable=False)
        batch_op.alter_column("hq_address_street_2", type_=sa.String(255), nullable=True)
        batch_op.alter_column("hq_address_street_3", type_=sa.String(255), nullable=True)
        batch_op.alter_column("hq_address_street_4", type_=sa.String(255), nullable=True)
        batch_op.alter_column("hq_address_city", type_=sa.String(255), nullable=False)
        batch_op.alter_column("hq_address_state", type_=sa.String(255), nullable=False)
        batch_op.alter_column("email", type_=sa.String(255), nullable=False)
        batch_op.alter_column("phone_number", type_=sa.String(255), nullable=False)
        batch_op.alter_column("phone_ext", type_=sa.String(255), nullable=True)


def downgrade() -> None:
    with op.batch_alter_table("contact_info", schema=None) as batch_op:
        batch_op.alter_column("first_name", type_=sa.String, nullable=False)
        batch_op.alter_column("last_name", type_=sa.String, nullable=False)
        batch_op.alter_column("hq_address_street_1", type_=sa.String, nullable=False)
        batch_op.alter_column("hq_address_street_2", type_=sa.String, nullable=True)
        batch_op.alter_column("hq_address_street_3", type_=sa.String, nullable=True)
        batch_op.alter_column("hq_address_street_4", type_=sa.String, nullable=True)
        batch_op.alter_column("hq_address_city", type_=sa.String, nullable=False)
        batch_op.alter_column("hq_address_state", type_=sa.String, nullable=False)
        batch_op.alter_column("email", type_=sa.String, nullable=False)
        batch_op.alter_column("phone_number", type_=sa.String, nullable=False)
        batch_op.alter_column("phone_ext", type_=sa.String, nullable=True)

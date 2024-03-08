"""create contact info table

Revision ID: 31e39764e3c0
Revises: 19fccbf914bc
Create Date: 2024-02-27 01:35:08.209400

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "31e39764e3c0"
down_revision: Union[str, None] = "8e8faceb46bd"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "contact_info",
        sa.Column("id", sa.INTEGER, autoincrement=True),
        sa.Column("filing", sa.Integer, unique=True),
        sa.Column("first_name", sa.String, nullable=False),
        sa.Column("last_name", sa.String, nullable=False),
        sa.Column("hq_address_street_1", sa.String, nullable=False),
        sa.Column("hq_address_street_2", sa.String, nullable=True),
        sa.Column("hq_address_city", sa.String, nullable=False),
        sa.Column("hq_address_state", sa.String, nullable=False),
        sa.Column("hq_address_zip", sa.String, nullable=False),
        sa.Column("email", sa.String, nullable=False),
        sa.Column("phone", sa.String, nullable=False),
        sa.PrimaryKeyConstraint("id", name="contact_info_pkey"),
        sa.ForeignKeyConstraint(["filing"], ["filing.id"], name="contact_info_filing_fkey"),
    )


def downgrade() -> None:
    op.drop_table("contact_info")

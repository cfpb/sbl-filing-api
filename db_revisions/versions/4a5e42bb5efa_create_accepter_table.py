"""create accepter table

Revision ID: 4a5e42bb5efa
Revises: d0ab7f051052
Create Date: 2024-04-02 01:37:29.437393

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "4a5e42bb5efa"
down_revision: Union[str, None] = "d0ab7f051052"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "accepter",
        sa.Column("id", sa.INTEGER, autoincrement=True),
        sa.Column("accepter", sa.String, nullable=False),
        sa.Column("accepter_name", sa.String, nullable=True),
        sa.Column("accepter_email", sa.String, nullable=False),
        sa.Column("submission", sa.Integer, unique=True),
        sa.Column("acception_time", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="accepter_pkey"),
        sa.ForeignKeyConstraint(["submission"], ["submission.id"], name="accepter_submission_fkey"),
    )


def downgrade() -> None:
    op.drop_table("accepter")

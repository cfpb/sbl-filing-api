"""create submitter table

Revision ID: ffd779216f6d
Revises: 4a5e42bb5efa
Create Date: 2024-04-03 16:04:42.792340

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "ffd779216f6d"
down_revision: Union[str, None] = "4a5e42bb5efa"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "submitter",
        sa.Column("id", sa.INTEGER, autoincrement=True),
        sa.Column("submitter", sa.String, nullable=False),
        sa.Column("submitter_name", sa.String, nullable=True),
        sa.Column("submitter_email", sa.String, nullable=False),
        sa.Column("submission", sa.Integer, unique=True),
        sa.PrimaryKeyConstraint("id", name="submitter_pkey"),
        sa.ForeignKeyConstraint(["submission"], ["submission.id"], name="submitter_submission_fkey"),
    )


def downgrade() -> None:
    op.drop_table("submitter")

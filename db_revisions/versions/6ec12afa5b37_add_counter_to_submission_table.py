"""add counter to submission table

Revision ID: 6ec12afa5b37
Revises: 26f11ac15b3c
Create Date: 2024-10-28 10:52:22.353469

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "6ec12afa5b37"
down_revision: Union[str, None] = "63138f5cf036"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # create the new column as nullable so it doesn't error with existing data
    with op.batch_alter_table("submission", schema=None) as batch_op:
        batch_op.add_column(sa.Column("counter", sa.Integer, nullable=True))
        batch_op.create_unique_constraint("unique_filing_counter", ["filing", "counter"])

    # run a counter of each submission in a given filing id, ordered by the submission id,
    # which is the PK incrementor.  This will give us accurate counts of 1, 2, 3, ... for
    # each submission per filing id.
    conn = op.get_bind()
    conn.execute(
        sa.text(
            """
        WITH counts AS (
            SELECT id, filing, ROW_NUMBER() OVER (PARTITION BY filing ORDER BY id) AS row_num FROM submission
        )
        UPDATE submission SET counter = counts.row_num
        FROM counts
        WHERE submission.id = counts.id
        """
        )
    )

    # set the counter column to required now that existing data is set.
    with op.batch_alter_table("submission", schema=None) as batch_op:
        batch_op.alter_column("counter", nullable=False)


def downgrade() -> None:
    op.drop_constraint(constraint_name="unique_filing_counter", table_name="submission")
    op.drop_column("submission", "counter")

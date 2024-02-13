"""refactor lei and period as keys

Revision ID: 83e1a5a70b11
Revises: 19fccbf914bc
Create Date: 2024-02-12 18:47:17.917907

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "83e1a5a70b11"
down_revision: Union[str, None] = "19fccbf914bc"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("filing_period") as batch_op:
        batch_op.drop_constraint("filing_period_pkey", type_="primary")
        batch_op.drop_column("id")
        batch_op.create_primary_key("filing_period_pkey", ["name"])

    with op.batch_alter_table("filing") as batch_op:
        batch_op.drop_constraint("filing_filing_period_fkey", "foreignkey")
        batch_op.alter_column("filing_period", type_=sa.String)
        batch_op.create_primary_key("filing_pkey", ["lei", "filing_period"])
        batch_op.drop_column("id")
        batch_op.create_foreign_key(
            "filing_filing_period_fkey",
            "filing_period",
            ["filing_period"],
            ["name"],
        )

    with op.batch_alter_table("submission") as batch_op:
        batch_op.drop_constraint("submission_filing_fkey", "foreignkey")
        batch_op.drop_column("filing")
        batch_op.add_column(sa.Column("filing_period", sa.String))
        batch_op.add_column(sa.Column("lei", sa.String))
        batch_op.create_foreign_key(
            "submission_filing_fkey",
            "filing",
            ["filing_period", "lei"],
            ["filing_period", "lei"],
        )

    with op.batch_alter_table("filing_task_state") as batch_op:
        batch_op.drop_constraint("filing_task_state_pkey", "primary")
        batch_op.add_column(sa.Column("id", sa.INTEGER, primary_key=True, autoincrement=True))
        batch_op.create_primary_key("filing_task_state_pkey", ["id"])
        batch_op.drop_constraint("filing_task_state_filing_fkey", "foreignkey")
        batch_op.drop_column("filing")
        batch_op.add_column(sa.Column("filing_period", sa.String))
        batch_op.add_column(sa.Column("lei", sa.String))
        batch_op.create_foreign_key(
            "filing_task_state_filing_fkey",
            "filing",
            ["filing_period", "lei"],
            ["filing_period", "lei"],
        )


def downgrade() -> None:
    with op.batch_alter_table("filing_period") as batch_op:
        batch_op.drop_constraint("filing_period_pkey", type_="primary")
        batch_op.add_column(sa.Column("id", sa.Integer, primary_key=True, autoincrement=True))
        batch_op.create_primary_key("filing_period_pkey", ["id"])

    with op.batch_alter_table("filing") as batch_op:
        batch_op.drop_constraint("filing_filing_period_fkey", "foreignkey")
        batch_op.alter_column("filing_period", type_=sa.Integer)
        batch_op.add_column(sa.Column("id", sa.Integer, primary_key=True, autoincrement=True))
        batch_op.drop_constraint("filing_pkey", "primary")
        batch_op.create_primary_key("filing_pkey", ["id"])
        batch_op.create_foreign_key(
            "filing_filing_period_fkey",
            "filing_period",
            ["filing_period"],
            ["id"],
        )

    with op.batch_alter_table("submission") as batch_op:
        batch_op.drop_constraint("submission_filing_fkey", "foreignkey")
        batch_op.add_column(sa.Column("filing", sa.Integer))
        batch_op.drop_column("filing_period")
        batch_op.drop_column("lei")
        batch_op.create_foreign_key(
            "submission_filing_fkey",
            "filing",
            ["filing"],
            ["id"],
        )

    with op.batch_alter_table("filing_task_state") as batch_op:
        batch_op.drop_constraint("filing_task_state_pkey", "primary")
        batch_op.drop_column("id")
        batch_op.add_column(sa.Column("filing", sa.INTEGER))
        batch_op.create_primary_key("filing_task_state_pkey", ["filing", "task_name"])
        batch_op.drop_constraint("filing_task_state_filing_fkey", "foreignkey")
        batch_op.drop_column("filing_period")
        batch_op.drop_column("lei")
        batch_op.create_foreign_key(
            "filing_task_state_filing_fkey",
            "filing",
            ["filing"],
            ["id"],
        )

"""240304 change filing_task_state to filing_task_progress

Revision ID: bbc51b08d22f
Revises: 19fccbf914bc
Create Date: 2024-03-04 12:02:27.253888

"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "bbc51b08d22f"
down_revision: Union[str, None] = "19fccbf914bc"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.rename_table("filing_task_state", "filing_task_progress")
    with op.batch_alter_table("filing_task_progress") as batch_op:
        batch_op.drop_constraint("filing_task_state_pkey")
        batch_op.drop_constraint("filing_task_state_filing_fkey")
        batch_op.drop_constraint("filing_task_state_filing_task_fkey")
        batch_op.create_primary_key("filing_task_progress_pkey", ["id"])
        batch_op.create_foreign_key("filing_task_progress_filing_fkey", "filing", ["filing"], ["id"])
        batch_op.create_foreign_key("filing_task_progress_filing_task_fkey", "filing_task", ["task_name"], ["name"])


def downgrade() -> None:
    op.rename_table("filing_task_progress", "filing_task_state")
    with op.batch_alter_table("filing_task_state") as batch_op:
        batch_op.drop_constraint("filing_task_progress_pkey")
        batch_op.drop_constraint("filing_task_progress_filing_fkey")
        batch_op.drop_constraint("filing_task_progress_filing_task_fkey")
        batch_op.create_primary_key("filing_task_state_pkey", ["id"])
        batch_op.create_foreign_key("filing_task_state_filing_fkey", "filing", ["filing"], ["id"])
        batch_op.create_foreign_key("filing_task_state_filing_task_fkey", "filing_task", ["task_name"], ["name"])

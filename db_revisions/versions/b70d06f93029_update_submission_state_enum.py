"""update submission state enum

Revision ID: b70d06f93029
Revises: 8eaef8ce4c23
Create Date: 2024-03-13 11:41:42.122257

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "b70d06f93029"
down_revision: Union[str, None] = "8eaef8ce4c23"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

old_options = (
    "SUBMISSION_UPLOADED",
    "VALIDATION_IN_PROGRESS",
    "VALIDATION_WITH_ERRORS",
    "VALIDATION_WITH_WARNINGS",
    "VALIDATION_SUCCESSFUL",
    "SUBMISSION_SIGNED",
)
new_options = sorted(old_options + ("SUBMISSION_STARTED",))


def upgrade() -> None:
    with op.batch_alter_table("submission", schema=None) as batch_op:
        batch_op.alter_column(
            "state",
            type_=sa.Enum(*new_options, name="submissionstate"),
            existing_type=sa.Enum(*old_options, name="submissionstate"),
            existing_server_default=sa.text("'text'"),
        )


def downgrade() -> None:
    with op.batch_alter_table("submission", schema=None) as batch_op:
        batch_op.alter_column(
            "state",
            type_=sa.Enum(*old_options, name="submissionstate"),
            existing_type=sa.Enum(*new_options, name="submissionstate"),
            existing_server_default=sa.text("'text'"),
        )

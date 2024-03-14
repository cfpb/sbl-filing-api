"""certify updates

Revision ID: 7a1b7eab0167
Revises: b3bfb504ae7e
Create Date: 2024-03-13 14:38:34.324557

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "7a1b7eab0167"
down_revision: Union[str, None] = "b3bfb504ae7e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


old_options = (
    "SUBMISSION_SIGNED",
    "SUBMISSION_STARTED",
    "SUBMISSION_UPLOADED",
    "VALIDATION_IN_PROGRESS",
    "VALIDATION_WITH_ERRORS",
    "VALIDATION_WITH_WARNINGS",
    "VALIDATION_SUCCESSFUL",
)
new_options = (
    "SUBMISSION_CERTIFIED",
    "SUBMISSION_STARTED",
    "SUBMISSION_UPLOADED",
    "VALIDATION_IN_PROGRESS",
    "VALIDATION_WITH_ERRORS",
    "VALIDATION_WITH_WARNINGS",
    "VALIDATION_SUCCESSFUL",
)


def upgrade() -> None:
    with op.batch_alter_table("submission", schema=None) as batch_op:
        batch_op.alter_column(
            "state",
            type_=sa.Enum(*new_options, name="submissionstate"),
            existing_type=sa.Enum(*old_options, name="submissionstate"),
            existing_server_default=sa.text("'text'"),
        )
        batch_op.add_column(sa.Column("certifier", sa.String))


def downgrade() -> None:
    with op.batch_alter_table("submission", schema=None) as batch_op:
        batch_op.alter_column(
            "state",
            type_=sa.Enum(*old_options, name="submissionstate"),
            existing_type=sa.Enum(*new_options, name="submissionstate"),
            existing_server_default=sa.text("'text'"),
        )
        batch_op.drop_column("certifier")

"""Add VALIDATION_EXPIRED state

Revision ID: 0040045eae14
Revises: fb46d55283d6
Create Date: 2024-04-11 13:08:20.850470

"""

from typing import Sequence, Union

from alembic import op, context
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0040045eae14"
down_revision: Union[str, None] = "ccc50ec18a7e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

old_submission_state = postgresql.ENUM(
    "SUBMISSION_ACCEPTED",
    "SUBMISSION_STARTED",
    "SUBMISSION_UPLOADED",
    "SUBMISSION_UPLOAD_MALFORMED",
    "VALIDATION_IN_PROGRESS",
    "VALIDATION_WITH_ERRORS",
    "VALIDATION_WITH_WARNINGS",
    "VALIDATION_SUCCESSFUL",
    name="submissionstate",
    create_type=False,
)

new_submission_state = postgresql.ENUM(
    "SUBMISSION_ACCEPTED",
    "SUBMISSION_STARTED",
    "SUBMISSION_UPLOADED",
    "SUBMISSION_UPLOAD_MALFORMED",
    "VALIDATION_IN_PROGRESS",
    "VALIDATION_WITH_ERRORS",
    "VALIDATION_WITH_WARNINGS",
    "VALIDATION_SUCCESSFUL",
    "VALIDATION_EXPIRED",
    "UPLOAD_FAILED",
    name="submissionstate",
    create_type=False,
)


def upgrade() -> None:
    if "sqlite" not in context.get_context().dialect.name:
        op.execute("ALTER TYPE submissionstate RENAME TO submissionstate_old")
        new_submission_state.create(op.get_bind(), checkfirst=True)
        op.execute("ALTER TABLE submission ALTER COLUMN state TYPE submissionstate USING state::text::submissionstate")
        op.execute("DROP TYPE submissionstate_old")


def downgrade() -> None:
    if "sqlite" not in context.get_context().dialect.name:
        op.execute("ALTER TYPE submissionstate RENAME TO submissionstate_old")
        old_submission_state.create(op.get_bind(), checkfirst=True)
        op.execute("ALTER TABLE submission ALTER COLUMN state TYPE submissionstate USING state::text::submissionstate")
        op.execute("DROP TYPE submissionstate_old")

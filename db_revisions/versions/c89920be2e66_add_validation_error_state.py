"""Add VALIDATION_ERROR state

Revision ID: c89920be2e66
Revises: 3f7e610035a6
Create Date: 2024-04-18 13:06:48.162639

"""

from typing import Sequence, Union

from alembic import op, context
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "c89920be2e66"
down_revision: Union[str, None] = "3f7e610035a6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


old_submission_state = postgresql.ENUM(
    "SUBMISSION_ACCEPTED",
    "SUBMISSION_STARTED",
    "SUBMISSION_UPLOADED",
    "SUBMISSION_UPLOAD_MALFORMED",
    "UPLOAD_FAILED",
    "VALIDATION_EXPIRED",
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
    "UPLOAD_FAILED",
    "VALIDATION_EXPIRED",
    "VALIDATION_IN_PROGRESS",
    "VALIDATION_WITH_ERRORS",
    "VALIDATION_WITH_WARNINGS",
    "VALIDATION_SUCCESSFUL",
    "VALIDATION_ERROR",
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

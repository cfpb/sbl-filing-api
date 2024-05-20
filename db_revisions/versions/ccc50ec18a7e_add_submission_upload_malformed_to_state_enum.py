"""add SUBMISSION_UPLOAD_MALFORMED to state enum

Revision ID: ccc50ec18a7e
Revises: 11dfc8200daa
Create Date: 2024-04-07 01:02:13.310717

"""

from typing import Sequence, Union

from alembic import op, context
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "ccc50ec18a7e"
down_revision: Union[str, None] = "fb46d55283d6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


old_submission_state = postgresql.ENUM(
    "SUBMISSION_ACCEPTED",
    "SUBMISSION_STARTED",
    "SUBMISSION_UPLOADED",
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
    "VALIDATION_IN_PROGRESS",
    "VALIDATION_WITH_ERRORS",
    "VALIDATION_WITH_WARNINGS",
    "VALIDATION_SUCCESSFUL",
    "SUBMISSION_UPLOAD_MALFORMED",
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

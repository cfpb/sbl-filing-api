"""Add VALIDATION_ERROR state

Revision ID: c89920be2e66
Revises: 3f7e610035a6
Create Date: 2024-04-18 13:06:48.162639

"""
from typing import Sequence, Union

from alembic import op, context


# revision identifiers, used by Alembic.
revision: str = "c89920be2e66"
down_revision: Union[str, None] = "3f7e610035a6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# fmt: off
old_options = (
    'SUBMISSION_ACCEPTED',
    'SUBMISSION_STARTED',
    'SUBMISSION_UPLOADED',
    'SUBMISSION_UPLOAD_MALFORMED',
    'UPLOAD_FAILED',
    'VALIDATION_EXPIRED',
    'VALIDATION_IN_PROGRESS',
    'VALIDATION_WITH_ERRORS',
    'VALIDATION_WITH_WARNINGS',
    'VALIDATION_SUCCESSFUL',
)
new_options = tuple(sorted(old_options + ('VALIDATION_ERROR',)))
# fmt: on


def upgrade() -> None:
    if "sqlite" not in context.get_context().dialect.name:
        op.execute("ALTER TYPE submissionstate RENAME TO submissionstate_old")
        op.execute(f"CREATE TYPE submissionstate AS ENUM{new_options}")
        op.execute("ALTER TABLE submission ALTER COLUMN state TYPE submissionstate USING state::text::submissionstate")
        op.execute("DROP TYPE submissionstate_old")


def downgrade() -> None:
    if "sqlite" not in context.get_context().dialect.name:
        op.execute("ALTER TYPE submissionstate RENAME TO submissionstate_old")
        op.execute(f"CREATE TYPE submissionstate AS ENUM{old_options}")
        op.execute("ALTER TABLE submission ALTER COLUMN state TYPE submissionstate USING state::text::submissionstate")
        op.execute("DROP TYPE submissionstate_old")

"""Add VALIDATION_EXPIRED state

Revision ID: 0040045eae14
Revises: fb46d55283d6
Create Date: 2024-04-11 13:08:20.850470

"""
from typing import Sequence, Union

from alembic import op, context


# revision identifiers, used by Alembic.
revision: str = "0040045eae14"
down_revision: Union[str, None] = "ccc50ec18a7e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# fmt: off
old_options = (
    'SUBMISSION_ACCEPTED',
    'SUBMISSION_STARTED',
    'SUBMISSION_UPLOADED',
    'SUBMISSION_UPLOAD_MALFORMED',
    'VALIDATION_IN_PROGRESS',
    'VALIDATION_WITH_ERRORS',
    'VALIDATION_WITH_WARNINGS',
    'VALIDATION_SUCCESSFUL',
)
new_options = tuple(sorted(old_options + ('VALIDATION_EXPIRED','UPLOAD_FAILED')))
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

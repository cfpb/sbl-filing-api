"""accept updates

Revision ID: 7a1b7eab0167
Revises: b3bfb504ae7e
Create Date: 2024-03-13 14:38:34.324557

"""

from typing import Sequence, Union

from alembic import op, context
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "7a1b7eab0167"
down_revision: Union[str, None] = "b3bfb504ae7e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


old_submission_state = postgresql.ENUM(
    "SUBMISSION_SIGNED",
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
    name="submissionstate",
    create_type=False,
)


def upgrade() -> None:
    if "sqlite" not in context.get_context().dialect.name:
        op.execute("ALTER TYPE submissionstate RENAME TO submissionstate_old")
        new_submission_state.create(op.get_bind(), checkfirst=True)
        op.execute("ALTER TABLE submission ALTER COLUMN state TYPE submissionstate USING state::text::submissionstate")
        op.execute("DROP TYPE submissionstate_old")
    op.add_column("submission", sa.Column("accepter", sa.String))


def downgrade() -> None:
    if "sqlite" not in context.get_context().dialect.name:
        op.execute("ALTER TYPE submissionstate RENAME TO submissionstate_old")
        old_submission_state.create(op.get_bind(), checkfirst=True)
        op.execute("ALTER TABLE submission ALTER COLUMN state TYPE submissionstate USING state::text::submissionstate")
        op.execute("DROP TYPE submissionstate_old")
    op.drop_column("submission", "accepter")

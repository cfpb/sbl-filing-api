"""updates for signing filing

Revision ID: 0581ef952d37
Revises: 8eaef8ce4c23
Create Date: 2024-03-13 11:26:55.619109

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0581ef952d37'
down_revision: Union[str, None] = '8eaef8ce4c23'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_column("submission", "confirmation_id")
    op.add_column("filing", sa.Column("confirmation_id", sa.String))
    op.drop_column("submission", "state")
    op.add_column("submission", sa.Column(
            "state",
            sa.Enum(
                "SUBMISSION_UPLOADED",
                "VALIDATION_IN_PROGRESS",
                "VALIDATION_WITH_ERRORS",
                "VALIDATION_WITH_WARNINGS",
                "VALIDATION_SUCCESSFUL",
                "SUBMISSION_CERTIFIED",
                name="submissionstate",
            ),
        ))


def downgrade() -> None:
    op.add_column("submission", sa.Column("confirmation_id", sa.String))
    op.drop_column("filing", "confirmation_id")
    op.drop_column("submission", "state")
    op.add_column("submission", sa.Column(
            "state",
            sa.Enum(
                "SUBMISSION_UPLOADED",
                "VALIDATION_IN_PROGRESS",
                "VALIDATION_WITH_ERRORS",
                "VALIDATION_WITH_WARNINGS",
                "VALIDATION_SUCCESSFUL",
                "SUBMISSION_SIGNED",
                name="submissionstate",
            ),
        ))
    

"""create submission tables

Revision ID: f30c5c3c7a42
Revises: 4659352bd865
Create Date: 2023-12-12 12:40:14.501180

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "f30c5c3c7a42"
down_revision: Union[str, None] = "4659352bd865"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "submission",
        sa.Column("id", sa.INTEGER, autoincrement=True),
        sa.Column("submitter", sa.String, nullable=False),
        sa.Column(
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
        ),
        sa.Column("validation_ruleset_version", sa.String),
        sa.Column("validation_json", sa.JSON),
        sa.Column("filing_period", sa.String),
        sa.Column("lei", sa.String),
        sa.Column("confirmation_id", sa.String),
        sa.PrimaryKeyConstraint("id", name="submission_pkey"),
        sa.ForeignKeyConstraint(["filing_period", "lei"], ["filing.filing_period","filing.lei"], name="submission_filing_fkey"),
    )


def downgrade() -> None:
    op.drop_table("submission")

"""add signature table

Revision ID: fb46d55283d6
Revises: ffd779216f6d
Create Date: 2024-03-13 11:41:47.815220

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "fb46d55283d6"
down_revision: Union[str, None] = "2e81179924b5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "signature",
        sa.Column("id", sa.INTEGER, autoincrement=True),
        sa.Column("filing", sa.Integer),
        sa.Column("signer_id", sa.String, nullable=False),
        sa.Column("signer_name", sa.String),
        sa.Column("signer_email", sa.String, nullable=False),
        sa.Column("signed_date", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="signature_pkey"),
        sa.ForeignKeyConstraint(["filing"], ["filing.id"], name="signature_filing_fkey"),
    )


def downgrade() -> None:
    op.drop_table("signature")

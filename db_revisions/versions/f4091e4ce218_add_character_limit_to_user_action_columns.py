"""Add character limit to user_action columns

Revision ID: f4091e4ce218
Revises: 6babc6109a5a
Create Date: 2024-10-08 01:33:25.832473

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "f4091e4ce218"
down_revision: Union[str, None] = "6babc6109a5a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("user_action", schema=None) as batch_op:
        batch_op.alter_column(
            "user_name",
            type_=sa.String(length=255),
            existing_type=sa.String,
            nullable=False,
        )
        batch_op.alter_column(
            "user_email",
            type_=sa.String(length=255),
            nullable=False,
        )
        batch_op.alter_column(
            "user_id",
            type_=sa.String(length=36),
            existing_type=sa.String,
            nullable=False,
        )


def downgrade() -> None:
    with op.batch_alter_table("user_action", schema=None) as batch_op:
        batch_op.alter_column(
            "user_name",
            type_=sa.String,
            existing_type=sa.String(length=255),
            nullable=False,
        )
        batch_op.alter_column(
            "user_email",
            type_=sa.String,
            existing_type=sa.String(length=255),
            nullable=False,
        )
        batch_op.alter_column(
            "user_id",
            type_=sa.String,
            existing_type=sa.String(length=36),
            nullable=False,
        )

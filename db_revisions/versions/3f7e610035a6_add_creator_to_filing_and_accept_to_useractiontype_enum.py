"""add creator to filing

Revision ID: 3f7e610035a6
Revises: 102fb94a24cc
Create Date: 2024-04-22 13:03:16.328778

"""

from typing import Sequence, Union

from alembic import op, context
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "3f7e610035a6"
down_revision: Union[str, None] = "102fb94a24cc"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


old_user_action = postgresql.ENUM(
    "SUBMIT",
    "ACCEPT",
    "SIGNED",
    name="useractiontype",
    create_type=False,
)

new_user_action = postgresql.ENUM(
    "SUBMIT",
    "ACCEPT",
    "SIGNED",
    "CREATE",
    name="useractiontype",
    create_type=False,
)


def upgrade() -> None:
    with op.batch_alter_table("filing", schema=None) as batch_op:
        batch_op.add_column(sa.Column("creator_id", sa.Integer, nullable=False))
        batch_op.create_foreign_key("filing_creator_fkey", "user_action", ["creator_id"], ["id"])

    if "sqlite" not in context.get_context().dialect.name:
        op.execute("ALTER TYPE useractiontype RENAME TO useractiontype_old")
        new_user_action.create(op.get_bind(), checkfirst=True)
        op.execute(
            "ALTER TABLE user_action ALTER COLUMN action_type TYPE useractiontype USING user_action::text::useractiontype"
        )
        op.execute("DROP TYPE useractiontype_old")


def downgrade() -> None:
    op.drop_constraint(constraint_name="filing_creator_fkey", table_name="filing")
    op.drop_column("filing", "creator_id")

    if "sqlite" not in context.get_context().dialect.name:
        op.execute("ALTER TYPE useractiontype RENAME TO useractiontype_old")
        old_user_action.create(op.get_bind(), checkfirst=True)
        op.execute(
            "ALTER TABLE user_action ALTER COLUMN action_type TYPE useractiontype USING user_action::text::useractiontype"
        )
        op.execute("DROP TYPE useractiontype_old")

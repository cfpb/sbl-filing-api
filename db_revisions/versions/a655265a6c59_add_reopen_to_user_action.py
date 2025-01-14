"""Add REOPEN to user action

Revision ID: a655265a6c59
Revises: 7fe49d38726b
Create Date: 2025-01-08 13:59:33.098890

"""

from typing import Sequence, Union

from alembic import op, context
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "a655265a6c59"
down_revision: Union[str, None] = "7fe49d38726b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


old_user_action = postgresql.ENUM(
    "SUBMIT",
    "ACCEPT",
    "SIGN",
    "CREATE",
    name="useractiontype",
    create_type=False,
)

new_user_action = postgresql.ENUM(
    "SUBMIT",
    "ACCEPT",
    "SIGN",
    "CREATE",
    "REOPEN",
    name="useractiontype",
    create_type=False,
)


def upgrade() -> None:
    if "sqlite" not in context.get_context().dialect.name:
        op.execute("ALTER TYPE useractiontype RENAME TO useractiontype_old")
        new_user_action.create(op.get_bind(), checkfirst=True)
        op.execute(
            "ALTER TABLE user_action ALTER COLUMN action_type TYPE useractiontype USING user_action::text::useractiontype"
        )
        op.execute("DROP TYPE useractiontype_old")


def downgrade() -> None:
    if "sqlite" not in context.get_context().dialect.name:
        op.execute("ALTER TYPE useractiontype RENAME TO useractiontype_old")
        old_user_action.create(op.get_bind(), checkfirst=True)
        op.execute(
            "ALTER TABLE user_action ALTER COLUMN action_type TYPE useractiontype USING user_action::text::useractiontype"
        )
        op.execute("DROP TYPE useractiontype_old")

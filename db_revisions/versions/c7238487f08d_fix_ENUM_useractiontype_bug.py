"""fix ENUM useractiontype bug

Revision ID: c7238487f08d
Revises: 5492f53d1fa5
Create Date: 2024-05-07 11:04:38.575959

"""

from typing import Sequence, Union

from alembic import op, context
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "c7238487f08d"
down_revision: Union[str, None] = "5492f53d1fa5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


old_user_action = postgresql.ENUM(
    "SUBMIT",
    "ACCEPT",
    "SIGNED",
    "CREATE",
    name="useractiontype",
    create_type=False,
)

new_user_action = postgresql.ENUM(
    "SUBMIT",
    "ACCEPT",
    "SIGN",
    "CREATE",
    name="useractiontype",
    create_type=False,
)


def upgrade() -> None:
    if "sqlite" not in context.get_context().dialect.name:
        op.execute("ALTER TYPE useractiontype RENAME TO useractiontype_old")
        new_user_action.create(op.get_bind(), checkfirst=True)
        op.execute(
            "ALTER TABLE user_action ALTER COLUMN action_type TYPE useractiontype USING action_type::text::useractiontype"
        )
        op.execute("DROP TYPE useractiontype_old")


def downgrade() -> None:
    if "sqlite" not in context.get_context().dialect.name:
        op.execute("ALTER TYPE useractiontype RENAME TO useractiontype_old")
        old_user_action.create(op.get_bind(), checkfirst=True)
        op.execute(
            "ALTER TABLE user_action ALTER COLUMN action_type TYPE useractiontype USING action_type::text::useractiontype"
        )
        op.execute("DROP TYPE useractiontype_old")

"""Renaming validation json to results

Revision ID: 5492f53d1fa5
Revises: e1b0d044c840
Create Date: 2024-05-01 13:40:54.288361

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "5492f53d1fa5"
down_revision: Union[str, None] = "e1b0d044c840"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("submission") as batch_op:
        batch_op.alter_column("validation_json", new_column_name="validation_results")


def downgrade() -> None:
    with op.batch_alter_table("submission") as batch_op:
        batch_op.alter_column("validation_results", new_column_name="validation_json")

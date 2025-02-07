"""user_action add filing submission fks

Revision ID: ef815604e2a9
Revises: 6ec12afa5b37
Create Date: 2025-01-24 10:15:32.975738

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

from sbl_filing_api.entities.models.model_enums import UserActionType

# revision identifiers, used by Alembic.
revision: str = "ef815604e2a9"
down_revision: Union[str, None] = "6ec12afa5b37"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add links to Filing and Submission to user_action
    with op.batch_alter_table("user_action", schema=None) as batch_op:
        batch_op.add_column(sa.Column("filing_id", sa.Integer, nullable=True))
        batch_op.create_foreign_key("user_action_filing_fkey", "filing", ["filing_id"], ["id"])
        batch_op.add_column(sa.Column("submission_id", sa.Integer, nullable=True))
        batch_op.create_foreign_key("user_action_submission_fkey", "submission", ["submission_id"], ["id"])
    # Update links with existing info
    op.execute(
        """
        UPDATE user_action 
        SET filing_id = COALESCE(
            (SELECT id FROM filing WHERE creator_id = user_action.id), 
            (SELECT filing FROM filing_signature WHERE user_action = user_action.id),
            (SELECT filing FROM submission WHERE submitter_id = user_action.id OR accepter_id = user_action.id)
        )
    """
    )
    op.execute(
        """
        UPDATE user_action 
        SET submission_id = (SELECT id FROM submission WHERE submitter_id = user_action.id OR accepter_id = user_action.id) 
    """
    )
    # Index the foreign keys
    op.create_index("user_action_filing_id", table_name="user_action", columns=["filing_id"])
    op.create_index("user_action_submission_id", table_name="user_action", columns=["submission_id"])
    with op.batch_alter_table("user_action", schema=None) as batch_op:
        batch_op.alter_column("filing_id", nullable=False)
        batch_op.alter_column("submission_id", nullable=True)
    # Drop old table and columns no longer needed
    op.drop_table("filing_signature")
    with op.batch_alter_table("filing", schema=None) as batch_op:
        batch_op.drop_column("creator_id")
    with op.batch_alter_table("submission", schema=None) as batch_op:
        batch_op.drop_column("submitter_id")
        batch_op.drop_column("accepter_id")


def downgrade() -> None:
    # recreate the filing_signature table
    op.create_table(
        "filing_signature",
        sa.Column("user_action", sa.INTEGER, primary_key=True, unique=True, nullable=False),
        sa.Column("filing", sa.Integer, nullable=False),
        sa.PrimaryKeyConstraint("user_action", name="filing_signatures_pkey"),
        sa.ForeignKeyConstraint(["user_action"], ["user_action.id"], name="filing_signatures_user_action_fkey"),
        sa.ForeignKeyConstraint(["filing"], ["filing.id"], name="filing_signatures_filing_fkey"),
    )
    # re-add link columns
    with op.batch_alter_table("filing", schema=None) as batch_op:
        batch_op.add_column(sa.Column("creator_id", sa.Integer))
        batch_op.create_foreign_key("filing_creator_fkey", "user_action", ["creator_id"], ["id"])

    with op.batch_alter_table("submission", schema=None) as batch_op:
        batch_op.add_column(sa.Column("submitter_id", sa.Integer))
        batch_op.add_column(sa.Column("accepter_id", sa.Integer))
        batch_op.create_foreign_key("submission_submitter_fkey", "user_action", ["submitter_id"], ["id"])
        batch_op.create_foreign_key("submission_accepter_fkey", "user_action", ["accepter_id"], ["id"])

    # re-populate data
    op.execute(
        f"""
        INSERT INTO filing_signature (user_action, filing)
        SELECT id, filing_id FROM user_action WHERE action_type = '{UserActionType.SIGN}' 
    """
    )
    op.execute(
        f"""
        UPDATE submission
        SET submitter_id = (SELECT id FROM user_action WHERE submission.id = user_action.submission_id AND action_type = '{UserActionType.SUBMIT}'),
        accepter_id = (SELECT id FROM user_action WHERE submission.id = user_action.submission_id AND action_type = '{UserActionType.ACCEPT}')
    """
    )
    op.execute(
        f"""
        UPDATE filing
        SET creator_id = (SELECT id FROM user_action WHERE filing.id = user_action.filing_id AND action_type = '{UserActionType.CREATE}')
    """
    )

    # Make columns non-nullable
    with op.batch_alter_table("filing", schema=None) as batch_op:
        batch_op.alter_column("creator_id", nullable=False)
    with op.batch_alter_table("submission", schema=None) as batch_op:
        batch_op.alter_column("submitter_id", nullable=False)

    # Drop new columns
    op.drop_index("user_action_filing_id", table_name="user_action")
    op.drop_index("user_action_submission_id", table_name="user_action")
    op.drop_constraint(constraint_name="user_action_filing_fkey", table_name="user_action")
    op.drop_column("user_action", "filing_id")
    op.drop_constraint(constraint_name="user_action_submission_fkey", table_name="user_action")
    op.drop_column("user_action", "submission_id")

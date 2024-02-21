from pytest_alembic.tests import (
    test_single_head_revision,  # noqa: F401
    test_up_down_consistency,  # noqa: F401
    test_upgrade,  # noqa: F401
)

import sqlalchemy
from sqlalchemy.engine import Engine

from pytest_alembic import MigrationContext


def test_migrations_up_to_078cbbc69fe5(alembic_runner: MigrationContext, alembic_engine: Engine):
    alembic_runner.migrate_up_to("078cbbc69fe5")

    inspector = sqlalchemy.inspect(alembic_engine)
    tables = inspector.get_table_names()

    assert "filing_task" in tables
    assert {"name", "task_order"} == set([c["name"] for c in inspector.get_columns("filing_task")])

    assert "filing_task_state" in tables
    assert {"id", "filing", "task_name", "state", "user", "change_timestamp"} == set(
        [c["name"] for c in inspector.get_columns("filing_task_state")]
    )

    filing_task_state_pk = inspector.get_pk_constraint("filing_task_state")
    assert filing_task_state_pk["name"] == "filing_task_state_pkey"
    assert filing_task_state_pk["constrained_columns"] == ["id"]

    filing_task_state_fk = inspector.get_foreign_keys("filing_task_state")[0]
    assert filing_task_state_fk["name"] == "filing_task_state_filing_fkey"
    assert (
        ["filing"] == filing_task_state_fk["constrained_columns"]
        and "filing" == filing_task_state_fk["referred_table"]
        and ["id"] == filing_task_state_fk["referred_columns"]
    )

    filing_state_fk2 = inspector.get_foreign_keys("filing_task_state")[1]
    assert (
        "task_name" in filing_state_fk2["constrained_columns"]
        and "filing_task" == filing_state_fk2["referred_table"]
        and "name" in filing_state_fk2["referred_columns"]
    )

    assert "state" not in set([c["name"] for c in inspector.get_columns("filing")])


def test_migrations(alembic_runner: MigrationContext, alembic_engine: Engine):
    alembic_runner.migrate_up_to("f30c5c3c7a42")

    inspector = sqlalchemy.inspect(alembic_engine)
    tables = inspector.get_table_names()

    assert "filing_period" in tables
    assert {"code", "description", "start_period", "end_period", "due", "filing_type"} == set(
        [c["name"] for c in inspector.get_columns("filing_period")]
    )

    assert "filing" in tables
    assert {"id", "filing_period", "lei", "state", "institution_snapshot_id", "contact_info"} == set(
        [c["name"] for c in inspector.get_columns("filing")]
    )

    assert "submission" in tables
    assert {
        "id",
        "filing",
        "submitter",
        "state",
        "validation_ruleset_version",
        "validation_json",
        "confirmation_id",
    } == set([c["name"] for c in inspector.get_columns("submission")])

    filing_period_pk = inspector.get_pk_constraint("filing_period")
    assert filing_period_pk["name"] == "filing_period_pkey"
    assert filing_period_pk["constrained_columns"] == ["code"]

    filing_pk = inspector.get_pk_constraint("filing")
    assert filing_pk["name"] == "filing_pkey"
    assert filing_pk["constrained_columns"] == ["id"]

    filing_fk = inspector.get_foreign_keys("filing")[0]
    assert filing_fk["name"] == "filing_filing_period_fkey"
    assert (
        "filing_period" in filing_fk["constrained_columns"]
        and "filing_period" == filing_fk["referred_table"]
        and "code" in filing_fk["referred_columns"]
    )

    submission_fk = inspector.get_foreign_keys("submission")[0]
    assert submission_fk["name"] == "submission_filing_fkey"
    assert (
        ["filing"] == submission_fk["constrained_columns"]
        and "filing" == submission_fk["referred_table"]
        and ["id"] == submission_fk["referred_columns"]
    )


def test_migration_to_19fccbf914bc(alembic_runner: MigrationContext, alembic_engine: Engine):
    alembic_runner.migrate_up_to("19fccbf914bc")

    inspector = sqlalchemy.inspect(alembic_engine)

    assert "submission_time" in set([c["name"] for c in inspector.get_columns("submission")])

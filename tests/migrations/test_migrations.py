from pytest_alembic.tests import (
    test_single_head_revision,  # noqa: F401
    test_up_down_consistency,  # noqa: F401
    test_upgrade,  # noqa: F401
)

import sqlalchemy
from sqlalchemy.engine import Engine

from pytest_alembic import MigrationContext


def test_migrations(alembic_runner: MigrationContext, alembic_engine: Engine):
    alembic_runner.migrate_up_to("f30c5c3c7a42")

    inspector = sqlalchemy.inspect(alembic_engine)
    tables = inspector.get_table_names()

    assert "filing_period" in tables
    assert {"id", "name", "start_period", "end_period", "due", "filing_type"} == set(
        [c["name"] for c in inspector.get_columns("filing_period")]
    )

    assert "filing" in tables
    assert {"id", "lei", "state", "institution_snapshot_id", "filing_period", "contact_info"} == set(
        [c["name"] for c in inspector.get_columns("filing")]
    )

    assert "submission" in tables
    assert {
        "id",
        "submitter",
        "state",
        "validation_ruleset_version",
        "validation_json",
        "filing",
        "confirmation_id",
    } == set([c["name"] for c in inspector.get_columns("submission")])

    filing_fk = inspector.get_foreign_keys("filing")[0]
    assert (
        "filing_period" in filing_fk["constrained_columns"]
        and "filing_period" == filing_fk["referred_table"]
        and "id" in filing_fk["referred_columns"]
    )

    submission_fk = inspector.get_foreign_keys("submission")[0]
    assert (
        "filing" in submission_fk["constrained_columns"]
        and "filing" == submission_fk["referred_table"]
        and "id" in submission_fk["referred_columns"]
    )


def test_migration_to_19fccbf914bc(alembic_runner: MigrationContext, alembic_engine: Engine):
    alembic_runner.migrate_up_to("19fccbf914bc")

    inspector = sqlalchemy.inspect(alembic_engine)

    assert "submission_time" in set([c["name"] for c in inspector.get_columns("submission")])

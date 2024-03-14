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

    filing_idx = inspector.get_indexes("filing")[0]
    assert filing_idx["name"] == "idx_lei_filing_period"
    assert ["lei", "filing_period"] == filing_idx["column_names"]
    assert filing_idx["unique"] == 1

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


def test_migration_to_bbc51b08d22f(alembic_runner: MigrationContext, alembic_engine: Engine):
    alembic_runner.migrate_up_to("bbc51b08d22f")

    inspector = sqlalchemy.inspect(alembic_engine)
    tables = inspector.get_table_names()
    assert "filing_task_progress" in tables
    assert "filing_task_state" not in tables
    assert {"id", "filing", "task_name", "state", "user", "change_timestamp"} == set(
        [c["name"] for c in inspector.get_columns("filing_task_progress")]
    )

    filing_task_progress_pk = inspector.get_pk_constraint("filing_task_progress")
    assert filing_task_progress_pk["name"] == "filing_task_progress_pkey"
    assert filing_task_progress_pk["constrained_columns"] == ["id"]

    filing_task_state_fk = inspector.get_foreign_keys("filing_task_progress")[0]
    assert filing_task_state_fk["name"] == "filing_task_progress_filing_fkey"
    assert (
        ["filing"] == filing_task_state_fk["constrained_columns"]
        and "filing" == filing_task_state_fk["referred_table"]
        and ["id"] == filing_task_state_fk["referred_columns"]
    )


def test_migrations_to_8e8faceb46bd(alembic_runner: MigrationContext, alembic_engine: Engine):
    alembic_runner.migrate_up_to("8e8faceb46bd")

    inspector = sqlalchemy.inspect(alembic_engine)

    assert "filename" in set([c["name"] for c in inspector.get_columns("submission")])


def test_migration_to_8eaef8ce4c23(alembic_runner: MigrationContext, alembic_engine: Engine):
    alembic_runner.migrate_up_to("8eaef8ce4c23")

    inspector = sqlalchemy.inspect(alembic_engine)

    tables = inspector.get_table_names()

    assert "contact_info" in tables
    assert {
        "id",
        "first_name",
        "last_name",
        "hq_address_street_1",
        "hq_address_street_2",
        "hq_address_city",
        "hq_address_state",
        "hq_address_zip",
        "phone",
        "email",
        "filing",
    } == set([c["name"] for c in inspector.get_columns("contact_info")])

    contact_info_fk = inspector.get_foreign_keys("contact_info")[0]
    assert contact_info_fk["name"] == "contact_info_filing_fkey"
    assert (
        "filing" in contact_info_fk["constrained_columns"]
        and "filing" == contact_info_fk["referred_table"]
        and "id" in contact_info_fk["referred_columns"]
    )

    assert "contact_info" not in [c["name"] for c in inspector.get_columns("contact_info")]


def test_migration_to_b3bfb504ae7e(alembic_runner: MigrationContext, alembic_engine: Engine):
    alembic_runner.migrate_up_to("b3bfb504ae7e")

    inspector = sqlalchemy.inspect(alembic_engine)

    assert "confirmation_id" not in [c["name"] for c in inspector.get_columns("submission")]

    assert "confirmation_id" in [c["name"] for c in inspector.get_columns("filing")]


def test_migration_to_b70d06f93029(alembic_runner: MigrationContext, alembic_engine: Engine):
    alembic_runner.migrate_up_to("b70d06f93029")

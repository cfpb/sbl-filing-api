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


def test_migrations_to_fb46d55283d6(alembic_runner: MigrationContext, alembic_engine: Engine):
    alembic_runner.migrate_up_to("fb46d55283d6")
    inspector = sqlalchemy.inspect(alembic_engine)

    tables = inspector.get_table_names()

    assert "signature" in tables
    assert {
        "id",
        "filing",
        "signer_id",
        "signer_name",
        "signer_email",
        "signed_date",
    } == set([c["name"] for c in inspector.get_columns("signature")])

    sig_filing_fk = inspector.get_foreign_keys("signature")[0]
    assert sig_filing_fk["name"] == "signature_filing_fkey"
    assert (
        "filing" in sig_filing_fk["constrained_columns"]
        and "filing" == sig_filing_fk["referred_table"]
        and "id" in sig_filing_fk["referred_columns"]
    )


def test_migrations_to_7a1b7eab0167(alembic_runner: MigrationContext, alembic_engine: Engine):
    alembic_runner.migrate_up_to("7a1b7eab0167")
    inspector = sqlalchemy.inspect(alembic_engine)

    assert "accepter" in [c["name"] for c in inspector.get_columns("submission")]


def test_migration_to_b3bfb504ae7e(alembic_runner: MigrationContext, alembic_engine: Engine):
    alembic_runner.migrate_up_to("b3bfb504ae7e")

    inspector = sqlalchemy.inspect(alembic_engine)

    assert "confirmation_id" not in [c["name"] for c in inspector.get_columns("submission")]

    assert "confirmation_id" in [c["name"] for c in inspector.get_columns("filing")]


def test_migration_to_b70d06f93029(alembic_runner: MigrationContext, alembic_engine: Engine):
    alembic_runner.migrate_up_to("b70d06f93029")


def test_migration_to_d0ab7f051052(alembic_runner: MigrationContext, alembic_engine: Engine):
    alembic_runner.migrate_up_to("d0ab7f051052")

    inspector = sqlalchemy.inspect(alembic_engine)

    assert "accepter" not in [c["name"] for c in inspector.get_columns("submission")]
    assert "submitter" not in [c["name"] for c in inspector.get_columns("submission")]


def test_migration_to_4a5e42bb5efa(alembic_runner: MigrationContext, alembic_engine: Engine):
    alembic_runner.migrate_up_to("4a5e42bb5efa")

    inspector = sqlalchemy.inspect(alembic_engine)

    tables = inspector.get_table_names()

    assert "accepter" in tables

    assert {
        "id",
        "submission",
        "accepter",
        "accepter_name",
        "accepter_email",
        "acception_time",
    } == set([c["name"] for c in inspector.get_columns("accepter")])

    accepter_fk = inspector.get_foreign_keys("accepter")[0]
    assert accepter_fk["name"] == "accepter_submission_fkey"
    assert (
        "submission" in accepter_fk["constrained_columns"]
        and "submission" == accepter_fk["referred_table"]
        and "id" in accepter_fk["referred_columns"]
    )


def test_migration_to_ffd779216f6d(alembic_runner: MigrationContext, alembic_engine: Engine):
    alembic_runner.migrate_up_to("ffd779216f6d")

    inspector = sqlalchemy.inspect(alembic_engine)

    tables = inspector.get_table_names()

    assert "submitter" in tables

    assert {
        "id",
        "submission",
        "submitter",
        "submitter_name",
        "submitter_email",
    } == set([c["name"] for c in inspector.get_columns("submitter")])

    submitter_fk = inspector.get_foreign_keys("submitter")[0]
    assert submitter_fk["name"] == "submitter_submission_fkey"
    assert (
        "submission" in submitter_fk["constrained_columns"]
        and "submission" == submitter_fk["referred_table"]
        and "id" in submitter_fk["referred_columns"]
    )


def test_migration_to_2e81179924b5(alembic_runner: MigrationContext, alembic_engine: Engine):
    alembic_runner.migrate_up_to("2e81179924b5")

    inspector = sqlalchemy.inspect(alembic_engine)

    assert "hq_address_street_3" in [c["name"] for c in inspector.get_columns("contact_info")]
    assert "hq_address_street_4" in [c["name"] for c in inspector.get_columns("contact_info")]


def test_migration_to_102fb94a24cc(alembic_runner: MigrationContext, alembic_engine: Engine):
    alembic_runner.migrate_up_to("102fb94a24cc")

    inspector = sqlalchemy.inspect(alembic_engine)

    tables = inspector.get_table_names()

    assert "user_action" in tables
    assert "signature" not in tables
    assert "accepter" not in tables
    assert "submitter" not in tables

    assert set(["id", "user_id", "user_name", "user_email", "action_type", "timestamp"]) == set(
        [c["name"] for c in inspector.get_columns("user_action")]
    )

    assert set(
        [
            "user_action",
            "filing",
        ]
    ) == set([c["name"] for c in inspector.get_columns("filing_signature")])

    filing_sig_fks = inspector.get_foreign_keys("filing_signature")
    assert filing_sig_fks[0]["name"] == "filing_signatures_user_action_fkey"
    assert filing_sig_fks[1]["name"] == "filing_signatures_filing_fkey"

    assert (
        "user_action" in filing_sig_fks[0]["constrained_columns"]
        and "user_action" == filing_sig_fks[0]["referred_table"]
        and "id" in filing_sig_fks[0]["referred_columns"]
    )
    assert (
        "filing" in filing_sig_fks[1]["constrained_columns"]
        and "filing" == filing_sig_fks[1]["referred_table"]
        and "id" in filing_sig_fks[1]["referred_columns"]
    )

    assert "submitter_id" in [c["name"] for c in inspector.get_columns("submission")]
    assert "accepter_id" in [c["name"] for c in inspector.get_columns("submission")]

    submission_fks = inspector.get_foreign_keys("submission")
    assert submission_fks[1]["name"] == "submission_submitter_fkey"
    assert submission_fks[2]["name"] == "submission_accepter_fkey"

    assert (
        "submitter_id" in submission_fks[1]["constrained_columns"]
        and "user_action" == submission_fks[1]["referred_table"]
        and "id" in submission_fks[1]["referred_columns"]
    )
    assert (
        "accepter_id" in submission_fks[2]["constrained_columns"]
        and "user_action" == submission_fks[2]["referred_table"]
        and "id" in submission_fks[2]["referred_columns"]
    )


def test_migration_to_3f7e610035a6(alembic_runner: MigrationContext, alembic_engine: Engine):
    alembic_runner.migrate_up_to("3f7e610035a6")

    inspector = sqlalchemy.inspect(alembic_engine)

    assert "creator_id" in [c["name"] for c in inspector.get_columns("filing")]

    filing_fks = inspector.get_foreign_keys("filing")
    assert (
        "creator_id" in filing_fks[1]["constrained_columns"]
        and "user_action" == filing_fks[1]["referred_table"]
        and "id" in filing_fks[1]["referred_columns"]
    )


def test_migration_to_e1b0d044c840(alembic_runner: MigrationContext, alembic_engine: Engine):
    alembic_runner.migrate_up_to("e1b0d044c840")

    inspector = sqlalchemy.inspect(alembic_engine)

    assert "phone_number" in [c["name"] for c in inspector.get_columns("contact_info")]
    assert "phone" not in [c["name"] for c in inspector.get_columns("contact_info")]


def test_migration_to_5492f53d1fa5(alembic_runner: MigrationContext, alembic_engine: Engine):
    alembic_runner.migrate_up_to("5492f53d1fa5")

    inspector = sqlalchemy.inspect(alembic_engine)

    assert "validation_results" in [c["name"] for c in inspector.get_columns("submission")]
    assert "validation_json" not in [c["name"] for c in inspector.get_columns("submission")]


def test_migrations_to_7356a7d7036d(alembic_runner: MigrationContext, alembic_engine: Engine):
    alembic_runner.migrate_up_to("7356a7d7036d")

    inspector = sqlalchemy.inspect(alembic_engine)

    assert "total_records" in set([c["name"] for c in inspector.get_columns("submission")])


def test_migrations_to_ba8234fe9eb5(alembic_runner: MigrationContext, alembic_engine: Engine):
    alembic_runner.migrate_up_to("ba8234fe9eb5")

    inspector = sqlalchemy.inspect(alembic_engine)

    assert "phone_ext" in set([c["name"] for c in inspector.get_columns("contact_info")])


def test_migrations_to_6babc6109a5a(alembic_runner: MigrationContext, alembic_engine: Engine):
    alembic_runner.migrate_up_to("6babc6109a5a")

    inspector = sqlalchemy.inspect(alembic_engine)

    col_set = set(
        [
            (c["name"], c["type"].length if isinstance(c["type"].python_type(), str) else None)
            for c in inspector.get_columns("contact_info")
        ]
    )

    assert ("first_name", 255) in col_set
    assert ("last_name", 255) in col_set
    assert ("hq_address_street_1", 255) in col_set
    assert ("hq_address_street_2", 255) in col_set
    assert ("hq_address_street_3", 255) in col_set
    assert ("hq_address_street_4", 255) in col_set
    assert ("hq_address_city", 255) in col_set
    assert ("hq_address_state", 255) in col_set
    assert ("email", 255) in col_set
    assert ("phone_number", 255) in col_set
    assert ("phone_ext", 255) in col_set


def test_migrations_to_f4091e4ce218(alembic_runner: MigrationContext, alembic_engine: Engine):
    alembic_runner.migrate_up_to("f4091e4ce218")

    inspector = sqlalchemy.inspect(alembic_engine)

    columns = inspector.get_columns("user_action")

    assert [c for c in columns if c["name"] == "user_id"][0]["type"].length == 36
    assert [c for c in columns if c["name"] == "user_name"][0]["type"].length == 255
    assert [c for c in columns if c["name"] == "user_email"][0]["type"].length == 255


def test_migrations_to_26f11ac15b3c(alembic_runner: MigrationContext, alembic_engine: Engine):
    alembic_runner.migrate_up_to("26f11ac15b3c")

    inspector = sqlalchemy.inspect(alembic_engine)

    assert "is_voluntary" in set([c["name"] for c in inspector.get_columns("filing")])


def test_migrations_to_6ec12afa5b37(alembic_runner: MigrationContext, alembic_engine: Engine):
    alembic_runner.migrate_up_to("6ec12afa5b37")

    inspector = sqlalchemy.inspect(alembic_engine)

    counter_constraint = inspector.get_unique_constraints("submission")[0]

    assert "counter" in set([c["name"] for c in inspector.get_columns("submission")])
    assert counter_constraint["name"] == "unique_filing_counter"
    assert set(counter_constraint["column_names"]) == set(["filing", "counter"])


def test_migrations_to_63138f5cf036(alembic_runner: MigrationContext, alembic_engine: Engine):
    alembic_runner.migrate_up_to("63138f5cf036")

    inspector = sqlalchemy.inspect(alembic_engine)
    columns = inspector.get_columns("filing")
    assert next(c for c in columns if c["name"] == "is_voluntary")["nullable"]

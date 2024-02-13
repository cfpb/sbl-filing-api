import pandas as pd
import pytest

import datetime
from datetime import datetime as dt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_scoped_session

from entities.models import (
    SubmissionDAO,
    SubmissionDTO,
    FilingPeriodDAO,
    FilingPeriodDTO,
    FilingDAO,
    FilingDTO,
    FilingTaskStateDAO,
    FilingTaskDAO,
    FilingType,
    FilingTaskState,
    SubmissionState,
)
from entities.repos import submission_repo as repo
from pytest_mock import MockerFixture

from entities.engine import engine as entities_engine

from regtech_api_commons.models.auth import AuthenticatedUser


class TestSubmissionRepo:
    @pytest.fixture(scope="function", autouse=True)
    async def setup(
        self, transaction_session: AsyncSession, mocker: MockerFixture, session_generator: async_scoped_session
    ):
        mocker.patch.object(entities_engine, "SessionLocal", return_value=session_generator)

        filing_task_1 = FilingTaskDAO(name="Task-1", task_order=1)
        filing_task_2 = FilingTaskDAO(name="Task-2", task_order=2)
        transaction_session.add(filing_task_1)
        transaction_session.add(filing_task_2)

        filing_period = FilingPeriodDAO(
            name="FilingPeriod2024",
            start_period=dt.now(),
            end_period=dt.now(),
            due=dt.now(),
            filing_type=FilingType.ANNUAL,
        )
        transaction_session.add(filing_period)

        filing1 = FilingDAO(
            lei="1234567890",
            institution_snapshot_id="Snapshot-1",
            filing_period=1,
        )
        filing2 = FilingDAO(
            lei="ABCDEFGHIJ",
            institution_snapshot_id="Snapshot-1",
            filing_period=1,
        )
        transaction_session.add(filing1)
        transaction_session.add(filing2)

        submission1 = SubmissionDAO(
            submitter="test1@cfpb.gov",
            filing=1,
            state=SubmissionState.SUBMISSION_UPLOADED,
            validation_ruleset_version="v1",
            submission_time=dt.now(),
        )
        submission2 = SubmissionDAO(
            submitter="test2@cfpb.gov",
            filing=2,
            state=SubmissionState.SUBMISSION_UPLOADED,
            validation_ruleset_version="v1",
            submission_time=(dt.now() - datetime.timedelta(seconds=1000)),
        )
        submission3 = SubmissionDAO(
            submitter="test2@cfpb.gov",
            filing=2,
            state=SubmissionState.SUBMISSION_UPLOADED,
            validation_ruleset_version="v1",
            submission_time=dt.now(),
        )
        print(f"{submission2}")
        print(f"{submission3}")
        transaction_session.add(submission1)
        transaction_session.add(submission2)
        transaction_session.add(submission3)

        await transaction_session.commit()

    async def test_add_filing_period(self, transaction_session: AsyncSession):
        new_fp = FilingPeriodDTO(
            name="FilingPeriod2024.1",
            start_period=dt.now(),
            end_period=dt.now(),
            due=dt.now(),
            filing_type=FilingType.ANNUAL,
        )
        res = await repo.upsert_filing_period(transaction_session, new_fp)
        assert res.id == 2
        assert res.filing_type == FilingType.ANNUAL

    async def test_get_filing_periods(self, query_session: AsyncSession):
        res = await repo.get_filing_periods(query_session)
        assert len(res) == 1
        assert res[0].name == "FilingPeriod2024"

    async def test_get_filing_period(self, query_session: AsyncSession):
        res = await repo.get_filing_period(query_session, filing_period_id=1)
        assert res.id == 1
        assert res.name == "FilingPeriod2024"
        assert res.filing_type == FilingType.ANNUAL

    async def test_add_and_modify_filing(self, transaction_session: AsyncSession):
        new_filing = FilingDTO(lei="12345ABCDE", institution_snapshot_id="Snapshot-1", filing_period=1, tasks=[])
        res = await repo.upsert_filing(transaction_session, new_filing)
        assert res.id == 3
        assert res.lei == "12345ABCDE"
        assert res.institution_snapshot_id == "Snapshot-1"

        mod_filing = FilingDTO(id=3, lei="12345ABCDE", institution_snapshot_id="Snapshot-2", filing_period=1, tasks=[])
        res = await repo.upsert_filing(transaction_session, mod_filing)
        assert res.id == 3
        assert res.lei == "12345ABCDE"
        assert res.institution_snapshot_id == "Snapshot-2"

    async def test_get_filing_tasks(self, transaction_session: AsyncSession):
        tasks = await repo.get_filing_tasks(transaction_session)
        assert len(tasks) == 2
        assert tasks[0].name == "Task-1"
        assert tasks[1].name == "Task-2"

    async def test_add_task_to_filing(self, query_session: AsyncSession, transaction_session: AsyncSession):
        filing = await repo.get_filing(query_session, filing_id=1)
        task = await query_session.scalar(select(FilingTaskDAO).where(FilingTaskDAO.name == "Task-1"))
        filing_task = FilingTaskStateDAO(
            filing=filing.id, task=task, user="test@cfpb.gov", state=FilingTaskState.IN_PROGRESS
        )
        filing.tasks = [filing_task]
        seconds_now = dt.utcnow().timestamp()
        await repo.upsert_filing(transaction_session, filing)

        filing_task_states = (await transaction_session.scalars(select(FilingTaskStateDAO))).all()

        assert len(filing_task_states) == 1
        assert filing_task_states[0].task.name == "Task-1"
        assert filing_task_states[0].filing == 1
        assert filing_task_states[0].state == FilingTaskState.IN_PROGRESS
        assert filing_task_states[0].user == "test@cfpb.gov"
        assert filing_task_states[0].change_timestamp.timestamp() == pytest.approx(
            seconds_now, abs=1.0
        )  # allow for possible 1 second difference

    async def test_get_filing(self, query_session: AsyncSession):
        res = await repo.get_filing(query_session, filing_id=1)
        assert res.id == 1
        assert res.lei == "1234567890"
        assert len(res.tasks) == 2
        assert FilingTaskState.NOT_STARTED in set([t.state for t in res.tasks])

        res = await repo.get_filing(query_session, filing_id=2)
        assert res.id == 2
        assert res.lei == "ABCDEFGHIJ"
        assert len(res.tasks) == 2
        assert FilingTaskState.NOT_STARTED in set([t.state for t in res.tasks])

    async def test_get_period_filings_for_user(self, query_session: AsyncSession, mocker: MockerFixture):
        user = AuthenticatedUser.from_claim({"institutions": ["ZYXWVUTSRQP"]})
        results = await repo.get_period_filings_for_user(query_session, user, period_name="FilingPeriod2024")
        assert len(results) == 0

        user = AuthenticatedUser.from_claim({"institutions": ["1234567890", "0987654321"]})
        results = await repo.get_period_filings_for_user(query_session, user, period_name="FilingPeriod2024")
        assert len(results) == 1
        assert results[0].id == 1
        assert results[0].lei == "1234567890"
        assert len(results[0].tasks) == 2

        try:
            await repo.get_period_filings_for_user(query_session, user, period_name="FilingPeriod2025")
        except repo.NoFilingPeriodException as nfpe:
            assert str(nfpe) == "There is no Filing Period with name FilingPeriod2025 defined in the database."

    async def test_get_latest_submission(self, query_session: AsyncSession):
        res = await repo.get_latest_submission(query_session, filing_id=2)
        assert res.id == 3
        assert res.submitter == "test2@cfpb.gov"
        assert res.filing == 2
        assert res.state == SubmissionState.SUBMISSION_UPLOADED
        assert res.validation_ruleset_version == "v1"

    async def test_get_submission(self, query_session: AsyncSession):
        res = await repo.get_submission(query_session, submission_id=1)
        assert res.id == 1
        assert res.submitter == "test1@cfpb.gov"
        assert res.filing == 1
        assert res.state == SubmissionState.SUBMISSION_UPLOADED
        assert res.validation_ruleset_version == "v1"

    async def test_get_submissions(self, query_session: AsyncSession):
        res = await repo.get_submissions(query_session)
        assert len(res) == 3
        assert {1, 2, 3} == set([s.id for s in res])
        assert res[0].submitter == "test1@cfpb.gov"
        assert res[1].filing == 2
        assert res[2].state == SubmissionState.SUBMISSION_UPLOADED

        res = await repo.get_submissions(query_session, filing_id=2)
        assert len(res) == 2
        assert {2, 3} == set([s.id for s in res])
        assert {"test2@cfpb.gov"} == set([s.submitter for s in res])
        assert {2} == set([s.filing for s in res])
        assert {SubmissionState.SUBMISSION_UPLOADED} == set([s.state for s in res])

        # verify a filing with no submissions behaves ok
        res = await repo.get_submissions(query_session, filing_id=3)
        assert len(res) == 0

    async def test_add_submission(self, transaction_session: AsyncSession):
        res = await repo.add_submission(transaction_session, SubmissionDTO(submitter="test@cfpb.gov", filing=1))
        assert res.id == 4
        assert res.submitter == "test@cfpb.gov"
        assert res.filing == 1
        assert res.state == SubmissionState.SUBMISSION_UPLOADED

    async def test_update_submission(self, session_generator: async_scoped_session):
        async with session_generator() as add_session:
            res = await repo.add_submission(add_session, SubmissionDTO(submitter="test2@cfpb.gov", filing=2))

        res.state = SubmissionState.VALIDATION_IN_PROGRESS
        res = await repo.update_submission(res)

        async def query_updated_dao():
            async with session_generator() as search_session:
                stmt = select(SubmissionDAO).filter(SubmissionDAO.id == 4)
                new_res1 = await search_session.scalar(stmt)
                assert new_res1.id == 4
                assert new_res1.filing == 2
                assert new_res1.state == SubmissionState.VALIDATION_IN_PROGRESS

        await query_updated_dao()

        validation_json = self.get_error_json()
        res.validation_json = validation_json
        res.state = SubmissionState.VALIDATION_WITH_ERRORS
        # to test passing in a session to the update_submission function
        async with session_generator() as update_session:
            res = await repo.update_submission(res, update_session)

        async def query_updated_dao():
            async with session_generator() as search_session:
                stmt = select(SubmissionDAO).filter(SubmissionDAO.id == 4)
                new_res2 = await search_session.scalar(stmt)
                assert new_res2.id == 4
                assert new_res2.filing == 2
                assert new_res2.state == SubmissionState.VALIDATION_WITH_ERRORS
                assert new_res2.validation_json == validation_json

        await query_updated_dao()

    def get_error_json(self):
        df_columns = [
            "record_no",
            "field_name",
            "field_value",
            "validation_severity",
            "validation_id",
            "validation_name",
            "validation_desc",
        ]
        df_data = [
            [
                0,
                "uid",
                "BADUID0",
                "error",
                "E0001",
                "id.invalid_text_length",
                "'Unique identifier' must be at least 21 characters in length.",
            ],
            [
                0,
                "uid",
                "BADTEXTLENGTH",
                "error",
                "E0100",
                "ct_credit_product_ff.invalid_text_length",
                "'Free-form text field for other credit products' must not exceed 300 characters in length.",
            ],
            [
                1,
                "uid",
                "BADUID1",
                "error",
                "E0001",
                "id.invalid_text_length",
                "'Unique identifier' must be at least 21 characters in length.",
            ],
        ]
        error_df = pd.DataFrame(df_data, columns=df_columns)
        return error_df.to_json()

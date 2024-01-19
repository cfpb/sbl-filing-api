import pandas as pd
import pytest

from datetime import datetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from entities.models import (
    SubmissionDAO,
    SubmissionDTO,
    FilingPeriodDAO,
    FilingPeriodDTO,
    FilingDAO,
    FilingDTO,
    FilingType,
    FilingState,
    SubmissionState,
)
from entities.repos import submission_repo as repo


class TestSubmissionRepo:
    @pytest.fixture(scope="function", autouse=True)
    async def setup(
        self,
        transaction_session: AsyncSession,
    ):
        filing_period = FilingPeriodDAO(
            name="FilingPeriod2024",
            start_period=datetime.now(),
            end_period=datetime.now(),
            due=datetime.now(),
            filing_type=FilingType.MANUAL,
        )
        transaction_session.add(filing_period)

        filing1 = FilingDAO(
            lei="1234567890",
            state=FilingState.FILING_STARTED,
            institution_snapshot_id="Snapshot-1",
            filing_period=1,
        )
        filing2 = FilingDAO(
            lei="ABCDEFGHIJ",
            state=FilingState.FILING_STARTED,
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
        )
        submission2 = SubmissionDAO(
            submitter="test2@cfpb.gov",
            filing=2,
            state=SubmissionState.SUBMISSION_UPLOADED,
            validation_ruleset_version="v1",
        )
        submission3 = SubmissionDAO(
            submitter="test2@cfpb.gov",
            filing=2,
            state=SubmissionState.SUBMISSION_UPLOADED,
            validation_ruleset_version="v1",
        )
        transaction_session.add(submission1)
        transaction_session.add(submission2)
        transaction_session.add(submission3)

        await transaction_session.commit()

    async def test_add_filing_period(self, transaction_session: AsyncSession):
        new_fp = FilingPeriodDTO(
            name="FilingPeriod2024.1",
            start_period=datetime.now(),
            end_period=datetime.now(),
            due=datetime.now(),
            filing_type=FilingType.MANUAL,
        )
        res = await repo.upsert_filing_period(transaction_session, new_fp)
        assert res.id == 2
        assert res.filing_type == FilingType.MANUAL

    async def test_get_filing_period(self, query_session: AsyncSession):
        res = await repo.get_filing_period(query_session, filing_period_id=1)
        assert res.id == 1
        assert res.name == "FilingPeriod2024"
        assert res.filing_type == FilingType.MANUAL

    async def test_add_and_modify_filing(self, transaction_session: AsyncSession):
        new_filing = FilingDTO(
            lei="12345ABCDE",
            state=FilingState.FILING_IN_PROGRESS,
            institution_snapshot_id="Snapshot-1",
            filing_period=1,
        )
        res = await repo.upsert_filing(transaction_session, new_filing)
        assert res.id == 3
        assert res.lei == "12345ABCDE"
        assert res.state == FilingState.FILING_IN_PROGRESS

        mod_filing = FilingDTO(
            id=3,
            lei="12345ABCDE",
            state=FilingState.FILING_COMPLETE,
            institution_snapshot_id="Snapshot-1",
            filing_period=1,
        )
        res = await repo.upsert_filing(transaction_session, mod_filing)
        assert res.id == 3
        assert res.lei == "12345ABCDE"
        assert res.state == FilingState.FILING_COMPLETE

    async def test_get_filing(self, query_session: AsyncSession):
        res = await repo.get_filing_period(query_session, filing_period_id=1)
        assert res.id == 1
        assert res.name == "FilingPeriod2024"
        assert res.filing_type == FilingType.MANUAL

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

    async def test_add_submission(self, transaction_session: AsyncSession):
        res = await repo.add_submission(transaction_session, SubmissionDTO(submitter="test@cfpb.gov", filing=1))
        assert res.id == 4
        assert res.submitter == "test@cfpb.gov"
        assert res.filing == 1
        assert res.state == SubmissionState.SUBMISSION_UPLOADED

    async def test_update_submission(self, transaction_session: AsyncSession):
        res = await repo.add_submission(transaction_session, SubmissionDTO(submitter="test2@cfpb.gov", filing=2))
        res.state = SubmissionState.VALIDATION_IN_PROGRESS

        stmt = select(SubmissionDAO).filter(SubmissionDAO.id == 4)
        new_res1 = await transaction_session.scalar(stmt)
        assert new_res1.id == 4
        assert new_res1.filing == 2
        assert new_res1.state == SubmissionState.VALIDATION_IN_PROGRESS

        validation_json = self.get_error_json()
        res.validation_json = validation_json
        res.state = SubmissionState.VALIDATION_WITH_ERRORS

        stmt = select(SubmissionDAO).filter(SubmissionDAO.id == 4)
        new_res2 = await transaction_session.scalar(stmt)

        assert new_res2.id == 4
        assert new_res2.filing == 2
        assert new_res2.state == SubmissionState.VALIDATION_WITH_ERRORS
        assert new_res2.validation_json == validation_json

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

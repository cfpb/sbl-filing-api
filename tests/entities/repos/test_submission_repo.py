import pandas as pd
import pytest

import datetime
from datetime import datetime as dt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_scoped_session

from sbl_filing_api.entities.models.dao import (
    SubmissionDAO,
    FilingPeriodDAO,
    FilingDAO,
    FilingTaskProgressDAO,
    FilingTaskDAO,
    FilingType,
    FilingTaskState,
    SubmissionState,
    ContactInfoDAO,
    UserActionDAO,
)
from sbl_filing_api.entities.models.dto import FilingPeriodDTO, ContactInfoDTO
from sbl_filing_api.entities.models.model_enums import UserActionType
from sbl_filing_api.entities.repos import submission_repo as repo
from regtech_api_commons.models.auth import AuthenticatedUser
from pytest_mock import MockerFixture


class TestSubmissionRepo:
    @pytest.fixture(scope="function", autouse=True)
    async def setup(
        self, transaction_session: AsyncSession, mocker: MockerFixture, session_generator: async_scoped_session
    ):
        mocker.patch.object(repo, "SessionLocal", return_value=session_generator)

        user_action1 = UserActionDAO(
            id=1,
            user_id="test@local.host",
            user_name="signer name",
            user_email="test@local.host",
            action_type=UserActionType.SIGN,
            timestamp=dt.now(),
        )
        user_action2 = UserActionDAO(
            id=2,
            user_id="test@local.host",
            user_name="submitter name",
            user_email="test@local.host",
            action_type=UserActionType.SUBMIT,
            timestamp=dt.now(),
        )
        user_action3 = UserActionDAO(
            id=3,
            user_id="test@local.host",
            user_name="accepter name",
            user_email="test@local.host",
            action_type=UserActionType.ACCEPT,
            timestamp=dt.now(),
        )
        user_action4 = UserActionDAO(
            id=4,
            user_id="test@local.host",
            user_name="creator name",
            user_email="test@local.host",
            action_type=UserActionType.CREATE,
            timestamp=dt.now(),
        )

        transaction_session.add(user_action1)
        transaction_session.add(user_action2)
        transaction_session.add(user_action3)
        transaction_session.add(user_action4)

        filing_task_1 = FilingTaskDAO(name="Task-1", task_order=1)
        filing_task_2 = FilingTaskDAO(name="Task-2", task_order=2)
        transaction_session.add(filing_task_1)
        transaction_session.add(filing_task_2)

        filing_period = FilingPeriodDAO(
            code="2024",
            description="Filing Period 2024",
            start_period=dt.now(),
            end_period=dt.now(),
            due=dt.now(),
            filing_type=FilingType.ANNUAL,
        )
        transaction_session.add(filing_period)

        filing1 = FilingDAO(
            id=1,
            lei="1234567890",
            institution_snapshot_id="Snapshot-1",
            filing_period="2024",
        )
        filing2 = FilingDAO(
            id=2,
            lei="ABCDEFGHIJ",
            institution_snapshot_id="Snapshot-1",
            filing_period="2024",
        )
        filing3 = FilingDAO(
            id=3,
            lei="ZYXWVUTSRQP",
            institution_snapshot_id="Snapshot-1",
            filing_period="2024",
        )
        filing1.creator = user_action4
        filing2.creator = user_action4
        filing3.creator = user_action4

        transaction_session.add(filing1)
        transaction_session.add(filing2)
        transaction_session.add(filing3)

        filing_task1 = FilingTaskProgressDAO(
            id=1,
            filing=1,
            task_name="Task-1",
            user="testuser",
            state="IN_PROGRESS",
        )
        transaction_session.add(filing_task1)

        submission1 = SubmissionDAO(
            id=1,
            filing=1,
            submitter_id=2,
            state=SubmissionState.SUBMISSION_UPLOADED,
            validation_ruleset_version="v1",
            submission_time=dt.now(),
            filename="file1.csv",
        )

        submission2 = SubmissionDAO(
            id=2,
            filing=2,
            submitter_id=2,
            state=SubmissionState.SUBMISSION_UPLOADED,
            validation_ruleset_version="v1",
            submission_time=(dt.now() - datetime.timedelta(seconds=200)),
            filename="file2.csv",
        )
        submission3 = SubmissionDAO(
            id=3,
            filing=2,
            submitter_id=2,
            state=SubmissionState.SUBMISSION_UPLOADED,
            validation_ruleset_version="v1",
            submission_time=dt.now(),
            filename="file3.csv",
        )
        submission4 = SubmissionDAO(
            id=4,
            filing=1,
            state=SubmissionState.SUBMISSION_UPLOADED,
            validation_ruleset_version="v1",
            submission_time=(dt.now() - datetime.timedelta(seconds=400)),
            filename="file4.csv",
        )
        submission1.submitter = user_action2
        submission2.submitter = user_action2
        submission3.submitter = user_action2
        submission4.submitter = user_action2

        transaction_session.add(submission1)
        transaction_session.add(submission2)
        transaction_session.add(submission3)
        transaction_session.add(submission4)

        contact_info1 = ContactInfoDAO(
            id=1,
            filing=1,
            first_name="test_first_name_1",
            last_name="test_last_name_1",
            hq_address_street_1="address street 1",
            hq_address_street_2="",
            hq_address_street_3="",
            hq_address_street_4="",
            hq_address_city="Test City 1",
            hq_address_state="TS",
            hq_address_zip="12345",
            phone="112-345-6789",
            email="test1@cfpb.gov",
        )
        contact_info2 = ContactInfoDAO(
            id=2,
            filing=2,
            first_name="test_first_name_2",
            last_name="test_last_name_2",
            hq_address_street_1="address street 2",
            hq_address_street_2="",
            hq_address_street_3="",
            hq_address_street_4="",
            hq_address_city="Test City 2",
            hq_address_state="TS",
            hq_address_zip="12345",
            phone="212-345-6789",
            email="test2@cfpb.gov",
        )
        transaction_session.add(contact_info1)
        transaction_session.add(contact_info2)

        await transaction_session.commit()

    async def test_add_filing_period(self, transaction_session: AsyncSession):
        new_fp = FilingPeriodDTO(
            code="2024Q1",
            description="Filing Period 2024 Q1",
            start_period=dt.now(),
            end_period=dt.now(),
            due=dt.now(),
            filing_type=FilingType.ANNUAL,
        )
        res = await repo.upsert_filing_period(transaction_session, new_fp)
        assert res.code == "2024Q1"
        assert res.description == "Filing Period 2024 Q1"

    async def test_get_filing_periods(self, query_session: AsyncSession):
        res = await repo.get_filing_periods(query_session)
        assert len(res) == 1
        assert res[0].code == "2024"
        assert res[0].description == "Filing Period 2024"

    async def test_get_filing_period(self, query_session: AsyncSession):
        res = await repo.get_filing_period(query_session, filing_period="2024")
        assert res.code == "2024"
        assert res.filing_type == FilingType.ANNUAL

    async def test_add_filing(self, transaction_session: AsyncSession):
        user_action_create = await repo.add_user_action(
            transaction_session,
            user_id="123456-7890-ABCDEF-GHIJ",
            user_name="test creator",
            user_email="test@local.host",
            action_type=UserActionType.CREATE,
        )
        res = await repo.create_new_filing(
            transaction_session, lei="12345ABCDE", filing_period="2024", creator_id=user_action_create.id
        )
        assert res.id == 4
        assert res.filing_period == "2024"
        assert res.lei == "12345ABCDE"
        assert res.institution_snapshot_id is None
        assert res.creator.id == user_action_create.id
        assert res.creator.user_id == "123456-7890-ABCDEF-GHIJ"
        assert res.creator.user_name == "test creator"
        assert res.creator.user_email == "test@local.host"
        assert res.creator.action_type == UserActionType.CREATE

    async def test_modify_filing(self, transaction_session: AsyncSession):
        user_action_create = await repo.add_user_action(
            transaction_session,
            user_id="123456-7890-ABCDEF-GHIJ",
            user_name="test creator",
            user_email="test@local.host",
            action_type=UserActionType.CREATE,
        )

        mod_filing = FilingDAO(
            id=3,
            lei="ZYXWVUTSRQP",
            institution_snapshot_id="Snapshot-2",
            filing_period="2024",
            tasks=[],
            creator_id=user_action_create.id,
        )

        res = await repo.upsert_filing(transaction_session, mod_filing)
        assert res.id == 3
        assert res.filing_period == "2024"
        assert res.lei == "ZYXWVUTSRQP"
        assert res.institution_snapshot_id == "Snapshot-2"
        assert res.creator.id == user_action_create.id
        assert res.creator.user_id == "123456-7890-ABCDEF-GHIJ"
        assert res.creator.user_name == "test creator"

    async def test_get_filing_tasks(self, transaction_session: AsyncSession):
        tasks = await repo.get_filing_tasks(transaction_session)
        assert len(tasks) == 2
        assert tasks[0].name == "Task-1"
        assert tasks[1].name == "Task-2"

    async def test_mod_filing_task(self, query_session: AsyncSession, transaction_session: AsyncSession):
        user = AuthenticatedUser.from_claim({"preferred_username": "testuser"})
        await repo.update_task_state(
            query_session, lei="1234567890", filing_period="2024", task_name="Task-1", state="COMPLETED", user=user
        )
        seconds_now = dt.utcnow().timestamp()
        filing = await repo.get_filing(query_session, lei="1234567890", filing_period="2024")
        filing_task_states = filing.tasks

        assert len(filing_task_states) == 2
        assert filing_task_states[0].task.name == "Task-1"
        assert filing_task_states[0].id == 1
        assert filing_task_states[0].filing == 1
        assert filing_task_states[0].state == FilingTaskState.COMPLETED
        assert filing_task_states[0].user == "testuser"
        assert filing_task_states[0].change_timestamp.timestamp() == pytest.approx(
            seconds_now, abs=1.5
        )  # allow for possible 1.5 second difference

    async def test_add_filing_task(self, query_session: AsyncSession, transaction_session: AsyncSession):
        user = AuthenticatedUser.from_claim({"preferred_username": "testuser"})
        await repo.update_task_state(
            query_session, lei="1234567890", filing_period="2024", task_name="Task-2", state="IN_PROGRESS", user=user
        )
        seconds_now = dt.utcnow().timestamp()
        filing = await repo.get_filing(query_session, lei="1234567890", filing_period="2024")
        filing_task_states = filing.tasks

        assert len(filing_task_states) == 2
        assert filing_task_states[1].task.name == "Task-2"
        assert filing_task_states[1].id == 2
        assert filing_task_states[1].filing == 1
        assert filing_task_states[1].state == FilingTaskState.IN_PROGRESS
        assert filing_task_states[1].user == "testuser"
        assert filing_task_states[1].change_timestamp.timestamp() == pytest.approx(
            seconds_now, abs=1.0
        )  # allow for possible 1 second difference

    async def test_get_filing(self, query_session: AsyncSession, mocker: MockerFixture):
        spy_populate_missing_tasks = mocker.patch(
            "sbl_filing_api.entities.repos.submission_repo.populate_missing_tasks", wraps=repo.populate_missing_tasks
        )
        res1 = await repo.get_filing(query_session, lei="1234567890", filing_period="2024")
        assert res1.id == 1
        assert res1.filing_period == "2024"
        assert res1.lei == "1234567890"
        assert len(res1.tasks) == 2
        assert FilingTaskState.NOT_STARTED in set([t.state for t in res1.tasks])
        tasks1 = set([task_progress.task for task_progress in res1.tasks])
        assert len(tasks1) == 2
        assert "Task-1" in set([task.name for task in tasks1])
        assert "Task-2" in set([task.name for task in tasks1])

        res2 = await repo.get_filing(query_session, lei="ABCDEFGHIJ", filing_period="2024")
        assert res2.id == 2
        assert res2.filing_period == "2024"
        assert res2.lei == "ABCDEFGHIJ"
        assert len(res2.tasks) == 2
        assert FilingTaskState.NOT_STARTED in set([t.state for t in res2.tasks])
        tasks2 = set([task_progress.task for task_progress in res2.tasks])
        assert len(tasks2) == 2
        assert "Task-1" in set([task.name for task in tasks2])
        assert "Task-2" in set([task.name for task in tasks2])

        tasks_populated_filings = []
        for call in spy_populate_missing_tasks.call_args_list:
            args, _ = call
            filings = args[1]
            assert isinstance(filings[0], FilingDAO)
            tasks_populated_filings.append(filings[0].id)
        assert set(tasks_populated_filings) == set([1, 2])

    async def test_get_period_filings(self, query_session: AsyncSession, mocker: MockerFixture):
        results = await repo.get_period_filings(query_session, filing_period="2024")
        assert len(results) == 3
        assert results[0].id == 1
        assert results[0].lei == "1234567890"
        assert results[0].filing_period == "2024"
        assert results[1].id == 2
        assert results[1].lei == "ABCDEFGHIJ"
        assert results[1].filing_period == "2024"
        assert results[2].id == 3
        assert results[2].lei == "ZYXWVUTSRQP"
        assert results[2].filing_period == "2024"

    async def test_get_latest_submission(self, query_session: AsyncSession):
        res = await repo.get_latest_submission(query_session, lei="ABCDEFGHIJ", filing_period="2024")
        assert res.id == 3
        assert res.filing == 2
        assert res.state == SubmissionState.SUBMISSION_UPLOADED
        assert res.validation_ruleset_version == "v1"

    async def test_get_submission(self, query_session: AsyncSession):
        res = await repo.get_submission(incoming_session=query_session, submission_id=1)
        assert res.id == 1
        assert res.filing == 1
        assert res.state == SubmissionState.SUBMISSION_UPLOADED
        assert res.validation_ruleset_version == "v1"

    async def test_get_submissions(self, query_session: AsyncSession):
        res = await repo.get_submissions(query_session)
        assert len(res) == 4
        assert {1, 2, 3, 4} == set([s.id for s in res])
        assert res[1].filing == 2
        assert res[2].state == SubmissionState.SUBMISSION_UPLOADED

        res = await repo.get_submissions(query_session, lei="ABCDEFGHIJ", filing_period="2024")
        assert len(res) == 2
        assert {2, 3} == set([s.id for s in res])
        assert {2} == set([s.filing for s in res])
        assert {SubmissionState.SUBMISSION_UPLOADED} == set([s.state for s in res])

        # verify a filing with no submissions behaves ok
        res = await repo.get_submissions(query_session, lei="ZYXWVUTSRQP", filing_period="2024")
        assert len(res) == 0

    async def test_add_submission(self, transaction_session: AsyncSession):
        user_action_submit = await repo.add_user_action(
            transaction_session,
            user_id="123456-7890-ABCDEF-GHIJ",
            user_name="test submitter",
            user_email="test@local.host",
            action_type=UserActionType.SUBMIT,
        )

        res = await repo.add_submission(
            transaction_session, filing_id=1, filename="file1.csv", submitter_id=user_action_submit.id
        )
        assert res.id == 5
        assert res.filing == 1
        assert res.state == SubmissionState.SUBMISSION_STARTED
        assert res.submitter.id == user_action_submit.id
        assert res.submitter.user_id == user_action_submit.user_id
        assert res.submitter.user_name == user_action_submit.user_name
        assert res.submitter.user_email == user_action_submit.user_email
        assert res.submitter.action_type == UserActionType.SUBMIT

    async def test_update_submission(self, session_generator: async_scoped_session):
        user_action_submit = UserActionDAO(
            id=2,
            user_id="123456-7890-ABCDEF-GHIJ",
            user_name="test submitter",
            user_email="test@local.host",
            action_type=UserActionType.SUBMIT,
            timestamp=datetime.datetime.now(),
        )
        async with session_generator() as add_session:
            res = await repo.add_submission(
                add_session, filing_id=1, filename="file1.csv", submitter_id=user_action_submit.id
            )

        res.state = SubmissionState.VALIDATION_IN_PROGRESS
        res = await repo.update_submission(res)

        async def query_updated_dao():
            async with session_generator() as search_session:
                stmt = select(SubmissionDAO).filter(SubmissionDAO.id == 5)
                new_res1 = await search_session.scalar(stmt)
                assert new_res1.id == 5
                assert new_res1.filing == 1
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
                stmt = select(SubmissionDAO).filter(SubmissionDAO.id == 5)
                new_res2 = await search_session.scalar(stmt)
                assert new_res2.id == 5
                assert new_res2.filing == 1
                assert new_res2.state == SubmissionState.VALIDATION_WITH_ERRORS
                assert new_res2.validation_json == validation_json

        await query_updated_dao()

    async def test_get_contact_info(self, query_session: AsyncSession):
        res = await repo.get_contact_info(session=query_session, lei="ABCDEFGHIJ", filing_period="2024")

        assert res.id == 2
        assert res.filing == 2
        assert res.first_name == "test_first_name_2"
        assert res.last_name == "test_last_name_2"
        assert res.hq_address_street_1 == "address street 2"
        assert res.hq_address_street_2 == ""
        assert res.hq_address_street_3 == ""
        assert res.hq_address_street_4 == ""
        assert res.hq_address_city == "Test City 2"
        assert res.hq_address_state == "TS"
        assert res.hq_address_zip == "12345"
        assert res.phone == "212-345-6789"
        assert res.email == "test2@cfpb.gov"

    async def test_create_contact_info(self, transaction_session: AsyncSession):
        filing = await repo.update_contact_info(
            transaction_session,
            lei="ZYXWVUTSRQP",
            filing_period="2024",
            new_contact_info=ContactInfoDTO(
                first_name="test_first_name_3",
                last_name="test_last_name_3",
                hq_address_street_1="address street 1",
                hq_address_street_2="",
                hq_address_street_3="",
                hq_address_street_4="",
                hq_address_city="Test City",
                hq_address_state="TS",
                hq_address_zip="12345",
                phone="312-345-6789",
                email="test3@cfpb.gov",
            ),
        )

        assert filing.lei == "ZYXWVUTSRQP"
        assert filing.contact_info.id == 3
        assert filing.contact_info.filing == 3
        assert filing.contact_info.first_name == "test_first_name_3"
        assert filing.contact_info.last_name == "test_last_name_3"
        assert filing.contact_info.hq_address_street_1 == "address street 1"
        assert filing.contact_info.hq_address_street_2 == ""
        assert filing.contact_info.hq_address_street_3 == ""
        assert filing.contact_info.hq_address_street_4 == ""
        assert filing.contact_info.hq_address_city == "Test City"
        assert filing.contact_info.hq_address_state == "TS"
        assert filing.contact_info.hq_address_zip == "12345"
        assert filing.contact_info.phone == "312-345-6789"
        assert filing.contact_info.email == "test3@cfpb.gov"

    async def test_update_contact_info(self, transaction_session: AsyncSession):
        filing = await repo.update_contact_info(
            transaction_session,
            lei="ABCDEFGHIJ",
            filing_period="2024",
            new_contact_info=ContactInfoDTO(
                id=2,
                filing=2,
                first_name="test_first_name_upd",
                last_name="test_last_name_upd",
                hq_address_street_1="address street upd",
                hq_address_street_2="",
                hq_address_street_3="",
                hq_address_street_4="",
                hq_address_city="Test City upd",
                hq_address_state="TS",
                hq_address_zip="12345",
                phone="212-345-6789_upd",
                email="test2_upd@cfpb.gov",
            ),
        )

        assert filing.lei == "ABCDEFGHIJ"
        assert filing.contact_info.id == 2
        assert filing.contact_info.filing == 2
        assert filing.contact_info.first_name == "test_first_name_upd"
        assert filing.contact_info.last_name == "test_last_name_upd"
        assert filing.contact_info.hq_address_street_1 == "address street upd"
        assert filing.contact_info.hq_address_street_2 == ""
        assert filing.contact_info.hq_address_street_3 == ""
        assert filing.contact_info.hq_address_street_4 == ""
        assert filing.contact_info.hq_address_city == "Test City upd"
        assert filing.contact_info.hq_address_state == "TS"
        assert filing.contact_info.hq_address_zip == "12345"
        assert filing.contact_info.phone == "212-345-6789_upd"
        assert filing.contact_info.email == "test2_upd@cfpb.gov"

    async def test_get_user_action(self, query_session: AsyncSession):
        res = await repo.get_user_action(session=query_session, id=3)

        assert res.user_id == "test@local.host"
        assert res.user_name == "accepter name"
        assert res.user_email == "test@local.host"
        assert res.action_type == UserActionType.ACCEPT

    async def test_get_user_actions(self, query_session: AsyncSession):
        res = await repo.get_user_actions(session=query_session)

        assert len(res) == 4
        assert res[0].id == 1
        assert res[0].user_name == "signer name"

    async def test_add_user_action(self, query_session: AsyncSession, transaction_session: AsyncSession):
        user_actions_in_repo = await repo.get_user_actions(query_session)

        accepter = await repo.add_user_action(
            session=transaction_session,
            user_id="test2@cfpb.gov",
            user_name="test2 accepter name",
            user_email="test2@cfpb.gov",
            action_type=UserActionType.ACCEPT,
        )

        assert accepter.id == len(user_actions_in_repo) + 1
        assert accepter.user_id == "test2@cfpb.gov"
        assert accepter.user_name == "test2 accepter name"
        assert accepter.user_email == "test2@cfpb.gov"
        assert accepter.action_type == UserActionType.ACCEPT

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

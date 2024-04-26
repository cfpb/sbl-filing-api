import asyncio

from multiprocessing import Manager
from pytest_mock import MockerFixture
from sbl_filing_api.entities.models.dao import SubmissionDAO, SubmissionState
from sbl_filing_api.services.multithread_handler import check_future, handle_submission
from unittest.mock import Mock


class TestMultithreader:
    async def mock_future(self, sleeptime):
        await asyncio.sleep(sleeptime)
        return

    async def test_future_checker(self, mocker: MockerFixture):
        exec_check = Manager().dict()
        exec_check["continue"] = True

        mocker.patch("sbl_filing_api.services.multithread_handler.settings.expired_submission_check_secs", 4)
        repo_mock = mocker.patch("sbl_filing_api.entities.repos.submission_repo.expire_submission")
        log_mock = mocker.patch("sbl_filing_api.services.multithread_handler.logger")

        future = asyncio.get_event_loop().create_task(self.mock_future(5))
        await check_future(future, 1, exec_check)

        assert not exec_check["continue"]
        repo_mock.assert_called_with(1)
        log_mock.warning.assert_called_with(
            "Validation for submission 1 did not complete within the expected timeframe, will be set to VALIDATION_EXPIRED."
        )

        repo_mock.reset_mock()
        log_mock.reset_mock()
        future = asyncio.get_event_loop().create_task(self.mock_future(1))
        exec_check["continue"] = True
        await check_future(future, 2, exec_check)

        assert exec_check["continue"]
        assert not repo_mock.called
        assert not log_mock.called

    async def test_handler(self, mocker: MockerFixture):
        mock_sub = SubmissionDAO(
            id=1,
            filing=1,
            state=SubmissionState.SUBMISSION_UPLOADED,
            filename="submission.csv",
        )

        validation_mock = mocker.patch("sbl_filing_api.services.multithread_handler.validate_and_update_submission")
        mock_new_loop = mocker.patch("asyncio.new_event_loop")
        mock_event_loop = Mock()
        mock_new_loop.return_value = mock_event_loop

        set_loop_mock = mocker.patch("asyncio.set_event_loop")

        exec_check = Manager().dict()
        exec_check["continue"] = True

        handle_submission("2024", "123456789TESTBANK123", mock_sub, b"\00\00", exec_check)

        set_loop_mock.assert_called_with(mock_event_loop)
        validation_mock.assert_called_with("2024", "123456789TESTBANK123", mock_sub, b"\00\00", exec_check)
        mock_event_loop.close.assert_called_once()
from unittest.mock import ANY
from pytest_mock import MockerFixture
from sbl_filing_api.services.request_handler import send_confirmation_email


def test_send_confirmation_email(mocker: MockerFixture, caplog):
    # No errors
    post_mock = mocker.patch("sbl_filing_api.services.request_handler.httpx.post")
    post_mock.return_value.status_code = 200
    send_confirmation_email("full_name", "user@email.com", "contact@info.com", "confirmation", 12345)
    post_mock.assert_called_with(
        ANY,
        json={
            "confirmation_id": "confirmation",
            "contact_email": "contact@info.com",
            "signer_email": "user@email.com",
            "signer_name": "full_name",
            "timestamp": 12345,
        },
    )

    # With errors
    post_mock.side_effect = None
    post_mock.return_value.status_code = 400
    post_mock.return_value.text = "Email_response"
    send_confirmation_email("full_name", "user@email.com", "contact@info.com", "confirmation", 12345)
    assert "Email_response" in caplog.messages[0]

    post_mock.side_effect = IOError("test")
    send_confirmation_email("full_name", "user@email.com", "contact@info.com", "confirmation", 12345)
    assert "Failed to send confirmation email for full_name" in caplog.messages[1]

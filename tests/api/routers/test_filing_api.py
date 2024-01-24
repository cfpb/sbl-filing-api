from unittest.mock import Mock

from fastapi import FastAPI
from fastapi.testclient import TestClient
from pytest_mock import MockerFixture


class TestFilingApi:
    def test_get_periods(self, mocker: MockerFixture, app_fixture: FastAPI, get_filing_period_mock: Mock):
        client = TestClient(app_fixture)
        res = client.get("/v1/filing/periods")
        assert res.status_code == 200
        assert len(res.json()) == 1
        assert res.json()[0]["name"] == "FilingPeriod2024"

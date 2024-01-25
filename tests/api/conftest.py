import pytest

from fastapi import FastAPI
from pytest_mock import MockerFixture


@pytest.fixture
def app_fixture(mocker: MockerFixture) -> FastAPI:
    from main import app

    return app
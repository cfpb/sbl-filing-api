from sbl_filing_api.config import Settings


def test_postgres_dsn_building():
    mock_config = {
        "db_name": "test",
        "db_user": "user",
        "db_pwd": "\\z9-/tgb76#@",
        "db_host": "test:5432",
        "db_scehma": "test",
    }
    settings = Settings(**mock_config)
    assert str(settings.conn) == "postgresql+asyncpg://user:%5Cz9-%2Ftgb76%23%40@test:5432/test"


def test_default_maxes():
    settings = Settings()
    assert settings.max_validation_errors == 1000000
    assert settings.max_json_records == 10000
    assert settings.max_json_group_size == 200


def test_default_server_configs():
    settings = Settings()
    assert settings.server_config.host == "0.0.0.0"
    assert settings.server_config.workers == 4
    assert settings.server_config.reload is False
    assert settings.server_config.time_out == 65
    assert settings.server_config.port == 8888


def test_url_configs():
    settings = Settings()
    assert settings.mail_api_url == "http://mail-api:8765/internal/confirmation/send"

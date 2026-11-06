import pytest
from pydantic import ValidationError

from app.core.config import Settings


def make(monkeypatch, **env):
    for key in ("APP_NAME", "ENVIRONMENT", "LOG_LEVEL", "API_V1_PREFIX"):
        monkeypatch.delenv(key, raising=False)
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    return Settings(_env_file=None)


def test_defaults(monkeypatch):
    s = make(monkeypatch)
    assert s.app_name == "Parcial-P3-Algoritmos-IA"
    assert s.environment == "local"
    assert s.log_level == "INFO"
    assert s.api_v1_prefix == "/api/v1"


def test_override_from_environment(monkeypatch):
    s = make(monkeypatch, LOG_LEVEL="DEBUG", ENVIRONMENT="staging")
    assert s.log_level == "DEBUG"
    assert s.environment == "staging"


def test_invalid_value_names_the_setting(monkeypatch):
    with pytest.raises(ValidationError) as exc:
        make(monkeypatch, LOG_LEVEL="LOUD")
    assert "log_level" in str(exc.value)

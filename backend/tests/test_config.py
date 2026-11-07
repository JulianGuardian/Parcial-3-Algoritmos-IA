import pytest
from pydantic import ValidationError

from app.core.config import Settings


def make(monkeypatch, **env):
    for key in (
        "APP_NAME",
        "ENVIRONMENT",
        "LOG_LEVEL",
        "API_V1_PREFIX",
        "INTENT_CLASSIFIER",
        "INTENT_MODEL",
        "INTENT_MODEL_API_KEY",
    ):
        monkeypatch.delenv(key, raising=False)
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    return Settings(_env_file=None)


def test_defaults(monkeypatch):
    s = make(monkeypatch)
    assert s.app_name == "nubara-backend"
    assert s.environment == "local"
    assert s.log_level == "INFO"
    assert s.api_v1_prefix == "/api/v1"
    assert s.intent_classifier == "keyword"
    assert s.intent_model_api_key is None


def test_service_starts_with_keyword_classifier_and_no_key(monkeypatch):
    s = make(monkeypatch, INTENT_CLASSIFIER="keyword")
    assert s.intent_classifier == "keyword"
    assert s.intent_model_api_key is None


def test_intent_classifier_override(monkeypatch):
    s = make(monkeypatch, INTENT_CLASSIFIER="adk", INTENT_MODEL="gemini-2.0-pro")
    assert s.intent_classifier == "adk"
    assert s.intent_model == "gemini-2.0-pro"


def test_override_from_environment(monkeypatch):
    s = make(monkeypatch, LOG_LEVEL="DEBUG", ENVIRONMENT="staging")
    assert s.log_level == "DEBUG"
    assert s.environment == "staging"


def test_invalid_value_names_the_setting(monkeypatch):
    with pytest.raises(ValidationError) as exc:
        make(monkeypatch, LOG_LEVEL="LOUD")
    assert "log_level" in str(exc.value)

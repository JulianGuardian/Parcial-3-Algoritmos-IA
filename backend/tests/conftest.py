import io
import json
import logging

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.core.logging import JsonFormatter, RequestIdFilter
from app.main import create_app


@pytest.fixture
def log_lines():
    """Capture application log output exactly as the JSON formatter emits it."""
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(JsonFormatter())
    handler.addFilter(RequestIdFilter())
    logger = logging.getLogger("app")
    logger.addHandler(handler)
    try:
        yield lambda: [json.loads(line) for line in stream.getvalue().splitlines()]
    finally:
        logger.removeHandler(handler)


@pytest.fixture
def app():
    return create_app(Settings(_env_file=None))


@pytest.fixture
def client(app):
    return TestClient(app)

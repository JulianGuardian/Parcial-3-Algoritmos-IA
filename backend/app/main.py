from fastapi import FastAPI

from app.api import health
from app.api.v1.router import router as v1_router
from app.core.config import Settings, get_settings
from app.core.logging import configure_logging, register_request_middleware


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    configure_logging(settings.log_level)

    app = FastAPI(title=settings.app_name)
    register_request_middleware(app)
    app.include_router(health.router)
    app.include_router(v1_router, prefix=settings.api_v1_prefix)
    return app


app = create_app()

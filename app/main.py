"""FastAPI application factory and lifespan wiring."""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, ORJSONResponse
from fastapi.staticfiles import StaticFiles

from app import __version__
from app.api import links as links_api
from app.api import qr as qr_api
from app.api import redirect as redirect_api
from app.config import settings
from app.db import dispose_engine
from app.logging_config import configure_logging, get_logger
from app.middleware import RateLimitMiddleware, RequestIDMiddleware
from app.redis_client import close_redis, get_redis, init_redis
from app.services.geoip import close_geoip, get_geoip

logger = get_logger(__name__)

STATIC_DIR = Path(__file__).parent / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    await init_redis()
    get_geoip()  # eager-load reader so failures surface at startup
    logger.info("%s v%s started in %s mode", settings.app_name, __version__, settings.app_env)
    try:
        yield
    finally:
        await close_redis()
        close_geoip()
        await dispose_engine()
        logger.info("Shutdown complete")


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version=__version__,
        default_response_class=ORJSONResponse,
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # Middleware (outermost first).
    app.add_middleware(RateLimitMiddleware)
    app.add_middleware(RequestIDMiddleware)

    # Health checks.
    @app.get("/health", tags=["system"], include_in_schema=False)
    async def health() -> dict[str, str]:
        return {"status": "ok", "version": __version__}

    @app.get("/health/ready", tags=["system"], include_in_schema=False)
    async def ready() -> dict[str, str]:
        await get_redis().ping()
        return {"status": "ready"}

    # API routers (registered before the catch-all redirect route).
    app.include_router(links_api.router)
    app.include_router(qr_api.router)

    # Dashboard SPA.
    if STATIC_DIR.is_dir():
        app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

        @app.get("/", include_in_schema=False)
        async def dashboard() -> FileResponse:
            return FileResponse(STATIC_DIR / "index.html")

    # Catch-all redirect route MUST be registered last so it does not shadow
    # /api, /docs, /static, etc.
    app.include_router(redirect_api.router)

    return app


app = create_app()

import asyncio
import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.cleanup import run_periodic_cleanup
from app.core.config import get_settings
from app.core.logging import configure_logging

settings = get_settings()
configure_logging()
logger = logging.getLogger(__name__)

# Render sets this for every service automatically — a reliable signal we're
# deployed rather than running locally, independent of whether ENVIRONMENT
# was ever set. If CORS is still at its localhost-only default here, every
# browser request from the real frontend will be silently blocked by CORS
# (the backend itself stays healthy and reachable via curl, which is why
# this fails quietly instead of loudly) — log it plainly so it shows up in
# Render's logs instead of only manifesting as a confusing "offline" badge.
if os.environ.get("RENDER") and settings.cors_origin_list == ["http://localhost:3000"]:
    logger.warning(
        "cors.misconfigured_for_deployment",
        extra={
            "detail": (
                "CORS_ORIGINS is still the localhost-only default on a Render "
                "deployment. Set CORS_ORIGINS to your frontend's real origin "
                "(e.g. https://your-app.vercel.app) in the Render service's "
                "environment variables, or CORS_ORIGIN_REGEX for a pattern "
                "like preview URLs. Until then, the frontend will show "
                "'Backend Offline' even though this server is healthy."
            ),
        },
    )


@asynccontextmanager
async def lifespan(_: FastAPI):
    cleanup_task = asyncio.create_task(
        run_periodic_cleanup(settings.job_ttl_minutes, settings.cleanup_interval_minutes)
    )
    try:
        yield
    finally:
        cleanup_task.cancel()


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_origin_regex=settings.cors_origin_regex,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.api_v1_prefix)


@app.get("/", tags=["root"])
def root() -> dict[str, str]:
    return {"service": settings.app_name, "docs": "/api/docs"}

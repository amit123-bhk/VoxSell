"""
VoxSell - Autonomous AI Sales Voice Agent.
Main FastAPI application entrypoint.
"""

import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncGenerator
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from app.config import get_settings
from app.api.health import router as health_router
from app.api.websocket_call import router as voice_router
from app.api.kb_admin import router as kb_router
from app.api.analytics import router as analytics_router
from app.api.auth import router as auth_router
from app.api.leads import router as leads_router

# Setup application logging
settings = get_settings()
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d - %(message)s",
)
logger = logging.getLogger("voxsell")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Application lifespan manager.
    Handles startup hooks (pools, connections) and shutdown cleanup.
    """
    logger.info("Initializing VoxSell Voice Agent Engine...")
    logger.info(f"Environment: {settings.APP_ENV} | Host: {settings.APP_HOST}:{settings.APP_PORT}")
    yield
    logger.info("Shutting down VoxSell application gracefully...")


def create_application() -> FastAPI:
    """
    Application factory for VoxSell API.
    Configures middlewares, routers, and lifecycle events.
    """
    app = FastAPI(
        title="VoxSell — Autonomous AI Sales Voice Agent",
        description="Real-time multi-lingual AI sales voice agent with BANT qualification, RAG, and automated CRM sync.",
        version="0.1.0",
        lifespan=lifespan,
    )

    # CORS configuration
    cors_origins = (
        settings.CORS_ORIGINS
        if isinstance(settings.CORS_ORIGINS, list)
        else [settings.CORS_ORIGINS]
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register routers
    app.include_router(health_router)
    app.include_router(voice_router)
    app.include_router(kb_router)
    app.include_router(analytics_router)
    app.include_router(auth_router)
    app.include_router(leads_router)

    @app.get("/call", include_in_schema=False)
    async def serve_call_test_page():
        """Serves the real-time audio test interface for browser verification."""
        html_path = Path(__file__).resolve().parent.parent.parent / "frontend" / "call.html"
        return FileResponse(html_path)

    dist_path = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"
    if dist_path.exists():
        from fastapi.staticfiles import StaticFiles
        app.mount("/", StaticFiles(directory=dist_path, html=True), name="frontend")

    return app


app = create_application()

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.APP_HOST,
        port=settings.APP_PORT,
        reload=settings.DEBUG,
    )

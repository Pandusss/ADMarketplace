from __future__ import annotations

import asyncio
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import FileResponse
from starlette.staticfiles import StaticFiles
from starlette.exceptions import HTTPException

from app.api.router import api_router
from app.core.config import settings
from app.db.models import Base
from app.db.session import engine
from app.schemas.errors import ErrorResponse, ErrorDetail
from app.infra.telegram.handlers import process_update
from app.infra.telegram.poller import run_polling_loop
from app.infra.ton.webhook_manager import ton_webhook_manager
from app.infra.websocket.manager import manager as ws_manager
from app.infra.ton.sender import ton_sender
from app.domain.events.handlers import register_signal_handlers
from app.domain.exceptions import DomainError, NotFoundError, ForbiddenError, ConflictError, ValidationError, InfrastructureError

import logging

logger = logging.getLogger(__name__)

def create_app() -> FastAPI:
    """
    FastAPI application factory.
    """
    # Register internal signal handlers
    register_signal_handlers()

    app = FastAPI(title=settings.app_name)

    if settings.environment == "local":
        app.add_middleware(
            CORSMiddleware,
            allow_origin_regex=r"http://localhost:\d+",
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )


    @app.middleware("http")
    async def strip_api_trailing_slash(request: Request, call_next):
        """Strip trailing slash from /api/… requests so routes match cleanly."""
        path = request.scope["path"]
        if path.startswith("/api/") and path.endswith("/") and len(path) > 5:
            request.scope["path"] = path.rstrip("/")
        return await call_next(request)

    # API lives under /api (so frontend can call relative /api without hardcoding domains)
    app.include_router(api_router, prefix="/api")

    @app.on_event("startup")
    async def _startup() -> None:
        if settings.environment == "local":
            Base.metadata.create_all(bind=engine)
            logger.info("DEV mode: tables ensured via create_all (use 'alembic upgrade head' in production)")
        else:
            logger.info("Production mode: run 'alembic upgrade head' to apply migrations")

        # Telegram updates: polling getUpdates (like infinity_polling style; no public backend required).
        if settings.telegram_bot_token:
            logger.info("Spawning Telegram polling task...")
            app.state.telegram_poll_task = asyncio.create_task(run_polling_loop(process_update))
        
        # TON webhook: register webhook endpoint with tonapi.io for instant payment notifications
        if settings.vite_api_base_url:
            ton_webhook_url = settings.vite_api_base_url.rstrip("/") + "/api/webhooks/ton"
            try:
                await ton_webhook_manager.ensure_webhook(ton_webhook_url)
                logger.info("TON webhook registered: %s", ton_webhook_url)
            except Exception:
                logger.error("Failed to register TON webhook", exc_info=True)

        # WebSocket manager: start Redis Pub/Sub listener
        await ws_manager.start_redis_listener()
        
        # Initialize persistent HTTP client for TON
        await ton_sender.start()

    @app.on_event("shutdown")
    async def _shutdown() -> None:
        task = getattr(app.state, "telegram_poll_task", None)
        if task:
            task.cancel()
            try:
                await task
            except BaseException:
                pass
        
        await ws_manager.stop_redis_listener()
        await ton_sender.stop()

    # Serve built frontend (single-domain prod) if present.
    repo_root = Path(__file__).resolve().parents[2]
    dist_dir = repo_root / "frontend" / "dist"
    index_html = dist_dir / "index.html"

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content=ErrorResponse(
                error=ErrorDetail(
                    code=f"HTTP_{exc.status_code}",
                    message=exc.detail if isinstance(exc.detail, str) else "An error occurred",
                    detail=exc.detail if not isinstance(exc.detail, str) else None
                )
            ).model_dump()
        )

    @app.exception_handler(DomainError)
    async def domain_exception_handler(request: Request, exc: DomainError):
        status_map = {
            NotFoundError: 404,
            ForbiddenError: 403,
            ConflictError: 409,
            ValidationError: 422,
            InfrastructureError: 500,
        }
        status_code = status_map.get(type(exc), 500)
        return JSONResponse(
            status_code=status_code,
            content=ErrorResponse(
                error=ErrorDetail(
                    code=f"HTTP_{status_code}",
                    message=exc.detail,
                )
            ).model_dump()
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        return JSONResponse(
            status_code=422,
            content=ErrorResponse(
                error=ErrorDetail(
                    code="VALIDATION_ERROR",
                    message="Input validation failed",
                    detail=exc.errors()
                )
            ).model_dump()
        )

    if dist_dir.exists() and index_html.exists():
        # Serve compiled assets (JS/CSS/images) from /assets
        assets_dir = dist_dir / "assets"
        if assets_dir.exists():
            app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")

        # SPA fallback: serve index.html for any unknown non-API path,
        # or try to serve root-level static files (favicon.ico, etc.)
        @app.get("/{full_path:path}", include_in_schema=False)
        def spa_fallback(full_path: str):
            if full_path.startswith("api/"):
                raise HTTPException(status_code=404, detail="Not Found")
            # Try serving exact file from dist/ (e.g. favicon.ico, robots.txt)
            file_path = dist_dir / full_path
            if full_path and file_path.exists() and file_path.is_file():
                return FileResponse(str(file_path))
            return FileResponse(str(index_html))

    return app


app = create_app()


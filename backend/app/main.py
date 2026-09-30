"""FastAPI application entrypoint."""
from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager

import jwt
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.middleware import CSRFMiddleware, RateLimitMiddleware, RequestLogMiddleware
from app.api.router import api_router
from app.core.config import settings
from app.core.errors import AppError, error_body
from app.core.logging import configure_logging, get_logger
from app.services.reminders import reminder_loop

configure_logging()
logger = get_logger("app")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Start/stop background jobs alongside the API."""
    task: asyncio.Task | None = None
    if settings.due_reminder_enabled:
        task = asyncio.create_task(reminder_loop())
        logger.info("Due-date reminder job started (every %sh)",
                    settings.due_reminder_interval_hours)
    try:
        yield
    finally:
        if task:
            task.cancel()
            try:
                await task
            except (asyncio.CancelledError, Exception):
                pass


app = FastAPI(
    title=f"{settings.app_name} API",
    version="1.0.0",
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
    redoc_url=None,
    lifespan=lifespan,
)

# CORS (frontend served same-origin in prod via Caddy; explicit origins for dev).
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(CSRFMiddleware)
app.add_middleware(
    RateLimitMiddleware,
    limit=settings.auth_rate_limit_requests,
    window_seconds=settings.auth_rate_limit_window_seconds,
)
app.add_middleware(RequestLogMiddleware)


# ── Exception handlers → consistent error envelope ─────────────
@app.exception_handler(AppError)
async def handle_app_error(request: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content=error_body(exc.code, exc.message, exc.details),
    )


@app.exception_handler(RequestValidationError)
async def handle_validation(request: Request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content=error_body("VALIDATION_ERROR", "Request validation failed", exc.errors()),
    )


@app.exception_handler(jwt.PyJWTError)
async def handle_jwt(request: Request, exc: jwt.PyJWTError) -> JSONResponse:
    return JSONResponse(
        status_code=401, content=error_body("UNAUTHENTICATED", "Invalid session")
    )


@app.exception_handler(StarletteHTTPException)
async def handle_http(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content=error_body("HTTP_ERROR", str(exc.detail)),
    )


@app.exception_handler(Exception)
async def handle_unexpected(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content=error_body("INTERNAL_ERROR", "An unexpected error occurred"),
    )


app.include_router(api_router, prefix="/api")


@app.get("/api")
async def root() -> dict:
    return {"name": settings.app_name, "status": "ok", "docs": "/api/docs"}

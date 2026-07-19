"""FastAPI application entry point, middleware, and global handlers."""

import asyncio
from contextlib import asynccontextmanager, suppress
from pathlib import Path

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.api.v1 import api_router
from app.core.config import settings
from app.core.distributed_lock import try_acquire_lock
from app.core.errors import ErrorCode, build_error_payload, normalize_http_exception_detail
from app.core.health import check_database_connection, ping_redis
from app.core.logging import get_logger, request_id_ctx_var, setup_logging
from app.core.middleware import get_or_create_request_id
from app.core.security_middleware import HttpsRedirectMiddleware, RequestBodySizeLimitMiddleware
from app.core.startup import bootstrap_catalog_seed, bootstrap_super_admin
from app.db.database import async_session_maker
from app.services.order_expiry_service import cancel_expired_pending_payment_orders

setup_logging()
logger = get_logger(__name__)


async def _order_expiry_worker(stop_event: asyncio.Event) -> None:
    """Periodically cancel abandoned unpaid purchase orders."""
    while not stop_event.is_set():
        try:
            if await try_acquire_lock(
                "order_expiry_sweep",
                settings.ORDER_EXPIRY_SWEEP_INTERVAL_SECONDS,
            ):
                async with async_session_maker() as session:
                    cancelled = await cancel_expired_pending_payment_orders(session)
                    if cancelled:
                        await session.commit()
        except Exception:
            logger.exception("Order expiry sweep failed")
        try:
            await asyncio.wait_for(
                stop_event.wait(),
                timeout=settings.ORDER_EXPIRY_SWEEP_INTERVAL_SECONDS,
            )
        except TimeoutError:
            continue


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Run startup hooks before serving traffic."""
    await bootstrap_super_admin()
    await bootstrap_catalog_seed()
    stop_event = asyncio.Event()
    expiry_task = asyncio.create_task(_order_expiry_worker(stop_event))
    try:
        yield
    finally:
        stop_event.set()
        expiry_task.cancel()
        with suppress(asyncio.CancelledError):
            await expiry_task


app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Industrial Lathe Tools API - Complete product management system",
    version=settings.VERSION,
    docs_url="/api/docs" if settings.ENABLE_API_DOCS else None,
    redoc_url="/api/redoc" if settings.ENABLE_API_DOCS else None,
    openapi_url="/api/openapi.json" if settings.ENABLE_API_DOCS else None,
    lifespan=lifespan,
    # Avoid Starlette slash-redirects that rebuild absolute URLs with the wrong
    # scheme (http) when sitting behind TLS-terminating Nginx.
    redirect_slashes=False,
)

# Honor X-Forwarded-Proto / X-Forwarded-For from the local reverse proxy.
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

_proxy_trusted = settings.trusted_proxies_list or ["127.0.0.1"]
app.add_middleware(ProxyHeadersMiddleware, trusted_hosts=_proxy_trusted)

if settings.trusted_hosts_list:
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.trusted_hosts_list)

app.add_middleware(HttpsRedirectMiddleware)
app.add_middleware(RequestBodySizeLimitMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=settings.cors_origins_list != ["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

if settings.ENABLE_METRICS:
    from prometheus_fastapi_instrumentator import Instrumentator

    Instrumentator(
        should_group_status_codes=True,
        excluded_handlers=["/metrics", "/health", "/ready"],
    ).instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)

app.include_router(api_router, prefix="/api/v1")
PROJECT_ROOT = Path(__file__).resolve().parents[1]
_uploads_root = PROJECT_ROOT / "data" / "uploads"
_uploads_root.mkdir(parents=True, exist_ok=True)
app.mount("/static/uploads", StaticFiles(directory=_uploads_root), name="uploads")


def custom_openapi():
    """Build OpenAPI and mark optional-Bearer routes as anonymous-capable."""
    if app.openapi_schema:
        return app.openapi_schema

    from fastapi.openapi.utils import get_openapi

    schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )

    # Required auth uses OAuth2PasswordBearer; optional auth uses HTTPBearer(auto_error=False).
    # OpenAPI treats a lone security requirement as mandatory — add {} so anonymous is allowed.
    for _path, methods in schema.get("paths", {}).items():
        for method, operation in methods.items():
            if method.startswith("x-") or not isinstance(operation, dict):
                continue
            security = operation.get("security")
            if security == [{"HTTPBearer": []}]:
                operation["security"] = [{}, {"HTTPBearer": []}]

    app.openapi_schema = schema
    return app.openapi_schema


app.openapi = custom_openapi


@app.middleware("http")
async def request_context_middleware(request: Request, call_next):
    request_id = get_or_create_request_id(request)
    token = request_id_ctx_var.set(request_id)
    try:
        response = await call_next(request)
    finally:
        request_id_ctx_var.reset(token)

    response.headers["X-Request-ID"] = request_id
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
    response.headers["Content-Security-Policy"] = "default-src 'self'; frame-ancestors 'none'; base-uri 'self'"
    return response


@app.get("/", tags=["System"])
async def root():
    return {
        "message": "Karzar Industrial Lathe Tools API",
        "version": settings.VERSION,
        "docs": "/api/docs" if settings.ENABLE_API_DOCS else None,
        "status": "running",
    }


@app.get("/health", tags=["System"], summary="Health check")
async def health_check():
    """Liveness probe — returns 200 when the process is running."""
    logger.info("Health check requested")
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "status": "healthy",
            "service": settings.PROJECT_NAME,
            "version": settings.VERSION,
        },
    )


@app.get("/ready", tags=["System"], summary="Readiness check")
async def readiness_check():
    """Readiness probe — verifies database (and Redis when configured)."""
    db_ok = await check_database_connection()
    redis_ok = await ping_redis()

    if db_ok and redis_ok:
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status": "ready",
                "service": settings.PROJECT_NAME,
                "database": "ok",
                "redis": "ok" if settings.redis_enabled else "disabled",
            },
        )

    logger.error("Readiness check failed: db_ok=%s redis_ok=%s", db_ok, redis_ok)
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={
            "status": "not_ready",
            "database": "ok" if db_ok else "unavailable",
            "redis": "ok" if redis_ok else ("disabled" if not settings.redis_enabled else "unavailable"),
        },
    )


@app.get("/api/v1", tags=["System"])
async def api_info():
    return {
        "api_version": "v1",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "endpoints": {
            "products": "/api/v1/products",
            "categories": "/api/v1/categories",
            "auth": "/api/v1/auth",
            "docs": "/api/docs" if settings.ENABLE_API_DOCS else None,
        },
    }


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request, exc: StarletteHTTPException):
    """Normalize all HTTPException responses to the standard error envelope."""
    content = normalize_http_exception_detail(exc.status_code, exc.detail)
    return JSONResponse(status_code=exc.status_code, content=content, headers=getattr(exc, "headers", None))


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc: RequestValidationError):
    """Map Pydantic validation errors to VALIDATION_FAILED with field details."""
    content = normalize_http_exception_detail(status.HTTP_422_UNPROCESSABLE_CONTENT, exc.errors())
    return JSONResponse(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, content=content)


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Catch-all handler to prevent raw tracebacks leaking to clients."""
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=build_error_payload(
            error_code=ErrorCode.INTERNAL_ERROR,
            message="Internal server error",
        ),
    )

# app/main.py
from contextlib import asynccontextmanager

from fastapi import FastAPI, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqladmin import Admin
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.sessions import SessionMiddleware

from app.admin.auth import admin_auth_backend
from app.admin.views import ProductAdmin, CategoryAdmin, BrandAdmin, ProductImageAdmin, UserAdmin
from app.api.v1 import api_router
from app.core.config import settings
from app.core.errors import ErrorCode, build_error_payload, normalize_http_exception_detail
from app.core.health import check_database_connection, ping_redis
from app.core.logging import setup_logging, get_logger
from app.core.startup import bootstrap_super_admin
from app.db.database import engine

setup_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await bootstrap_super_admin()
    yield


app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Industrial Lathe Tools API - Complete product management system",
    version=settings.VERSION,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
)

app.add_middleware(SessionMiddleware, secret_key=settings.SECRET_KEY)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

admin = Admin(app, engine, authentication_backend=admin_auth_backend)
admin.add_view(CategoryAdmin)
admin.add_view(BrandAdmin)
admin.add_view(ProductAdmin)
admin.add_view(ProductImageAdmin)
admin.add_view(UserAdmin)

app.include_router(api_router, prefix="/api/v1")


@app.get("/", tags=["System"])
async def root():
    return {
        "message": "Karzar Industrial Lathe Tools API",
        "version": settings.VERSION,
        "docs": "/api/docs",
        "status": "running",
    }


@app.get("/health", tags=["System"], summary="Health check")
async def health_check():
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
            "docs": "/api/docs",
            "admin": "/admin",
        },
    }


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request, exc: StarletteHTTPException):
    content = normalize_http_exception_detail(exc.status_code, exc.detail)
    return JSONResponse(status_code=exc.status_code, content=content, headers=getattr(exc, "headers", None))


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc: RequestValidationError):
    content = normalize_http_exception_detail(status.HTTP_422_UNPROCESSABLE_CONTENT, exc.errors())
    return JSONResponse(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, content=content)


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=build_error_payload(
            error_code=ErrorCode.INTERNAL_ERROR,
            message="Internal server error",
        ),
    )

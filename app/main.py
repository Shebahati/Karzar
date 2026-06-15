# app/main.py
from fastapi import FastAPI, status
from fastapi.responses import JSONResponse

# Import security logging setup
from app.core.logging import setup_logging, get_logger
from app.core.config import settings

# Setup logging
setup_logging()
logger = get_logger(__name__)

# ایمپورت صحیح روتر محصولات
from app.api.endpoints.product import router as product_router
from app.api.endpoints.auth import router as auth_router

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Industrial Lathe Tools API - Complete product management system",
    version=settings.VERSION,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

# Include routers
app.include_router(product_router, prefix="/api/v1/products", tags=["Products"])
app.include_router(auth_router, prefix="/api/v1/auth", tags=["Authentication"])


@app.get("/", tags=["System"])
async def root():
    """Root endpoint - API information."""
    return {
        "message": "Karzar Industrial Lathe Tools API",
        "version": settings.VERSION,
        "docs": "/api/docs",
        "status": "running"
    }


@app.get("/health", tags=["System"], summary="Health check")
async def health_check():
    """
    Health check endpoint for monitoring and orchestration.
    Returns 200 if service is healthy.
    """
    logger.info("Health check requested")
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "status": "healthy",
            "service": settings.PROJECT_NAME,
            "version": settings.VERSION,
        }
    )


@app.get("/ready", tags=["System"], summary="Readiness check")
async def readiness_check():
    """
    Readiness check endpoint for Kubernetes/Docker orchestration.
    Returns 200 if service is ready to accept traffic.
    """
    try:
        logger.debug("Readiness check requested")
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status": "ready",
                "service": settings.PROJECT_NAME,
            }
        )
    except Exception as e:
        logger.error(f"Readiness check failed: {str(e)}")
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "not_ready",
                "error": str(e),
            }
        )


@app.get("/api/v1", tags=["System"])
async def api_info():
    """API version information."""
    return {
        "api_version": "v1",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "endpoints": {
            "products": "/api/v1/products",
            "auth": "/api/v1/auth",
            "docs": "/api/docs",
        }
    }


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler for unhandled errors."""
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error"}
    )

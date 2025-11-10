"""
Aplicación FastAPI principal
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.core.database import db
from app.core.logging import setup_logging, get_logger
from app.core.errors import BaseServiceError
from app.api.middleware import RequestLoggingMiddleware
from app.api.routes import health, trips, wialon, whatsapp

# Configurar logging
setup_logging(log_level=settings.log_level, json_logs=settings.json_logs)
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifecycle manager para la aplicación

    Maneja startup y shutdown de recursos
    """
    # Startup
    logger.info("application_starting", environment=settings.environment)

    try:
        # Conectar a la base de datos MySQL
        await db.connect(
            host=settings.mysql_host,
            port=settings.mysql_port,
            database=settings.mysql_database,
            user=settings.mysql_user,
            password=settings.mysql_password,
            min_size=settings.db_pool_min_size,
            max_size=settings.db_pool_max_size,
            timeout=settings.db_pool_timeout,
        )
        logger.info("database_connected", db_type="mysql", database=settings.mysql_database)

    except Exception as e:
        logger.error("application_startup_failed", error=str(e))
        raise

    logger.info("application_ready")

    yield

    # Shutdown
    logger.info("application_shutting_down")

    try:
        await db.disconnect()
        logger.info("database_disconnected")
    except Exception as e:
        logger.error("database_disconnect_failed", error=str(e))

    logger.info("application_stopped")


# Crear aplicación FastAPI
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Microservicio para gestión de flotas logísticas",
    lifespan=lifespan,
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Middleware personalizado
app.add_middleware(RequestLoggingMiddleware)


# Exception handlers
@app.exception_handler(BaseServiceError)
async def service_error_handler(request, exc: BaseServiceError):
    """Handler para errores de servicio"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": {
                "code": exc.code,
                "message": exc.message,
                "context": exc.context,
            },
            "trace_id": getattr(request.state, "trace_id", None),
        },
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc: Exception):
    """Handler para excepciones generales"""
    import traceback
    error_traceback = traceback.format_exc()
    logger.error("unhandled_exception", error=str(exc), type=type(exc).__name__, traceback=error_traceback)
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": {
                "code": "INTERNAL_ERROR",
                "message": str(exc),
                "type": type(exc).__name__,
                "traceback": error_traceback,  # DEBUG: Incluir traceback en desarrollo
            },
            "trace_id": getattr(request.state, "trace_id", None),
        },
    )


# Incluir routers
app.include_router(health.router, prefix=settings.api_prefix)
app.include_router(trips.router, prefix=settings.api_prefix)
app.include_router(wialon.router, prefix=settings.api_prefix)
app.include_router(whatsapp.router, prefix=settings.api_prefix)


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment,
        "docs": "/docs" if settings.debug else "disabled",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug,
        log_level=settings.log_level.lower(),
    )


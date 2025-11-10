"""
Middleware personalizado para FastAPI
"""
import time
import uuid
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from app.core.logging import get_logger, log_context, clear_log_context
from app.core.context import set_trace_id, clear_trace_id

logger = get_logger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware para logging de requests"""

    async def dispatch(self, request: Request, call_next):
        # Generar o extraer trace_id de headers
        trace_id = request.headers.get("X-Trace-ID") or str(uuid.uuid4())
        
        # Establecer trace_id en el contexto global
        set_trace_id(trace_id)
        log_context(trace_id=trace_id)

        # Agregar trace_id al request state
        request.state.trace_id = trace_id

        # Registrar inicio del request
        start_time = time.time()
        logger.info(
            "request_started",
            method=request.method,
            path=request.url.path,
            client_host=request.client.host if request.client else None,
        )

        # Procesar request
        try:
            response = await call_next(request)

            # Calcular tiempo de procesamiento
            process_time = time.time() - start_time

            # Registrar fin del request
            logger.info(
                "request_completed",
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
                process_time_ms=round(process_time * 1000, 2),
            )

            # Agregar headers de respuesta
            response.headers["X-Trace-ID"] = trace_id
            response.headers["X-Process-Time"] = str(round(process_time * 1000, 2))

            return response

        except Exception as e:
            # Log error
            process_time = time.time() - start_time
            logger.error(
                "request_failed",
                method=request.method,
                path=request.url.path,
                error=str(e),
                process_time_ms=round(process_time * 1000, 2),
            )
            raise

        finally:
            # Limpiar contexto del logger y trace_id
            clear_log_context()
            clear_trace_id()


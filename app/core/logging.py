"""
Sistema de logging estructurado con structlog
"""
import logging
import sys
from typing import Any, Dict

import structlog
from structlog.types import EventDict, Processor


def add_app_context(logger: Any, method_name: str, event_dict: EventDict) -> EventDict:
    """Agregar contexto de la aplicación a los logs"""
    event_dict["app"] = "logistics-microservice"
    return event_dict


def setup_logging(log_level: str = "INFO", json_logs: bool = True) -> None:
    """
    Configurar el sistema de logging estructurado
    
    Args:
        log_level: Nivel de logging (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        json_logs: Si es True, los logs se emiten en formato JSON
    """
    # Procesadores comunes
    shared_processors: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        add_app_context,
    ]

    if json_logs:
        # Logs en formato JSON para producción
        structlog.configure(
            processors=[
                *shared_processors,
                structlog.processors.UnicodeDecoder(),
                structlog.processors.JSONRenderer(),
            ],
            wrapper_class=structlog.stdlib.BoundLogger,
            context_class=dict,
            logger_factory=structlog.stdlib.LoggerFactory(),
            cache_logger_on_first_use=True,
        )
    else:
        # Logs formateados para desarrollo
        structlog.configure(
            processors=[
                *shared_processors,
                structlog.dev.ConsoleRenderer(colors=True),
            ],
            wrapper_class=structlog.stdlib.BoundLogger,
            context_class=dict,
            logger_factory=structlog.stdlib.LoggerFactory(),
            cache_logger_on_first_use=True,
        )

    # Configurar logging estándar de Python
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, log_level.upper()),
    )

    # Reducir verbosidad de librerías externas
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("asyncpg").setLevel(logging.WARNING)


def get_logger(name: str = __name__) -> structlog.stdlib.BoundLogger:
    """
    Obtener un logger estructurado
    
    Args:
        name: Nombre del logger (generalmente __name__ del módulo)
    
    Returns:
        Logger estructurado configurado
    """
    return structlog.get_logger(name)


def log_context(**kwargs: Any) -> None:
    """
    Agregar contexto al logger actual
    
    Args:
        **kwargs: Pares clave-valor para agregar al contexto
    """
    structlog.contextvars.bind_contextvars(**kwargs)


def clear_log_context() -> None:
    """Limpiar el contexto del logger actual"""
    structlog.contextvars.clear_contextvars()


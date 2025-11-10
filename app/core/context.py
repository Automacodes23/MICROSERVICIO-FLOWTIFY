"""
Contexto global de request para propagación de trace_id
"""
from contextvars import ContextVar
from typing import Optional
import uuid

# ContextVar para almacenar el trace_id del request actual
_trace_id_var: ContextVar[Optional[str]] = ContextVar("trace_id", default=None)


def set_trace_id(trace_id: str) -> None:
    """
    Establecer trace_id para el contexto actual
    
    Args:
        trace_id: ID de traza del request
    """
    _trace_id_var.set(trace_id)


def get_trace_id() -> str:
    """
    Obtener trace_id del contexto actual
    
    Returns:
        trace_id actual o uno nuevo si no existe
    """
    trace_id = _trace_id_var.get()
    if not trace_id:
        trace_id = str(uuid.uuid4())
        set_trace_id(trace_id)
    return trace_id


def clear_trace_id() -> None:
    """Limpiar trace_id del contexto"""
    _trace_id_var.set(None)


def get_trace_headers() -> dict:
    """
    Obtener headers con trace_id para requests externos
    
    Returns:
        Diccionario con header X-Trace-ID
    """
    return {"X-Trace-ID": get_trace_id()}


"""
Funciones helper útiles
"""
from datetime import datetime, timezone
from typing import Any, Dict


def get_utc_now() -> datetime:
    """Obtener timestamp actual en UTC"""
    return datetime.now(timezone.utc)


def format_phone_number(phone: str) -> str:
    """
    Formatear número de teléfono para WhatsApp

    Args:
        phone: Número de teléfono (puede incluir +, espacios, etc.)

    Returns:
        Número formateado (ej: 5214771234567)
    """
    # Remover caracteres no numéricos
    clean_phone = "".join(filter(str.isdigit, phone))

    # Asegurar que empiece con código de país
    if not clean_phone.startswith("52") and len(clean_phone) == 10:
        clean_phone = "52" + clean_phone

    return clean_phone


def format_whatsapp_jid(phone: str, is_group: bool = False) -> str:
    """
    Formatear JID de WhatsApp

    Args:
        phone: Número de teléfono o ID de grupo
        is_group: True si es un grupo

    Returns:
        JID formateado
    """
    if is_group:
        return f"{phone}@g.us" if "@" not in phone else phone
    else:
        clean_phone = format_phone_number(phone)
        return f"{clean_phone}@s.whatsapp.net"


def extract_error_message(error: Exception) -> str:
    """
    Extraer mensaje legible de una excepción

    Args:
        error: Excepción

    Returns:
        Mensaje de error
    """
    return str(error) or error.__class__.__name__


def dict_without_none(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Remover valores None de un diccionario

    Args:
        data: Diccionario con posibles valores None

    Returns:
        Diccionario sin valores None
    """
    return {k: v for k, v in data.items() if v is not None}


def safe_int(value: Any, default: int = 0) -> int:
    """
    Convertir valor a int de forma segura

    Args:
        value: Valor a convertir
        default: Valor por defecto si la conversión falla

    Returns:
        Valor convertido o default
    """
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


def safe_float(value: Any, default: float = 0.0) -> float:
    """
    Convertir valor a float de forma segura

    Args:
        value: Valor a convertir
        default: Valor por defecto si la conversión falla

    Returns:
        Valor convertido o default
    """
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


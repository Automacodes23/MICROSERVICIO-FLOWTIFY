"""
Parser para eventos de Wialon
"""
from typing import Dict, Any, Union
from urllib.parse import parse_qs
from app.core.logging import get_logger

logger = get_logger(__name__)


def parse_wialon_event(
    body: Union[str, bytes, Dict[str, Any]], content_type: str = "application/json"
) -> Dict[str, Any]:
    """
    Parsear evento de Wialon

    Wialon puede enviar eventos en diferentes formatos:
    - application/json
    - application/x-www-form-urlencoded
    - text/plain

    Args:
        body: Cuerpo del request
        content_type: Content-Type del request

    Returns:
        Diccionario con los datos del evento
    """
    try:
        if isinstance(body, dict):
            # Ya es un diccionario
            return body

        if isinstance(body, bytes):
            body = body.decode("utf-8")

        # JSON
        if "application/json" in content_type:
            import json

            return json.loads(body)

        # Form-urlencoded
        if "application/x-www-form-urlencoded" in content_type or "=" in body:
            parsed = parse_qs(body)
            # Convertir listas a valores simples
            result = {k: v[0] if isinstance(v, list) and len(v) == 1 else v 
                     for k, v in parsed.items()}

            # Convertir tipos numéricos
            return _convert_types(result)

        # Plain text (asumimos que es form-urlencoded sin header correcto)
        if "=" in body:
            parsed = parse_qs(body)
            result = {k: v[0] if isinstance(v, list) and len(v) == 1 else v 
                     for k, v in parsed.items()}
            return _convert_types(result)

        logger.warning("wialon_unknown_format", content_type=content_type)
        return {}

    except Exception as e:
        logger.error("wialon_parse_error", error=str(e), body=str(body)[:200])
        return {}


def _convert_types(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convertir strings a tipos apropiados

    Args:
        data: Diccionario con strings

    Returns:
        Diccionario con tipos convertidos
    """
    result = {}

    for key, value in data.items():
        if not isinstance(value, str):
            result[key] = value
            continue

        # Intentar convertir a número
        if value.replace(".", "", 1).replace("-", "", 1).isdigit():
            if "." in value:
                result[key] = float(value)
            else:
                result[key] = int(value)
        else:
            result[key] = value

    return result


def normalize_wialon_event(raw_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalizar evento de Wialon a formato estándar

    Args:
        raw_data: Datos raw del evento

    Returns:
        Evento normalizado
    """
    return {
        "unit_name": raw_data.get("unit_name", ""),
        "unit_id": str(raw_data.get("unit_id", "")),
        "imei": str(raw_data.get("imei", "")) if raw_data.get("imei") is not None else None,
        "notification_type": raw_data.get("notification_type", ""),
        "notification_id": raw_data.get("notification_id") or raw_data.get("notif_id"),
        "event_time": int(raw_data.get("event_time", 0)),
        "latitude": float(raw_data.get("latitude", 0)),
        "longitude": float(raw_data.get("longitude", 0)),
        "altitude": float(raw_data.get("altitude", 0)) if raw_data.get("altitude") else None,
        "speed": float(raw_data.get("speed", 0)) if raw_data.get("speed") is not None else None,
        "course": int(raw_data.get("course", 0)) if raw_data.get("course") else None,
        "address": raw_data.get("address"),
        "pos_time": raw_data.get("pos_time"),
        "driver_name": raw_data.get("driver_name"),
        "driver_code": str(raw_data.get("driver_code", "")) if raw_data.get("driver_code") is not None else None,
        "geofence_name": raw_data.get("geofence_name"),
        "geofence_id": str(raw_data.get("geofence_id", "")) if raw_data.get("geofence_id") is not None else None,
        "max_speed": float(raw_data.get("max_speed", 0)) if raw_data.get("max_speed") else None,
        "deviation_distance_km": float(raw_data.get("deviation_distance_km", 0)) 
            if raw_data.get("deviation_distance_km") else None,
        "last_message_time": raw_data.get("last_message_time"),
    }


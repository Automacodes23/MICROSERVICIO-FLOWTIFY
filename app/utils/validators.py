"""
Validadores personalizados
"""
import re
from typing import Optional


def validate_phone_number(phone: str) -> bool:
    """
    Validar número de teléfono mexicano

    Args:
        phone: Número de teléfono

    Returns:
        True si es válido, False en caso contrario
    """
    # Remover caracteres no numéricos
    clean_phone = "".join(filter(str.isdigit, phone))

    # Debe tener 10 dígitos (sin código de país) o 12 (con código 52)
    if len(clean_phone) not in [10, 12]:
        return False

    # Si tiene 12, debe empezar con 52
    if len(clean_phone) == 12 and not clean_phone.startswith("52"):
        return False

    return True


def validate_trip_code(code: str) -> bool:
    """
    Validar formato de código de viaje

    Args:
        code: Código del viaje

    Returns:
        True si es válido, False en caso contrario
    """
    if not code or len(code) < 3:
        return False

    # Permitir letras, números, guiones
    pattern = r"^[A-Za-z0-9\-]+$"
    return bool(re.match(pattern, code))


def validate_coordinates(latitude: float, longitude: float) -> bool:
    """
    Validar coordenadas GPS

    Args:
        latitude: Latitud
        longitude: Longitud

    Returns:
        True si son válidas, False en caso contrario
    """
    # Validar rangos
    if not (-90 <= latitude <= 90):
        return False

    if not (-180 <= longitude <= 180):
        return False

    return True


def validate_imei(imei: str) -> bool:
    """
    Validar formato de IMEI

    Args:
        imei: IMEI del dispositivo

    Returns:
        True si es válido, False en caso contrario
    """
    # IMEI debe ser 15 dígitos
    if not imei or not imei.isdigit():
        return False

    return len(imei) == 15


def sanitize_string(text: str, max_length: Optional[int] = None) -> str:
    """
    Sanitizar string para prevenir inyecciones

    Args:
        text: Texto a sanitizar
        max_length: Longitud máxima opcional

    Returns:
        Texto sanitizado
    """
    # Remover caracteres de control
    sanitized = "".join(char for char in text if char.isprintable())

    # Truncar si es necesario
    if max_length and len(sanitized) > max_length:
        sanitized = sanitized[:max_length]

    return sanitized.strip()


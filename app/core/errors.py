"""
Excepciones personalizadas del sistema
"""
from typing import Any, Dict, Optional


class BaseServiceError(Exception):
    """Base exception para todos los errores del servicio"""

    def __init__(
        self,
        message: str,
        code: str = "SERVICE_ERROR",
        status_code: int = 500,
        context: Optional[Dict[str, Any]] = None,
    ):
        self.message = message
        self.code = code
        self.status_code = status_code
        self.context = context or {}
        super().__init__(self.message)


# Database Errors
class DatabaseError(BaseServiceError):
    """Error de base de datos"""

    def __init__(self, message: str, context: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message, code="DATABASE_ERROR", status_code=500, context=context
        )


class RecordNotFoundError(BaseServiceError):
    """Registro no encontrado"""

    def __init__(self, resource: str, identifier: Any):
        super().__init__(
            message=f"{resource} no encontrado: {identifier}",
            code="RECORD_NOT_FOUND",
            status_code=404,
            context={"resource": resource, "identifier": identifier},
        )


# Trip Errors
class TripNotFoundError(RecordNotFoundError):
    """Viaje no encontrado"""

    def __init__(self, trip_id: Any):
        super().__init__(resource="Trip", identifier=trip_id)


class TripAlreadyExistsError(BaseServiceError):
    """Viaje ya existe"""

    def __init__(self, trip_code: str):
        super().__init__(
            message=f"Viaje ya existe: {trip_code}",
            code="TRIP_ALREADY_EXISTS",
            status_code=409,
            context={"trip_code": trip_code},
        )


class InvalidTripStateError(BaseServiceError):
    """Estado de viaje inválido"""

    def __init__(self, current_state: str, attempted_state: str):
        super().__init__(
            message=f"Transición de estado inválida: {current_state} -> {attempted_state}",
            code="INVALID_TRIP_STATE",
            status_code=400,
            context={
                "current_state": current_state,
                "attempted_state": attempted_state,
            },
        )


# External API Errors
class ExternalAPIError(BaseServiceError):
    """Error en API externa"""

    def __init__(
        self, service: str, message: str, context: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=f"Error en {service}: {message}",
            code="EXTERNAL_API_ERROR",
            status_code=502,
            context={"service": service, **(context or {})},
        )


class EvolutionAPIError(ExternalAPIError):
    """Error en Evolution API"""

    def __init__(self, message: str, context: Optional[Dict[str, Any]] = None):
        super().__init__(service="Evolution API", message=message, context=context)


class GeminiAPIError(ExternalAPIError):
    """Error en Gemini API"""

    def __init__(self, message: str, context: Optional[Dict[str, Any]] = None):
        super().__init__(service="Gemini API", message=message, context=context)


class FloatifyAPIError(ExternalAPIError):
    """Error en Floatify API"""

    def __init__(self, message: str, context: Optional[Dict[str, Any]] = None):
        super().__init__(service="Floatify API", message=message, context=context)


# Validation Errors
class ValidationError(BaseServiceError):
    """Error de validación"""

    def __init__(self, message: str, field: Optional[str] = None):
        super().__init__(
            message=message,
            code="VALIDATION_ERROR",
            status_code=400,
            context={"field": field} if field else {},
        )


# Configuration Errors
class ConfigurationError(BaseServiceError):
    """Error de configuración"""

    def __init__(self, message: str):
        super().__init__(
            message=message, code="CONFIGURATION_ERROR", status_code=500
        )


# Business Logic Errors
class BusinessLogicError(BaseServiceError):
    """Error de lógica de negocio"""

    def __init__(self, message: str, context: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            code="BUSINESS_LOGIC_ERROR",
            status_code=400,
            context=context,
        )


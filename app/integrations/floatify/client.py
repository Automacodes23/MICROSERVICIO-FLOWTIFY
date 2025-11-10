"""
Cliente para callbacks a Floatify
"""
import httpx
from typing import Dict, Any, Optional
from app.core.logging import get_logger
from app.core.errors import FloatifyAPIError

logger = get_logger(__name__)


class FloatifyClient:
    """Cliente para enviar callbacks a Floatify"""

    def __init__(
        self,
        api_url: Optional[str] = None,
        api_key: Optional[str] = None,
        timeout: int = 30,
    ):
        """
        Inicializar cliente de Floatify

        Args:
            api_url: URL base de la API de Floatify
            api_key: API key para autenticación
            timeout: Timeout para las peticiones (segundos)
        """
        self.api_url = api_url.rstrip("/") if api_url else None
        self.api_key = api_key
        self.timeout = timeout
        self.headers = {"Content-Type": "application/json"}

        if self.api_key:
            self.headers["Authorization"] = f"Bearer {self.api_key}"

    async def notify_trip_completed(
        self, trip_data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Notificar a Floatify que un viaje se completó

        Args:
            trip_data: Datos del viaje completado

        Returns:
            Respuesta de Floatify o None si no está configurado
        """
        if not self.api_url:
            logger.warning("floatify_not_configured", event="trip_completed")
            return None

        try:
            url = f"{self.api_url}/webhooks/trip-completed"

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(url, json=trip_data, headers=self.headers)
                response.raise_for_status()

                logger.info(
                    "floatify_notified",
                    event="trip_completed",
                    trip_id=trip_data.get("trip_id"),
                )

                return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(
                "floatify_api_error",
                error=str(e),
                status_code=e.response.status_code,
            )
            raise FloatifyAPIError(
                f"Error al notificar a Floatify: {e.response.status_code}"
            )
        except Exception as e:
            logger.error("floatify_api_error", error=str(e))
            raise FloatifyAPIError(f"Error al notificar a Floatify: {str(e)}")

    async def notify_event(
        self, event_type: str, event_data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Notificar un evento genérico a Floatify

        Args:
            event_type: Tipo de evento
            event_data: Datos del evento

        Returns:
            Respuesta de Floatify o None si no está configurado
        """
        if not self.api_url:
            logger.warning("floatify_not_configured", event=event_type)
            return None

        try:
            url = f"{self.api_url}/webhooks/events"
            payload = {"event_type": event_type, "data": event_data}

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(url, json=payload, headers=self.headers)
                response.raise_for_status()

                logger.info("floatify_notified", event=event_type)
                return response.json()

        except Exception as e:
            logger.error("floatify_api_error", error=str(e), event=event_type)
            # No lanzamos excepción para no afectar el flujo principal
            return None


"""
Servicio para procesamiento de eventos de Wialon
"""
from typing import Dict, Any, Optional
import uuid
from app.core.logging import get_logger, log_context
from app.core.errors import BusinessLogicError
from app.core.database import Database
from app.core.constants import WIALON_EVENT_TYPES
from app.repositories.event_repository import EventRepository
from app.repositories.trip_repository import TripRepository
from app.repositories.unit_repository import UnitRepository
from app.models.event import WialonEvent
from app.integrations.evolution.client import EvolutionClient

logger = get_logger(__name__)


class EventService:
    """Servicio para procesar eventos de Wialon"""

    def __init__(self, db: Database, evolution_client: Optional[EvolutionClient] = None):
        self.db = db
        self.event_repo = EventRepository(db)
        self.trip_repo = TripRepository(db)
        self.unit_repo = UnitRepository(db)
        self.evolution_client = evolution_client

    async def process_wialon_event(
        self, event: WialonEvent
    ) -> Dict[str, Any]:
        """
        Procesar evento de Wialon

        Args:
            event: Evento de Wialon

        Returns:
            Resultado del procesamiento
        """
        trace_id = str(uuid.uuid4())
        log_context(
            trace_id=trace_id,
            event_type=event.notification_type,
            unit_id=event.unit_id,
        )

        try:
            logger.info("wialon_event_received", event_data=event.model_dump())

            # 1. Buscar viaje activo por wialon_id de la unidad
            trip = await self.trip_repo.find_active_by_wialon_id(event.unit_id)

            if not trip:
                logger.warning(
                    "no_active_trip_for_event",
                    unit_id=event.unit_id,
                    unit_name=event.unit_name,
                )
                return {
                    "success": True,
                    "message": "No active trip found for unit",
                    "event_saved": False,
                }

            # 2. Obtener unit_id de la base de datos
            unit = await self.unit_repo.find_by_wialon_id(event.unit_id)
            if not unit:
                logger.error("unit_not_found", wialon_id=event.unit_id)
                raise BusinessLogicError(f"Unit not found: {event.unit_id}")

            # 3. Buscar geofence_id en BD si viene del evento (para foreign key)
            geofence_db_id = None
            if event.geofence_id:
                # Buscar la geocerca por floatify_geofence_id (usando fetchval para obtener valor directo)
                geofence_db_id = await self.db.fetchval(
                    "SELECT id FROM geofences WHERE floatify_geofence_id = %s OR wialon_geofence_id = %s",
                    event.geofence_id,
                    event.geofence_id
                )
                if geofence_db_id:
                    logger.info("geofence_found_for_event", floatify_id=event.geofence_id, db_id=geofence_db_id)
                else:
                    logger.warning("geofence_not_found_for_event", floatify_id=event.geofence_id)
            
            # 4. Registrar evento (con idempotencia usando wialon_notification_id)
            event_data = {
                "wialon_notification_id": event.notification_id,
                "trip_id": trip["id"],
                "unit_id": unit["id"],
                "event_type": event.notification_type,
                "event_time": event.event_time,
                "latitude": event.latitude,
                "longitude": event.longitude,
                "geofence_id": geofence_db_id,  # Usar ID de BD o None
                "raw_payload": event.model_dump(),
            }

            created_event = await self.event_repo.create_event(event_data)

            if not created_event:
                # Evento duplicado (idempotencia) - recuperar el evento existente para devolver sus IDs
                logger.info(
                    "event_already_processed_idempotency",
                    wialon_notification_id=event.notification_id,
                    event_type=event.notification_type
                )
                existing_event = await self.event_repo.find_by_wialon_notification_id(event.notification_id)
                
                return {
                    "success": True,
                    "message": "Event already processed (idempotent)",
                    "event_saved": False,
                    "idempotent": True,
                    "event_id": existing_event["id"] if existing_event else None,
                    "trip_id": existing_event.get("trip_id") if existing_event else trip["id"],
                }

            logger.info("event_saved", event_id=created_event["id"])

            # 5. Determinar acción según tipo de evento
            action_result = await self._determine_action(event, trip)
            logger.info("action_determined", action=action_result, event_type=event.notification_type)

            # 6. Actualizar estado del viaje si es necesario
            if action_result.get("update_status"):
                await self.trip_repo.update_status(
                    trip["id"],
                    action_result["new_status"],
                    action_result["new_substatus"],
                )
                logger.info(
                    "trip_status_updated_by_event",
                    trip_id=trip["id"],
                    new_status=action_result["new_status"],
                    new_substatus=action_result["new_substatus"],
                )

            # 7. Enviar notificación WhatsApp si es necesario
            if action_result.get("send_notification") and self.evolution_client:
                whatsapp_group_id = trip.get("whatsapp_group_id")
                notification_message = action_result.get("notification_message")
                
                if whatsapp_group_id and notification_message:
                    try:
                        logger.info(
                            "sending_event_notification",
                            trip_id=trip["id"],
                            group_id=whatsapp_group_id,
                            event_type=event.notification_type
                        )
                        await self.evolution_client.send_text(
                            whatsapp_group_id,
                            notification_message
                        )
                        logger.info(
                            "event_notification_sent",
                            trip_id=trip["id"],
                            group_id=whatsapp_group_id,
                            event_type=event.notification_type
                        )
                    except Exception as e:
                        logger.error(
                            "event_notification_failed",
                            error=str(e),
                            trip_id=trip["id"],
                            group_id=whatsapp_group_id
                        )
                        # No fallar el proceso si solo falla el WhatsApp
                else:
                    logger.warning(
                        "event_notification_skipped_no_group",
                        trip_id=trip["id"],
                        has_group_id=bool(whatsapp_group_id),
                        has_message=bool(notification_message)
                    )

            # 8. Marcar evento como procesado
            await self.event_repo.mark_as_processed(created_event["id"])

            return {
                "success": True,
                "event_id": created_event["id"],
                "trip_id": trip["id"],
                "action": action_result,
                "message": "Event processed successfully",
            }

        except Exception as e:
            logger.error("event_processing_failed", error=str(e))
            raise BusinessLogicError(f"Error procesando evento: {str(e)}")

    async def _determine_action(
        self, event: WialonEvent, trip: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Determinar acción a tomar según el tipo de evento

        Args:
            event: Evento de Wialon
            trip: Viaje actual

        Returns:
            Diccionario con la acción a realizar
        """
        current_status = trip["status"]
        current_substatus = trip["substatus"]

        action = {
            "update_status": False,
            "send_notification": False,
            "notification_message": None,
            "new_status": current_status,
            "new_substatus": current_substatus,
        }

        # Entrada a geocerca
        if event.notification_type == WIALON_EVENT_TYPES["GEOFENCE_ENTRY"]:
            # Primero intentar determinar el rol desde la BD (más confiable)
            geofence_role = None
            if event.geofence_id:
                try:
                    geofence_role = await self.db.fetchval(
                        """
                        SELECT tg.visit_type 
                        FROM trip_geofences tg
                        JOIN geofences g ON g.id = tg.geofence_id
                        WHERE tg.trip_id = %s 
                          AND (g.floatify_geofence_id = %s OR g.wialon_geofence_id = %s)
                        LIMIT 1
                        """,
                        trip["id"],
                        event.geofence_id,
                        event.geofence_id
                    )
                    logger.info(
                        "geofence_role_detected",
                        geofence_id=event.geofence_id,
                        geofence_name=event.geofence_name,
                        role=geofence_role,
                        trip_id=trip["id"]
                    )
                except Exception as e:
                    logger.warning("geofence_role_lookup_failed", error=str(e), geofence_id=event.geofence_id)
            
            # Si encontramos el rol en BD, usarlo
            if geofence_role == "loading":
                action["update_status"] = True
                action["new_status"] = "en_zona_carga"
                action["new_substatus"] = "esperando_inicio_carga"
                action["send_notification"] = True
                action["notification_message"] = (
                    f"[CARGA] Llegaste a {event.geofence_name}. "
                    "Ya iniciaste la carga?"
                )
            
            elif geofence_role == "unloading":
                action["update_status"] = True
                action["new_status"] = "en_zona_descarga"
                action["new_substatus"] = "esperando_inicio_descarga"
                action["send_notification"] = True
                action["notification_message"] = (
                    f"[DESCARGA] Llegaste a {event.geofence_name}. "
                    "Confirma cuando inicies la descarga."
                )
            
            # Fallback: si no hay rol en BD, usar detección por nombre (compatibilidad con geocercas no asociadas)
            elif not geofence_role:
                geofence_name_lower = (event.geofence_name or "").lower()
                
                if "carga" in geofence_name_lower or "loading" in geofence_name_lower:
                    action["update_status"] = True
                    action["new_status"] = "en_zona_carga"
                    action["new_substatus"] = "esperando_inicio_carga"
                    action["send_notification"] = True
                    action["notification_message"] = (
                        f"[CARGA] Llegaste a {event.geofence_name}. "
                        "Ya iniciaste la carga?"
                    )
                    logger.info("geofence_detected_by_name_fallback", type="loading", geofence_name=event.geofence_name)
                
                elif "descarga" in geofence_name_lower or "unload" in geofence_name_lower:
                    action["update_status"] = True
                    action["new_status"] = "en_zona_descarga"
                    action["new_substatus"] = "esperando_inicio_descarga"
                    action["send_notification"] = True
                    action["notification_message"] = (
                        f"[DESCARGA] Llegaste a {event.geofence_name}. "
                        "Confirma cuando inicies la descarga."
                    )
                    logger.info("geofence_detected_by_name_fallback", type="unloading", geofence_name=event.geofence_name)

        # Salida de geocerca
        elif event.notification_type == WIALON_EVENT_TYPES["GEOFENCE_EXIT"]:
            geofence_name_lower = (event.geofence_name or "").lower()

            if "carga" in geofence_name_lower:
                action["update_status"] = True
                action["new_status"] = "en_ruta_destino"
                action["new_substatus"] = "rumbo_a_descarga"

        # Exceso de velocidad
        elif event.notification_type == WIALON_EVENT_TYPES["SPEED_VIOLATION"]:
            action["send_notification"] = True
            action["notification_message"] = (
                f"⚠️ Exceso de velocidad detectado: {event.speed}km/h "
                f"(límite: {event.max_speed}km/h). Por favor reduce la velocidad."
            )

        # Botón de pánico
        elif event.notification_type == WIALON_EVENT_TYPES["PANIC_BUTTON"]:
            action["send_notification"] = True
            action["notification_message"] = (
                f"🚨 ALERTA: Botón de pánico activado en {event.unit_name}. "
                f"Ubicación: {event.address}"
            )

        # Pérdida de conexión
        elif event.notification_type == WIALON_EVENT_TYPES["CONNECTION_LOST"]:
            action["send_notification"] = True
            action["notification_message"] = (
                f"📡 Pérdida de conexión en {event.unit_name}. "
                f"Última ubicación: {event.address}"
            )

        # Desviación de ruta
        elif event.notification_type == WIALON_EVENT_TYPES["ROUTE_DEVIATION"]:
            action["send_notification"] = True
            action["notification_message"] = (
                f"🗺️ Desviación de ruta detectada: {event.deviation_distance_km}km "
                f"de distancia de la ruta planificada."
            )

        return action

    async def get_trip_events(
        self, trip_id: str, limit: int = 100, offset: int = 0
    ) -> list:
        """Obtener eventos de un viaje"""
        return await self.event_repo.find_by_trip(trip_id, limit, offset)


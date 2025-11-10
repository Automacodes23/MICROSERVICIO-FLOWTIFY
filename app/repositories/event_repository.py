"""
Repository para eventos de Wialon
"""
from typing import Optional, Dict, Any, List
import json
import uuid
from app.repositories.base import BaseRepository
from app.core.database import Database
from app.core.logging import get_logger

logger = get_logger(__name__)


class EventRepository(BaseRepository):
    """Repository para gestionar eventos"""

    def __init__(self, db: Database):
        super().__init__(db, "events")

    async def find_by_wialon_notification_id(
        self, wialon_notification_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Buscar evento por wialon_notification_id para idempotencia
        
        Args:
            wialon_notification_id: ID único de notificación de Wialon
            
        Returns:
            Evento si existe, None en caso contrario
        """
        query = "SELECT * FROM events WHERE wialon_notification_id = %s"
        row = await self.db.fetchrow(query, wialon_notification_id)
        return row

    async def find_by_trip(
        self, trip_id: str, limit: int = 100, offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Buscar eventos por viaje"""
        query = """
            SELECT * FROM events
            WHERE trip_id = %s
            ORDER BY created_at DESC
            LIMIT %s OFFSET %s
        """
        rows = await self.db.fetch(query, trip_id, limit, offset)
        return rows or []

    async def find_unprocessed(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Buscar eventos no procesados"""
        query = """
            SELECT * FROM events
            WHERE processed = FALSE
            ORDER BY created_at ASC
            LIMIT %s
        """
        rows = await self.db.fetch(query, limit)
        return rows or []

    async def create_event(self, event_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Crear un evento con idempotencia usando wialon_notification_id
        
        Args:
            event_data: Datos del evento
            
        Returns:
            Evento creado o None si ya existía (idempotencia)
        """
        wialon_notification_id = event_data.get("wialon_notification_id")
        
        # Si no hay wialon_notification_id, generar uno único
        if not wialon_notification_id:
            event_type = event_data.get("event_type", "unknown")
            event_time = event_data.get("event_time", "")
            unit_id = event_data.get("unit_id", "")
            wialon_notification_id = f"{event_type}_{event_time}_{unit_id}_{uuid.uuid4().hex[:8]}"
            logger.warning(
                "wialon_notification_id_not_provided",
                generated_id=wialon_notification_id
            )
        
        # Verificar si ya existe (idempotencia)
        existing = await self.find_by_wialon_notification_id(wialon_notification_id)
        if existing:
            logger.info(
                "event_already_exists_idempotency",
                wialon_notification_id=wialon_notification_id,
                event_id=existing["id"]
            )
            return None  # Ya existe, no crear duplicado
        
        # Serializar raw_payload a JSON string
        raw_payload = event_data.get("raw_payload", {})
        raw_payload_json = json.dumps(raw_payload) if isinstance(raw_payload, dict) else raw_payload
        
        # Insertar nuevo evento (usando la MISMA conexión para INSERT y SELECT)
        query = """
            INSERT INTO events (
                id, event_type, unit_id, trip_id, geofence_id,
                latitude, longitude, event_time, wialon_notification_id,
                raw_payload, processed
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, FALSE)
        """
        
        event_id = str(uuid.uuid4())
        
        try:
            # Usar la misma conexión para INSERT y SELECT (fix transacción)
            async with self.db.acquire() as (cursor, conn):
                await cursor.execute(
                    query,
                    (
                        event_id,
                        event_data.get("event_type"),
                        event_data.get("unit_id"),
                        event_data.get("trip_id"),
                        event_data.get("geofence_id"),
                        event_data.get("latitude"),
                        event_data.get("longitude"),
                        event_data.get("event_time"),
                        wialon_notification_id,
                        raw_payload_json,
                    )
                )
                await conn.commit()
                
                # Recuperar el evento recién creado (misma conexión)
                await cursor.execute("SELECT * FROM events WHERE id = %s", (event_id,))
                result = await cursor.fetchone()
                created_event = self.db._deserialize_json_fields(result) if result else None
                
                logger.info("event_created", event_id=event_id, wialon_notification_id=wialon_notification_id)
                
                if not created_event:
                    logger.error("event_creation_failed_fetch", event_id=event_id)
                    raise Exception(f"Failed to retrieve created event: {event_id}")
                
                return created_event
            
        except Exception as e:
            # Si falla por UNIQUE constraint, es porque ya existe
            if "Duplicate entry" in str(e) or "unique" in str(e).lower():
                logger.info(
                    "event_duplicate_detected",
                    wialon_notification_id=wialon_notification_id
                )
                return None
            # Si es otro error, propagarlo
            logger.error("event_creation_failed", error=str(e))
            raise

    async def mark_as_processed(self, event_id: str) -> bool:
        """Marcar evento como procesado"""
        query = """
            UPDATE events
            SET processed = TRUE
            WHERE id = %s
        """
        result = await self.db.execute(query, event_id)
        return result > 0

    async def find_by_type(
        self, event_type: str, limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Buscar eventos por tipo"""
        query = """
            SELECT * FROM events
            WHERE event_type = %s
            ORDER BY created_at DESC
            LIMIT %s
        """
        rows = await self.db.fetch(query, event_type, limit)
        return rows or []


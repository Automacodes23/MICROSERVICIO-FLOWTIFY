"""
Repository para viajes
"""
from typing import Optional, Dict, Any, List
import json
from app.repositories.base import BaseRepository
from app.core.database import Database


class TripRepository(BaseRepository):
    """Repository para gestionar viajes"""

    def __init__(self, db: Database):
        super().__init__(db, "trips")

    async def find_by_floatify_id(self, floatify_trip_id: str) -> Optional[Dict[str, Any]]:
        """Buscar viaje por floatify_trip_id"""
        query = "SELECT * FROM trips WHERE floatify_trip_id = %s"
        row = await self.db.fetchrow(query, floatify_trip_id)
        return dict(row) if row else None

    async def find_by_id(self, trip_id: str) -> Optional[Dict[str, Any]]:
        """Buscar viaje por ID"""
        query = "SELECT * FROM trips WHERE id = %s"
        row = await self.db.fetchrow(query, trip_id)
        return dict(row) if row else None

    async def find_active_by_unit(self, unit_id: str) -> Optional[Dict[str, Any]]:
        """Buscar viaje activo por unidad"""
        query = """
            SELECT * FROM trips
            WHERE unit_id = %s
              AND status NOT IN ('completed', 'cancelled')
            ORDER BY created_at DESC
            LIMIT 1
        """
        row = await self.db.fetchrow(query, unit_id)
        return dict(row) if row else None

    async def find_active_by_wialon_id(
        self, wialon_unit_id: str
    ) -> Optional[Dict[str, Any]]:
        """Buscar viaje activo por wialon_id de la unidad"""
        query = """
            SELECT t.* FROM trips t
            JOIN units u ON t.unit_id = u.id
            WHERE u.wialon_unit_id = %s
              AND t.status NOT IN ('completed', 'cancelled')
            ORDER BY t.created_at DESC
            LIMIT 1
        """
        row = await self.db.fetchrow(query, wialon_unit_id)
        return dict(row) if row else None

    async def find_by_status(
        self, status: str, limit: int = 100, offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Buscar viajes por estado"""
        query = """
            SELECT * FROM trips
            WHERE status = %s
            ORDER BY created_at DESC
            LIMIT %s OFFSET %s
        """
        rows = await self.db.fetch(query, status, limit, offset)
        return [dict(row) for row in rows]

    async def update_status(
        self, trip_id: str, status: str, substatus: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Actualizar estado y subestado de un viaje"""
        query = """
            UPDATE trips
            SET status = %s, substatus = %s, updated_at = NOW()
            WHERE id = %s
        """
        await self.db.execute(query, status, substatus, trip_id)
        
        # MySQL no soporta RETURNING, así que hacemos un SELECT
        return await self.find_by_id(trip_id)

    async def complete_trip(
        self, trip_id: str, status: str = 'completed', substatus: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Completar un viaje"""
        query = """
            UPDATE trips
            SET status = %s, substatus = %s, trip_ended_at = NOW(), updated_at = NOW()
            WHERE id = %s
        """
        await self.db.execute(query, status, substatus, trip_id)
        
        # MySQL no soporta RETURNING, así que hacemos un SELECT
        return await self.find_by_id(trip_id)

    async def create_full_trip(self, trip_data: Dict[str, Any]) -> Dict[str, Any]:
        """Crear un viaje con todos sus datos"""
        # Extraer datos y guardar campos adicionales en metadata
        floatify_trip_id = trip_data.get("floatify_trip_id") or trip_data.get("code")
        unit_id = trip_data.get("unit_id")
        driver_id = trip_data.get("driver_id")
        status = trip_data.get("status", "pending")
        cargo_description = trip_data.get("cargo_description") or trip_data.get("metadata", {}).get("cargo_description")
        whatsapp_group_id = trip_data.get("whatsapp_group_id")
        whatsapp_group_name = trip_data.get("whatsapp_group_name")
        
        # Guardar campos adicionales en metadata
        metadata = trip_data.get("metadata", {})
        if "origin" in trip_data:
            metadata["origin"] = trip_data["origin"]
        if "destination" in trip_data:
            metadata["destination"] = trip_data["destination"]
        if "tenant_id" in trip_data:
            metadata["tenant_id"] = trip_data["tenant_id"]
        if "planned_start" in trip_data:
            metadata["planned_start"] = trip_data["planned_start"]
        if "planned_end" in trip_data:
            metadata["planned_end"] = trip_data["planned_end"]
        
        # Usar la misma conexión para INSERT y SELECT
        async with self.db.acquire() as (cursor, conn):
            insert_query = """
                INSERT INTO trips (
                    floatify_trip_id, unit_id, driver_id, status, 
                    cargo_description, whatsapp_group_id, whatsapp_group_name, metadata
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """
            
            await cursor.execute(
                insert_query,
                (floatify_trip_id, unit_id, driver_id, status, cargo_description, whatsapp_group_id, whatsapp_group_name, json.dumps(metadata))
            )
            await conn.commit()
            
            # Hacer SELECT en la misma conexión
            select_query = "SELECT * FROM trips WHERE floatify_trip_id = %s"
            await cursor.execute(select_query, (floatify_trip_id,))
            row = await cursor.fetchone()
            
            return dict(row) if row else None

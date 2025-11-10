"""
Repository para conductores
"""
from typing import Optional, Dict, Any
import json
from app.repositories.base import BaseRepository
from app.core.database import Database


class DriverRepository(BaseRepository):
    """Repository para gestionar conductores"""

    def __init__(self, db: Database):
        super().__init__(db, "drivers")

    async def find_by_phone(self, phone: str) -> Optional[Dict[str, Any]]:
        """Buscar conductor por teléfono"""
        query = "SELECT * FROM drivers WHERE phone = %s"
        row = await self.db.fetchrow(query, phone)
        return dict(row) if row else None

    async def find_by_wialon_code(
        self, wialon_driver_code: str
    ) -> Optional[Dict[str, Any]]:
        """Buscar conductor por código de Wialon"""
        query = "SELECT * FROM drivers WHERE wialon_driver_code = %s"
        row = await self.db.fetchrow(query, wialon_driver_code)
        return dict(row) if row else None

    async def upsert(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Crear o actualizar un conductor por teléfono"""
        from app.core.logging import get_logger
        logger = get_logger(__name__)
        
        name = data.get("name")
        phone = data.get("phone")
        wialon_driver_code = data.get("wialon_driver_code") or data.get("wialon_code")
        metadata = data.get("metadata", {})
        
        logger.info("driver_upsert_attempt", name=name, phone=phone, wialon_code=wialon_driver_code)
        
        # MySQL usa ON DUPLICATE KEY UPDATE en lugar de ON CONFLICT
        # Usar la misma conexión para INSERT y SELECT
        async with self.db.acquire() as (cursor, conn):
            insert_query = """
                INSERT INTO drivers (name, phone, wialon_driver_code, metadata)
                VALUES (%s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    name = VALUES(name),
                    wialon_driver_code = VALUES(wialon_driver_code),
                    metadata = VALUES(metadata),
                    updated_at = NOW()
            """
            
            try:
                # Ejecutar INSERT
                await cursor.execute(insert_query, (name, phone, wialon_driver_code, json.dumps(metadata)))
                await conn.commit()
                logger.info("driver_insert_success", phone=phone)
            except Exception as e:
                logger.error("driver_insert_failed", error=str(e), phone=phone)
                raise
            
            # Hacer SELECT en la misma conexión
            select_query = "SELECT * FROM drivers WHERE phone = %s"
            await cursor.execute(select_query, (phone,))
            row = await cursor.fetchone()
            
            if row:
                logger.info("driver_find_result", found=True, phone=phone)
                return dict(row)
            else:
                logger.warning("driver_find_result", found=False, phone=phone)
                return None

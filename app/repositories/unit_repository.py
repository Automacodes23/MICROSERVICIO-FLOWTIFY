"""
Repository para unidades de transporte
"""
from typing import Optional, Dict, Any
import json
from app.repositories.base import BaseRepository
from app.core.database import Database
from app.core.logging import get_logger

logger = get_logger(__name__)


class UnitRepository(BaseRepository):
    """Repository para gestionar unidades"""

    def __init__(self, db: Database):
        super().__init__(db, "units")

    async def find_by_floatify_id(self, floatify_unit_id: str) -> Optional[Dict[str, Any]]:
        """Buscar unidad por floatify_unit_id"""
        query = "SELECT * FROM units WHERE floatify_unit_id = %s"
        row = await self.db.fetchrow(query, floatify_unit_id)
        return dict(row) if row else None

    async def find_by_wialon_id(self, wialon_unit_id: str) -> Optional[Dict[str, Any]]:
        """Buscar unidad por ID de Wialon"""
        query = "SELECT * FROM units WHERE wialon_unit_id = %s"
        row = await self.db.fetchrow(query, wialon_unit_id)
        return dict(row) if row else None

    async def upsert(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Crear o actualizar una unidad por floatify_unit_id"""
        # Extraer campos del metadata si existen
        floatify_unit_id = data.get("floatify_unit_id") or data.get("metadata", {}).get("floatify_unit_id")
        wialon_unit_id = data.get("wialon_id") or data.get("wialon_unit_id")
        name = data.get("code") or data.get("name")
        plate = data.get("plate")
        metadata = data.get("metadata", {})
        
        # MySQL usa ON DUPLICATE KEY UPDATE en lugar de ON CONFLICT
        # Usar la misma conexión para INSERT y SELECT
        async with self.db.acquire() as (cursor, conn):
            insert_query = """
                INSERT INTO units (floatify_unit_id, wialon_unit_id, name, plate, metadata)
                VALUES (%s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    wialon_unit_id = VALUES(wialon_unit_id),
                    name = VALUES(name),
                    plate = VALUES(plate),
                    metadata = VALUES(metadata),
                    updated_at = NOW()
            """
            
            # Ejecutar INSERT
            await cursor.execute(insert_query, (floatify_unit_id, wialon_unit_id, name, plate, json.dumps(metadata)))
            await conn.commit()
            
            # Hacer SELECT en la misma conexión
            select_query = "SELECT * FROM units WHERE floatify_unit_id = %s"
            await cursor.execute(select_query, (floatify_unit_id,))
            row = await cursor.fetchone()
            
            return dict(row) if row else None

    async def find_by_id(self, unit_id: str) -> Optional[Dict[str, Any]]:
        """Buscar unidad por ID (UUID)"""
        query = "SELECT * FROM units WHERE id = %s"
        row = await self.db.fetchrow(query, unit_id)
        return dict(row) if row else None

    async def update(self, unit_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Actualizar campos de una unidad existente
        
        Args:
            unit_id: ID de la unidad (UUID)
            data: Diccionario con los campos a actualizar
                  Campos permitidos:
                  - whatsapp_group_id: str
                  - whatsapp_group_name: str
                  - name: str
                  - plate: str
                  - wialon_unit_id: str
                  - metadata: dict
        
        Returns:
            Diccionario con los datos actualizados de la unidad
        """
        # Lista de campos permitidos para actualización
        allowed_fields = [
            'whatsapp_group_id',
            'whatsapp_group_name',
            'name',
            'plate',
            'wialon_unit_id',
            'metadata'
        ]
        
        # Construir query dinámicamente basado en los campos a actualizar
        set_clauses = []
        values = []
        
        for key, value in data.items():
            if key in allowed_fields:
                set_clauses.append(f"{key} = %s")
                
                # Serializar metadata a JSON si es un diccionario
                if key == 'metadata' and isinstance(value, dict):
                    values.append(json.dumps(value))
                else:
                    values.append(value)
        
        if not set_clauses:
            # No hay nada que actualizar, devolver el registro actual
            logger.info(
                "unit_update_skipped_no_fields",
                unit_id=unit_id,
                provided_fields=list(data.keys())
            )
            return await self.find_by_id(unit_id)
        
        # Agregar updated_at automáticamente
        set_clauses.append("updated_at = NOW()")
        
        # Agregar unit_id al final para la cláusula WHERE
        values.append(unit_id)
        
        # Construir y ejecutar query
        query = f"""
            UPDATE units
            SET {', '.join(set_clauses)}
            WHERE id = %s
        """
        
        try:
            await self.db.execute(query, *values)
            logger.info(
                "unit_updated_successfully",
                unit_id=unit_id,
                updated_fields=list(data.keys())
            )
        except Exception as e:
            logger.error(
                "unit_update_failed",
                unit_id=unit_id,
                error=str(e)
            )
            raise
        
        # Devolver el registro actualizado
        return await self.find_by_id(unit_id)

    async def clear_whatsapp_group(self, unit_id: str) -> Dict[str, Any]:
        """
        Limpiar el grupo de WhatsApp de una unidad
        
        Útil cuando se quiere forzar la creación de un nuevo grupo
        en el siguiente viaje.
        """
        return await self.update(
            unit_id,
            {
                "whatsapp_group_id": None,
                "whatsapp_group_name": None
            }
        )

    async def find_by_whatsapp_group_id(self, whatsapp_group_id: str) -> Optional[Dict[str, Any]]:
        """
        Buscar unidad por ID de grupo de WhatsApp
        
        Útil para encontrar la unidad asociada a un mensaje cuando
        no existe registro en la tabla conversations.
        """
        query = "SELECT * FROM units WHERE whatsapp_group_id = %s"
        row = await self.db.fetchrow(query, whatsapp_group_id)
        return dict(row) if row else None

    async def get_units_with_active_groups(self) -> list[Dict[str, Any]]:
        """Obtener todas las unidades que tienen grupos de WhatsApp activos"""
        query = """
            SELECT * FROM units
            WHERE whatsapp_group_id IS NOT NULL
            ORDER BY updated_at DESC
        """
        rows = await self.db.fetch(query)
        return [dict(row) for row in rows]

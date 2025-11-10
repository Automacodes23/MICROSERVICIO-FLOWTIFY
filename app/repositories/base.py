"""
Repository base con operaciones CRUD comunes
"""
from typing import Generic, TypeVar, Optional, List, Dict, Any
from app.core.database import Database

T = TypeVar("T")


class BaseRepository(Generic[T]):
    """Repository base con operaciones CRUD"""

    def __init__(self, db: Database, table_name: str):
        self.db = db
        self.table_name = table_name

    async def find_by_id(self, id: int) -> Optional[Dict[str, Any]]:
        """Buscar por ID"""
        query = f"SELECT * FROM {self.table_name} WHERE id = %s"
        row = await self.db.fetchrow(query, id)
        return dict(row) if row else None

    async def find_all(
        self, limit: int = 100, offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Buscar todos los registros con paginación"""
        query = f"SELECT * FROM {self.table_name} ORDER BY id DESC LIMIT %s OFFSET %s"
        rows = await self.db.fetch(query, limit, offset)
        return [dict(row) for row in rows]

    async def create(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Crear un nuevo registro"""
        import uuid
        
        # Si no hay ID, generar uno
        if 'id' not in data:
            data['id'] = str(uuid.uuid4())
        
        columns = ", ".join(data.keys())
        placeholders = ", ".join(["%s"] * len(data))
        
        # MySQL no soporta RETURNING, así que usamos dos queries
        async with self.db.acquire() as (cursor, conn):
            insert_query = f"""
                INSERT INTO {self.table_name} ({columns})
                VALUES ({placeholders})
            """
            await cursor.execute(insert_query, tuple(data.values()))
            await conn.commit()
            
            # Obtener el registro insertado
            select_query = f"SELECT * FROM {self.table_name} WHERE id = %s"
            await cursor.execute(select_query, (data['id'],))
            row = await cursor.fetchone()
            
            return dict(row) if row else {}

    async def update(self, id: int, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Actualizar un registro"""
        set_clause = ", ".join(f"{key} = %s" for key in data.keys())
        
        # MySQL no soporta RETURNING, así que usamos dos queries
        async with self.db.acquire() as (cursor, conn):
            update_query = f"""
                UPDATE {self.table_name}
                SET {set_clause}, updated_at = NOW()
                WHERE id = %s
            """
            await cursor.execute(update_query, (*data.values(), id))
            await conn.commit()
            
            # Obtener el registro actualizado
            select_query = f"SELECT * FROM {self.table_name} WHERE id = %s"
            await cursor.execute(select_query, (id,))
            row = await cursor.fetchone()
            
            return dict(row) if row else None

    async def delete(self, id: int) -> bool:
        """Eliminar un registro"""
        query = f"DELETE FROM {self.table_name} WHERE id = %s"
        result = await self.db.execute(query, id)
        return result is not None

    async def exists(self, id: int) -> bool:
        """Verificar si existe un registro"""
        query = f"SELECT EXISTS(SELECT 1 FROM {self.table_name} WHERE id = %s) as `exists`"
        row = await self.db.fetchrow(query, id)
        return bool(row.get('exists', 0)) if row else False


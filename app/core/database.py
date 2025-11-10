"""
Pool de conexiones a MySQL usando aiomysql
"""
import aiomysql
from typing import Optional, Any, Tuple, Dict
from contextlib import asynccontextmanager
import json

from app.core.logging import get_logger
from app.core.errors import DatabaseError

logger = get_logger(__name__)


class Database:
    """Gestor de pool de conexiones a MySQL"""

    def __init__(self) -> None:
        self._pool: Optional[aiomysql.Pool] = None

    async def connect(
        self,
        host: str,
        port: int,
        database: str,
        user: str,
        password: str,
        min_size: int = 5,
        max_size: int = 20,
        timeout: float = 10.0,
    ) -> None:
        """
        Crear pool de conexiones a la base de datos MySQL
        
        Args:
            host: Host de la base de datos
            port: Puerto de la base de datos
            database: Nombre de la base de datos
            user: Usuario de la base de datos
            password: Contraseña de la base de datos
            min_size: Mínimo de conexiones en el pool
            max_size: Máximo de conexiones en el pool
            timeout: Timeout para obtener una conexión (segundos)
        """
        try:
            self._pool = await aiomysql.create_pool(
                host=host,
                port=port,
                db=database,
                user=user,
                password=password,
                minsize=min_size,
                maxsize=max_size,
                autocommit=False,
                charset='utf8mb4',
                connect_timeout=timeout,
            )
            logger.info(
                "database_pool_created",
                host=host,
                database=database,
                min_size=min_size,
                max_size=max_size,
            )
        except Exception as e:
            logger.error("database_connection_failed", error=str(e), host=host)
            raise DatabaseError(f"No se pudo conectar a la base de datos: {e}")

    async def disconnect(self) -> None:
        """Cerrar el pool de conexiones"""
        if self._pool:
            self._pool.close()
            await self._pool.wait_closed()
            logger.info("database_pool_closed")
            self._pool = None

    @property
    def pool(self) -> aiomysql.Pool:
        """
        Obtener el pool de conexiones
        
        Returns:
            Pool de conexiones de aiomysql
        
        Raises:
            DatabaseError: Si el pool no está inicializado
        """
        if not self._pool:
            raise DatabaseError("Pool de base de datos no inicializado")
        return self._pool

    @asynccontextmanager
    async def acquire(self):
        """
        Context manager para obtener una conexión del pool
        
        Yields:
            Conexión de aiomysql con cursor
        """
        if not self._pool:
            raise DatabaseError("Pool de base de datos no inicializado")

        async with self._pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cursor:
                yield cursor, conn

    async def execute(self, query: str, *args, timeout: Optional[float] = None):
        """
        Ejecutar una query que no retorna resultados
        
        Args:
            query: Query SQL a ejecutar
            *args: Argumentos para la query
            timeout: Timeout opcional para la query
        
        Returns:
            Número de filas afectadas
        """
        async with self.acquire() as (cursor, conn):
            await cursor.execute(query, args or None)
            await conn.commit()
            return cursor.rowcount

    async def fetch(self, query: str, *args, timeout: Optional[float] = None):
        """
        Ejecutar una query y retornar todos los resultados
        
        Args:
            query: Query SQL a ejecutar
            *args: Argumentos para la query
            timeout: Timeout opcional para la query
        
        Returns:
            Lista de registros como diccionarios
        """
        async with self.acquire() as (cursor, conn):
            await cursor.execute(query, args or None)
            results = await cursor.fetchall()
            return [self._deserialize_json_fields(row) for row in results]

    async def fetchrow(self, query: str, *args, timeout: Optional[float] = None):
        """
        Ejecutar una query y retornar un solo resultado
        
        Args:
            query: Query SQL a ejecutar
            *args: Argumentos para la query
            timeout: Timeout opcional para la query
        
        Returns:
            Un registro como diccionario o None
        """
        async with self.acquire() as (cursor, conn):
            await cursor.execute(query, args or None)
            result = await cursor.fetchone()
            return self._deserialize_json_fields(result) if result else None

    async def fetchval(self, query: str, *args, timeout: Optional[float] = None):
        """
        Ejecutar una query y retornar un solo valor
        
        Args:
            query: Query SQL a ejecutar
            *args: Argumentos para la query
            timeout: Timeout opcional para la query
        
        Returns:
            Un valor o None
        """
        async with self.acquire() as (cursor, conn):
            await cursor.execute(query, args or None)
            result = await cursor.fetchone()
            if result:
                # Retorna el primer valor de la primera fila
                return list(result.values())[0] if isinstance(result, dict) else result[0]
            return None
    
    @asynccontextmanager
    async def transaction(self):
        """
        Context manager para transacciones atómicas
        
        Yields:
            Tuple de (cursor, connection)
        """
        if not self._pool:
            raise DatabaseError("Pool de base de datos no inicializado")

        async with self._pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cursor:
                try:
                    await conn.begin()
                    yield cursor, conn
                    await conn.commit()
                except Exception as e:
                    await conn.rollback()
                    logger.error("transaction_rollback", error=str(e))
                    raise

    def _deserialize_json_fields(self, row: Optional[Dict]) -> Optional[Dict]:
        """
        Deserializar campos JSON que vienen como strings desde MySQL
        
        Args:
            row: Fila de resultado de MySQL
            
        Returns:
            Fila con campos JSON deserializados
        """
        if not row:
            return None
            
        # Campos que sabemos que son JSON
        json_fields = {'metadata', 'raw_payload', 'config_value'}
        
        for field in json_fields:
            if field in row and row[field] and isinstance(row[field], str):
                try:
                    row[field] = json.loads(row[field])
                except (json.JSONDecodeError, TypeError):
                    # Si no se puede deserializar, dejarlo como está
                    pass
        
        return row


# Instancia global del pool de base de datos
db = Database()


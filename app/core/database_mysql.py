"""
Database connection manager for MySQL (XAMPP)
"""
import aiomysql
from typing import Optional
from app.core.logging import get_logger
from app.config import get_settings

logger = get_logger(__name__)
settings = get_settings()

class MySQLDatabase:
    """MySQL Database Connection Manager"""
    
    def __init__(self):
        self.pool: Optional[aiomysql.Pool] = None
    
    async def connect(self) -> None:
        """Create MySQL connection pool"""
        if self.pool is not None:
            logger.warning("Database pool already exists")
            return
        
        try:
            self.pool = await aiomysql.create_pool(
                host=settings.MYSQL_HOST,
                port=settings.MYSQL_PORT,
                user=settings.MYSQL_USER,
                password=settings.MYSQL_PASSWORD,
                db=settings.MYSQL_DATABASE,
                minsize=5,
                maxsize=20,
                autocommit=False,
                charset='utf8mb4',
                echo=False
            )
            logger.info(
                "MySQL connection pool created",
                extra={
                    "host": settings.MYSQL_HOST,
                    "database": settings.MYSQL_DATABASE,
                    "pool_size": f"5-20"
                }
            )
        except Exception as e:
            logger.error(f"Failed to create MySQL pool: {e}")
            raise
    
    async def disconnect(self) -> None:
        """Close MySQL connection pool"""
        if self.pool is None:
            logger.warning("No database pool to close")
            return
        
        try:
            self.pool.close()
            await self.pool.wait_closed()
            self.pool = None
            logger.info("MySQL connection pool closed")
        except Exception as e:
            logger.error(f"Error closing MySQL pool: {e}")
            raise
    
    def get_pool(self) -> aiomysql.Pool:
        """Get the connection pool"""
        if self.pool is None:
            raise RuntimeError("Database pool not initialized. Call connect() first.")
        return self.pool


# Global instance
mysql_db = MySQLDatabase()


async def get_db_connection():
    """FastAPI dependency for getting a database connection"""
    pool = mysql_db.get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cursor:
            yield cursor


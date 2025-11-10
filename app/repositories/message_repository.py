"""
Repository para mensajes de WhatsApp
"""
from typing import Optional, Dict, Any, List
from app.repositories.base import BaseRepository
from app.core.database import Database


class MessageRepository(BaseRepository):
    """Repository para gestionar mensajes"""

    def __init__(self, db: Database):
        super().__init__(db, "messages")

    async def find_by_conversation(
        self, conversation_id: int, limit: int = 100, offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Buscar mensajes por conversación"""
        query = """
            SELECT * FROM messages
            WHERE conversation_id = %s
            ORDER BY created_at DESC
            LIMIT %s OFFSET %s
        """
        rows = await self.db.fetch(query, conversation_id, limit, offset)
        return [dict(row) for row in rows]

    async def find_by_trip(
        self, trip_id: str, limit: int = 100, offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Buscar mensajes por viaje"""
        query = """
            SELECT * FROM messages
            WHERE trip_id = %s
            ORDER BY created_at DESC
            LIMIT %s OFFSET %s
        """
        rows = await self.db.fetch(query, trip_id, limit, offset)
        return [dict(row) for row in rows]

    async def create_message(self, message_data: Dict[str, Any]) -> Dict[str, Any]:
        """Crear un mensaje"""
        import json
        import uuid
        
        # Generar UUID para el mensaje
        message_id = str(uuid.uuid4())
        
        # MySQL no soporta RETURNING, así que usamos dos queries
        async with self.db.acquire() as (cursor, conn):
            insert_query = """
                INSERT INTO messages (
                    id, conversation_id, trip_id, whatsapp_message_id,
                    sender_type, sender_phone, direction, content,
                    transcription, ai_result
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            
            # Convertir ai_result a JSON string si es dict
            ai_result = message_data.get("ai_result")
            if ai_result and isinstance(ai_result, dict):
                ai_result = json.dumps(ai_result)
            
            await cursor.execute(
                insert_query,
                (
                    message_id,
                    message_data.get("conversation_id"),
                    message_data.get("trip_id"),
                    message_data.get("whatsapp_message_id"),
                    message_data.get("sender_type"),
                    message_data.get("sender_phone"),
                    message_data.get("direction"),
                    message_data.get("content"),
                    message_data.get("transcription"),
                    ai_result,
                )
            )
            await conn.commit()
            
            # Obtener el mensaje insertado
            select_query = "SELECT * FROM messages WHERE id = %s"
            await cursor.execute(select_query, (message_id,))
            row = await cursor.fetchone()
            
            return dict(row) if row else {}


class ConversationRepository(BaseRepository):
    """Repository para gestionar conversaciones"""

    def __init__(self, db: Database):
        super().__init__(db, "conversations")

    async def find_by_trip(self, trip_id: str) -> Optional[Dict[str, Any]]:
        """Buscar conversación por viaje"""
        query = "SELECT * FROM conversations WHERE trip_id = %s"
        row = await self.db.fetchrow(query, trip_id)
        return dict(row) if row else None

    async def find_by_group_id(self, whatsapp_group_id: str) -> Optional[Dict[str, Any]]:
        """Buscar conversación por ID de grupo de WhatsApp"""
        query = "SELECT * FROM conversations WHERE whatsapp_group_id = %s"
        row = await self.db.fetchrow(query, whatsapp_group_id)
        return dict(row) if row else None

    async def create_conversation(
        self, conversation_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Crear una conversación"""
        import json
        
        # Guardar group_name y participants en metadata
        metadata = conversation_data.get("metadata", {})
        if "group_name" in conversation_data:
            metadata["group_name"] = conversation_data["group_name"]
        if "participants" in conversation_data:
            metadata["participants"] = conversation_data["participants"]
        
        # Usar la misma conexión para INSERT y SELECT
        async with self.db.acquire() as (cursor, conn):
            insert_query = """
                INSERT INTO conversations (
                    trip_id, whatsapp_group_id, driver_id, status, metadata
                )
                VALUES (%s, %s, %s, %s, %s)
            """
            
            await cursor.execute(
                insert_query,
                (
                    conversation_data.get("trip_id"),
                    conversation_data.get("whatsapp_group_id"),
                    conversation_data.get("driver_id"),
                    conversation_data.get("status", "active"),
                    json.dumps(metadata),
                )
            )
            await conn.commit()
            
            # Hacer SELECT en la misma conexión
            select_query = "SELECT * FROM conversations WHERE trip_id = %s"
            await cursor.execute(select_query, (conversation_data.get("trip_id"),))
            row = await cursor.fetchone()
            
            return dict(row) if row else None

    async def deactivate_conversation(self, conversation_id: str) -> bool:
        """Desactivar una conversación"""
        query = """
            UPDATE conversations 
            SET status = 'inactive', updated_at = NOW() 
            WHERE id = %s
        """
        result = await self.db.execute(query, conversation_id)
        return result > 0  # execute devuelve el número de filas afectadas


class AIInteractionRepository(BaseRepository):
    """Repository para interacciones de IA"""

    def __init__(self, db: Database):
        super().__init__(db, "ai_interactions")

    async def find_by_trip(
        self, trip_id: str, limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Buscar interacciones por viaje"""
        query = """
            SELECT * FROM ai_interactions
            WHERE trip_id = %s
            ORDER BY created_at DESC
            LIMIT %s
        """
        rows = await self.db.fetch(query, trip_id, limit)
        return [dict(row) for row in rows]

    async def create_interaction(
        self, interaction_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Crear una interacción de IA"""
        import json
        import uuid
        
        # Generar UUID para la interacción
        interaction_id = str(uuid.uuid4())
        
        # MySQL no soporta RETURNING, así que usamos dos queries
        async with self.db.acquire() as (cursor, conn):
            insert_query = """
                INSERT INTO ai_interactions (
                    id, message_id, trip_id, driver_message, ai_classification,
                    ai_confidence, ai_response, model_used, prompt_used, metadata
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            
            # Mapear nombres de columnas del código a los nombres de la BD
            driver_message = interaction_data.get("input_text", "")
            ai_classification = interaction_data.get("intent", "")
            ai_confidence = interaction_data.get("confidence", 0.0)
            ai_response = interaction_data.get("response_text", "")
            model_used = interaction_data.get("model_used", "gemini")
            prompt_used = interaction_data.get("prompt_used", "")
            
            # Combinar entities y response_metadata en metadata
            metadata = {
                "entities": interaction_data.get("entities", {}),
                "response_metadata": interaction_data.get("response_metadata", {})
            }
            if isinstance(metadata, dict):
                metadata = json.dumps(metadata)
            
            await cursor.execute(
                insert_query,
                (
                    interaction_id,
                    interaction_data.get("message_id"),
                    interaction_data.get("trip_id"),
                    driver_message,
                    ai_classification,
                    ai_confidence,
                    ai_response,
                    model_used,
                    prompt_used,
                    metadata,
                )
            )
            await conn.commit()
            
            # Obtener la interacción insertada
            select_query = "SELECT * FROM ai_interactions WHERE id = %s"
            await cursor.execute(select_query, (interaction_id,))
            row = await cursor.fetchone()
            
            return dict(row) if row else {}


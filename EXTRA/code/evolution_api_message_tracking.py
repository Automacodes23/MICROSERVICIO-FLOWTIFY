#!/usr/bin/env python3
"""
Evolution API - Verificación de Estado de Mensajes
==================================================

Este ejemplo muestra cómo verificar si un mensaje realmente se envió 
y llegó al número usando Evolution API con Python.

MÉTODOS DE VERIFICACIÓN:
1. WebSocket Events (RECOMENDADO - Tiempo real)
2. Webhooks (Callbacks en tiempo real)
3. Polling de estado (Verificación manual)
"""

import asyncio
import json
import time
import requests
import logging
from datetime import datetime
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass
from enum import Enum

# Configuración de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class MessageStatus(Enum):
    """Estados posibles de un mensaje en WhatsApp"""
    PENDING = "PENDING"
    SENT = "SENT"
    DELIVERED = "DELIVERED" 
    READ = "READ"
    FAILED = "FAILED"

@dataclass
class MessageInfo:
    """Información de un mensaje para tracking"""
    message_id: str
    phone_number: str
    content: str
    timestamp: str
    status: MessageStatus
    delivery_time: Optional[str] = None
    read_time: Optional[str] = None

class EvolutionAPIMessageTracker:
    """Cliente para tracking de mensajes con Evolution API"""
    
    def __init__(self, base_url: str, api_key: str, instance_name: str):
        """
        Inicializar el cliente de tracking
        
        Args:
            base_url: URL del servidor Evolution API (ej: http://localhost:8080)
            api_key: Tu API key de Evolution API
            instance_name: Nombre de tu instancia
        """
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.instance_name = instance_name
        self.headers = {
            'apikey': api_key,
            'Content-Type': 'application/json'
        }
        self.sent_messages: Dict[str, MessageInfo] = {}
        
    def send_message_with_tracking(self, phone_number: str, content: str) -> Optional[str]:
        """
        Envía un mensaje y prepara el tracking
        
        Args:
            phone_number: Número de teléfono del destinatario
            content: Contenido del mensaje
            
        Returns:
            ID del mensaje para tracking
        """
        url = f"{self.base_url}/message/sendText/{self.instance_name}"
        
        payload = {
            "number": phone_number,
            "textMessage": {
                "text": content
            }
        }
        
        try:
            response = requests.post(url, json=payload, headers=self.headers)
            response.raise_for_status()
            
            data = response.json()
            
            # Extraer el ID del mensaje de la respuesta
            message_id = data.get('key', {}).get('id')
            if not message_id:
                logger.error("No se pudo obtener el ID del mensaje")
                return None
                
            # Guardar información para tracking
            message_info = MessageInfo(
                message_id=message_id,
                phone_number=phone_number,
                content=content,
                timestamp=datetime.now().isoformat(),
                status=MessageStatus.PENDING
            )
            
            self.sent_messages[message_id] = message_info
            logger.info(f"Mensaje enviado - ID: {message_id}, Destino: {phone_number}")
            
            return message_id
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error enviando mensaje: {e}")
            return None

    def check_message_status(self, message_id: str) -> Optional[MessageInfo]:
        """
        Verifica el estado actual de un mensaje usando polling
        
        Args:
            message_id: ID del mensaje a verificar
            
        Returns:
            Información actualizada del mensaje o None si no se encuentra
        """
        if message_id not in self.sent_messages:
            logger.warning(f"Mensaje {message_id} no encontrado en tracking")
            return None
            
        # En Evolution API, el estado se actualiza a través de webhooks/webSocket
        # El polling directo no está disponible, pero podemos obtener el estado actual
        # de nuestro cache local
        return self.sent_messages[message_id]

    def get_all_pending_messages(self) -> List[MessageInfo]:
        """Obtiene todos los mensajes que aún no han sido entregados"""
        return [msg for msg in self.sent_messages.values() if msg.status in [MessageStatus.PENDING, MessageStatus.SENT]]

    def get_delivery_stats(self) -> Dict[str, int]:
        """Obtiene estadísticas de entrega de mensajes"""
        stats = {status.value: 0 for status in MessageStatus}
        for msg in self.sent_messages.values():
            stats[msg.status.value] += 1
        return stats

class WebhookServer:
    """Servidor webhook para recibir actualizaciones de estado de mensajes"""
    
    def __init__(self, tracker: EvolutionAPIMessageTracker, port: int = 5000):
        self.tracker = tracker
        self.port = port
        
    def process_message_update(self, data: Dict):
        """
        Procesa actualizaciones de estado de mensajes desde webhooks
        
        Args:
            data: Datos del webhook con información del mensaje
        """
        try:
            # Estructura típica del webhook MESSAGES_UPDATE
            if 'messages' in data and data['messages']:
                for message in data['messages']:
                    message_id = message.get('key', {}).get('id')
                    if not message_id or message_id not in self.tracker.sent_messages:
                        continue
                    
                    # Obtener el estado del mensaje
                    status_str = message.get('status', 'PENDING')
                    status = MessageStatus.PENDING
                    
                    # Mapear estados de WhatsApp a nuestro enum
                    status_mapping = {
                        'PENDING': MessageStatus.PENDING,
                        'SENT': MessageStatus.SENT,
                        'DELIVERED': MessageStatus.DELIVERED,
                        'READ': MessageStatus.READ,
                        'FAILED': MessageStatus.FAILED
                    }
                    
                    status = status_mapping.get(status_str, MessageStatus.PENDING)
                    
                    # Actualizar información del mensaje
                    msg_info = self.tracker.sent_messages[message_id]
                    old_status = msg_info.status
                    msg_info.status = status
                    
                    # Registrar timestamps específicos
                    if status == MessageStatus.DELIVERED and not msg_info.delivery_time:
                        msg_info.delivery_time = datetime.now().isoformat()
                        logger.info(f"📨 Mensaje {message_id} ENTREGADO a {msg_info.phone_number}")
                    elif status == MessageStatus.READ and not msg_info.read_time:
                        msg_info.read_time = datetime.now().isoformat()
                        logger.info(f"👁️ Mensaje {message_id} LEÍDO por {msg_info.phone_number}")
                    elif status == MessageStatus.FAILED:
                        logger.error(f"❌ Mensaje {message_id} FALLÓ para {msg_info.phone_number}")
                    
                    logger.info(f"Estado actualizado: {message_id} - {old_status.value} → {status.value}")
                    
        except Exception as e:
            logger.error(f"Error procesando actualización de mensaje: {e}")
    
    def start_webhook_server(self):
        """Inicia el servidor webhook (implementación Flask/FastAPI recomendada)"""
        logger.info(f"Servidor webhook iniciado en puerto {self.port}")
        # Aquí implementarías Flask/FastAPI para recibir webhooks
        # self.app = Flask(__name__)
        # @self.app.route('/webhook', methods=['POST'])
        # def webhook():
        #     data = request.get_json()
        #     self.process_message_update(data)
        #     return 'OK', 200
        # self.app.run(host='0.0.0.0', port=self.port)

class WebSocketTracker:
    """Tracker usando WebSocket para recibir actualizaciones en tiempo real"""
    
    def __init__(self, tracker: EvolutionAPIMessageTracker, websocket_url: str):
        self.tracker = tracker
        self.websocket_url = websocket_url
        self.callbacks: Dict[str, Callable] = {}
        
    def add_message_update_callback(self, callback: Callable):
        """Agregar callback para actualizaciones de mensajes"""
        self.callbacks['messages.update'] = callback
        
    def start_monitoring(self):
        """Inicia el monitoreo de mensajes vía WebSocket"""
        logger.info("Iniciando monitoreo WebSocket...")
        # Aquí implementarías la conexión WebSocket real
        # Usando la librería evolution-client-python o websockets
        
    def process_websocket_message(self, event_type: str, data: Dict):
        """Procesa mensajes recibidos por WebSocket"""
        if event_type == 'messages.update':
            if 'messages.update' in self.callbacks:
                self.callbacks['messages.update'](data)
            self.tracker.sent_messages = self.tracker.sent_messages or {}

# Ejemplo de uso
def ejemplo_uso():
    """Ejemplo práctico de uso del sistema de tracking"""
    
    # Configuración
    EVOLUTION_API_URL = "http://localhost:8080"
    API_KEY = "tu_api_key_aqui"
    INSTANCE_NAME = "tu_instancia"
    
    # Inicializar tracker
    tracker = EvolutionAPIMessageTracker(EVOLUTION_API_URL, API_KEY, INSTANCE_NAME)
    
    # Inicializar webhook server
    webhook_server = WebhookServer(tracker)
    
    # Inicializar WebSocket tracker
    websocket_tracker = WebSocketTracker(tracker, f"{EVOLUTION_API_URL}/websocket")
    
    # Enviar mensaje con tracking
    phone_number = "521234567890"  # Reemplaza con el número real
    content = "Hola, este es un mensaje de prueba para verificar la entrega."
    
    print("🚀 Enviando mensaje con tracking...")
    message_id = tracker.send_message_with_tracking(phone_number, content)
    
    if message_id:
        print(f"✅ Mensaje enviado. ID: {message_id}")
        print("📊 Monitoreando estado del mensaje...")
        
        # Simular verificaciones periódicas
        for i in range(10):  # Verificar por 10 ciclos
            time.sleep(2)  # Esperar 2 segundos entre verificaciones
            
            message_info = tracker.check_message_status(message_id)
            if message_info:
                print(f"Estado actual: {message_info.status.value}")
                
                if message_info.status in [MessageStatus.DELIVERED, MessageStatus.READ, MessageStatus.FAILED]:
                    break
        else:
            print("⚠️ Mensaje aún pendiente después del tiempo de espera")
        
        # Mostrar estadísticas finales
        stats = tracker.get_delivery_stats()
        print("\n📈 Estadísticas de entrega:")
        for status, count in stats.items():
            if count > 0:
                print(f"  {status}: {count}")
    
    else:
        print("❌ Error enviando mensaje")

if __name__ == "__main__":
    ejemplo_uso()
# Evolution API - Verificación de Entrega de Mensajes

Este proyecto proporciona una implementación completa en Python para verificar si los mensajes enviados a través de Evolution API realmente se enviaron y llegaron al número de destino.

## 📋 Características

- **Tracking de mensajes en tiempo real** usando WebSocket
- **Webhooks automáticos** para recibir confirmaciones de entrega
- **Verificación de números** con WhatsApp activo
- **Estadísticas detalladas** de entrega de mensajes
- **Monitoreo continuo** de estados de mensajes
- **Logs detallados** para debugging

## 🚀 Métodos de Verificación

### 1. **WebSocket Events (RECOMENDADO)**
- Recibe actualizaciones en tiempo real
- Baja latencia
- Confiabilidad alta
- Estados: `PENDING` → `SENT` → `DELIVERED` → `READ`

### 2. **Webhooks (CALLBACKS)**
- Configuración simple
- Escalable
- Ideal para aplicaciones de producción
- URLs específicas por evento

### 3. **Polling Manual**
- Verificación manual de estados
- Control total del timing
- Menos eficiente pero más control

## 📦 Instalación

1. **Instalar dependencias:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Verificar Evolution API:**
   - Asegúrate de que tu Evolution API esté ejecutándose
   - Ten tu API key y nombre de instancia listos
   - El puerto por defecto es 8080

## 🔧 Configuración

### Variables de Entorno
```bash
# .env
EVOLUTION_API_URL=http://localhost:8080
EVOLUTION_API_KEY=tu_api_key_aqui
EVOLUTION_INSTANCE_NAME=mi_instancia
WEBHOOK_BASE_URL=http://localhost:5000
```

### Configuración de Webhooks
En tu Evolution API, asegúrate de que los eventos de webhook estén habilitados:

```json
{
  "events": [
    "MESSAGES_UPSERT",
    "MESSAGES_UPDATE", 
    "SEND_MESSAGE",
    "MESSAGES_DELETE"
  ]
}
```

## 💻 Uso Básico

### 1. Verificar Estado de Un Mensaje

```python
from evolution_api_message_tracking import EvolutionAPIMessageTracker

# Configurar tracker
tracker = EvolutionAPIMessageTracker(
    base_url="http://localhost:8080",
    api_key="tu_api_key",
    instance_name="mi_instancia"
)

# Enviar mensaje con tracking
message_id = tracker.send_message_with_tracking(
    phone_number="521234567890",
    content="Hola, mensaje de prueba"
)

# Verificar estado
if message_id:
    message_info = tracker.check_message_status(message_id)
    print(f"Estado del mensaje: {message_info.status.value}")
```

### 2. Verificar Número con WhatsApp

```python
# Verificar si el número tiene WhatsApp
is_whatsapp = tracker.check_whatsapp_number("521234567890")
if is_whatsapp:
    print("✅ El número tiene WhatsApp")
else:
    print("❌ El número no tiene WhatsApp")
```

### 3. Obtener Estadísticas de Entrega

```python
# Estadísticas generales
stats = tracker.get_delivery_stats()
print(f"Mensajes entregados: {stats['DELIVERED']}")
print(f"Mensajes leídos: {stats['READ']}")
print(f"Mensajes fallidos: {stats['FAILED']}")

# Resumen detallado
summary = tracker.get_delivery_summary()
print(summary)
```

## 🌐 Servidor Webhook

### Configuración del Servidor

```python
from flask import Flask, request, jsonify
from evolution_api_complete_tracking import MessageDeliveryTracker

# Crear tracker
tracker = MessageDeliveryTracker(
    api_url="http://localhost:8080",
    api_key="tu_api_key",
    instance_name="mi_instancia"
)

# Crear aplicación Flask
app = Flask(__name__)

@app.route('/webhook/messages-update', methods=['POST'])
def webhook_messages_update():
    """Recibir actualizaciones de estado de mensajes"""
    data = request.get_json()
    
    for message in data.get('messages', []):
        message_id = message.get('key', {}).get('id')
        status = message.get('status', 'PENDING')
        tracker.update_message_status(message_id, status, message)
    
    return jsonify({'status': 'ok'}), 200

# Iniciar servidor
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
```

### URLs de Webhook

Una vez configurado, Evolution API enviará eventos a:

- `POST /webhook/messages-update` - Actualizaciones de estado
- `POST /webhook/messages-upsert` - Mensajes nuevos
- `POST /webhook/send-message` - Mensajes enviados

## 📊 Estados de Mensajes

| Estado | Descripción | Timestamp |
|--------|-------------|-----------|
| `PENDING` | Mensaje enviado, esperando confirmación | `sent_time` |
| `SENT` | Mensaje enviado al servidor de WhatsApp | `sent_time` |
| `DELIVERED` | Mensaje entregado al dispositivo | `delivery_time` |
| `READ` | Mensaje leído por el destinatario | `read_time` |
| `FAILED` | Error en el envío | `failed_time` |

## 🔄 Ejemplo Completo de Uso

```python
import asyncio
from evolution_api_complete_tracking import MessageDeliveryTracker

async def ejemplo_completo():
    # Configurar tracker
    tracker = MessageDeliveryTracker(
        api_url="http://localhost:8080",
        api_key="tu_api_key", 
        instance_name="mi_instancia"
    )
    
    # Verificar número
    phone = "521234567890"
    if not await tracker.check_whatsapp_number(phone):
        print("Número no válido")
        return
    
    # Configurar webhooks
    await tracker.configure_webhooks("http://localhost:5000")
    
    # Enviar mensaje
    message_id = await tracker.send_text_message_with_tracking(
        phone, "Hola, este es un mensaje de prueba"
    )
    
    # Monitorear estado por 30 segundos
    for i in range(6):
        await asyncio.sleep(5)
        message_info = tracker.get_message_status(message_id)
        print(f"Estado actual: {message_info['status']}")
    
    # Mostrar resumen final
    print(tracker.get_delivery_summary())

# Ejecutar
asyncio.run(ejemplo_completo())
```

## 🛠️ Configuración de Evolution API

### 1. Instalar Evolution API
```bash
# Docker
docker run -d \
  --name evolution-api \
  -p 8080:8080 \
  -e TZ=America/Mexico_City \
  evolution/api:latest
```

### 2. Crear Instancia
```bash
curl -X POST "http://localhost:8080/instance/create" \
  -H "apikey: tu_api_key" \
  -H "Content-Type: application/json" \
  -d '{
    "instanceName": "mi_instancia",
    "integration": "whatsapp-baileys"
  }'
```

### 3. Conectar WhatsApp
- Abre WhatsApp en tu teléfono
- Ve a Dispositivos vinculados
- Escanea el código QR que aparece en los logs

## 🚨 Troubleshooting

### Problemas Comunes

1. **Error 401 Unauthorized**
   - Verifica tu API key
   - Confirma el nombre de la instancia

2. **Mensajes no llegan**
   - Verifica que el número tenga WhatsApp
   - Revisa la configuración de webhooks
   - Confirma que el servidor webhook esté activo

3. **Webhook no recibe eventos**
   - Verifica la URL del webhook
   - Confirma que Evolution API tenga acceso a tu servidor
   - Revisa los logs del servidor

### Logs de Debug
```python
import logging
logging.basicConfig(level=logging.DEBUG)

# Esto mostrará información detallada de todas las operaciones
```

## 📈 Métricas y Monitoreo

### Estadísticas Disponibles
- Total de mensajes enviados
- Tasa de entrega (%)
- Tasa de lectura (%)
- Mensajes fallidos
- Tiempo promedio de entrega

### Ejemplo de Métricas
```
📊 RESUMEN DE ENTREGA (Total: 10 mensajes)
  ⏳ Pendientes: 0
  📤 Enviados: 1
  📨 Entregados: 8
  👁️ Leídos: 1
  ❌ Fallidos: 0

🎯 Tasa de entrega exitosa: 90.0%
```

## 🔐 Seguridad

- **API Key:** Mantén tu API key segura
- **HTTPS:** Usa HTTPS en producción para webhooks
- **Validación:** Valida todas las entradas
- **Rate Limiting:** Implementa límites de velocidad

## 📚 Recursos Adicionales

- [Documentación oficial de Evolution API](https://doc.evolution-api.com/)
- [Cliente Python oficial](https://github.com/EvolutionAPI/evolution-client-python)
- [Webhook de WhatsApp Cloud API](https://developers.facebook.com/docs/whatsapp/cloud-api/guides/set-up-webhooks/)

## 🤝 Contribución

1. Fork el proyecto
2. Crea una rama para tu feature
3. Commit tus cambios
4. Push a la rama
5. Abre un Pull Request

## 📄 Licencia

Este proyecto está bajo la licencia MIT. Ver `LICENSE` para más detalles.

---

**Nota:** Este proyecto es una implementación educativa. Para uso en producción, asegúrate de implementar las medidas de seguridad apropiadas y realizar pruebas exhaustivas.
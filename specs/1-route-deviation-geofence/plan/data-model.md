# Data Model: Detección de Desviación de Ruta mediante Geocercas

## Entidades Principales

### Geocerca de Ruta (Geofence)

**Tabla**: `geofences` (existente)
**Relación**: `trip_geofences` (existente)

**Campos Clave**:
- `id`: UUID - Identificador único de la geocerca
- `floatify_geofence_id`: VARCHAR(255) - ID de la geocerca en Floatify
- `wialon_geofence_id`: VARCHAR(255) - ID de la geocerca en Wialon
- `name`: VARCHAR(255) - Nombre de la geocerca (ej: "RUTA")
- `geofence_type`: VARCHAR(50) - Tipo de geocerca (circle, polygon, etc.)

**Relación con Viaje**: `trip_geofences`
- `trip_id`: UUID - ID del viaje
- `geofence_id`: UUID - ID de la geocerca
- `visit_type`: VARCHAR(50) - **Role de la geocerca (ej: "route", "loading", "unloading")**
- `sequence_order`: INT - Orden en la secuencia
- `entered_at`: TIMESTAMP - Fecha/hora de entrada a la geocerca
- `exited_at`: TIMESTAMP - Fecha/hora de salida de la geocerca

**Validaciones**:
- `visit_type` debe ser uno de: "origin", "loading", "unloading", "waypoint", "depot", **"route"**
- `visit_type` = "route" indica que es una geocerca de ruta
- La geocerca debe estar asociada a un viaje activo

---

### Evento de Desviación de Ruta (Event)

**Tabla**: `events` (existente)

**Campos Clave**:
- `id`: UUID - Identificador único del evento
- `trip_id`: UUID - ID del viaje asociado
- `unit_id`: UUID - ID de la unidad/vehículo
- `source`: VARCHAR(50) - Fuente del evento (ej: "wialon")
- `event_type`: VARCHAR(50) - Tipo de evento (ej: "geofence_exit")
- `latitude`: DECIMAL(10, 8) - Latitud del vehículo
- `longitude`: DECIMAL(11, 8) - Longitud del vehículo
- `speed`: DECIMAL(10, 2) - Velocidad del vehículo
- `address`: TEXT - Dirección geocodificada
- `raw_payload`: JSON - Payload completo del evento de Wialon
- `processed`: BOOLEAN - Indica si el evento fue procesado
- `processed_at`: TIMESTAMP - Fecha/hora de procesamiento

**Validaciones**:
- `event_type` debe ser "geofence_exit" para detectar desviación de ruta
- `raw_payload` debe incluir `geofence_id` y `geofence_name`
- El evento debe estar asociado a un viaje activo

---

### Notificación de Desviación (Notification Tracking)

**Tabla**: No requiere tabla (almacenamiento en memoria)

**Estructura en Memoria**:
```python
{
    "trip_id": {
        "last_notification_time": timestamp,
        "last_geofence_name": str
    }
}
```

**Campos**:
- `trip_id`: UUID - ID del viaje
- `last_notification_time`: TIMESTAMP - Última vez que se envió notificación de desviación
- `last_geofence_name`: STR - Nombre de la última geocerca de la cual salió

**Validaciones**:
- Período de gracia: 5 minutos (configurable)
- Solo se almacena para viajes activos
- Se limpia cuando el viaje se completa o cancela

---

### Webhook de Desviación (Route Deviation Webhook)

**Modelo**: `RouteDeviationWebhook` (existente)

**Campos Clave**:
- `event`: STR - Tipo de evento ("route_deviation")
- `timestamp`: ISO8601 - Timestamp del evento
- `tenant_id`: INT - ID del tenant
- `deviation`: DICT - Información de la desviación
  - `type`: STR - Tipo de desviación ("route_deviation")
  - `severity`: STR - Severidad ("critical")
  - `deviation_id`: STR - ID único de la desviación
  - `distance_from_route_meters`: FLOAT - Distancia de la ruta (0 para salida de geocerca)
  - `max_allowed_deviation`: FLOAT - Desviación máxima permitida (100 metros por defecto)
  - `excess_deviation_meters`: FLOAT - Exceso de desviación (0 para salida de geocerca)
  - `deviation_duration_seconds`: INT - Duración de la desviación (0 para salida de geocerca)
  - `current_location`: DICT - Ubicación actual del vehículo
  - `nearest_point_on_route`: DICT - Punto más cercano en la ruta (vacío para salida de geocerca)
- `trip`: DICT - Información del viaje
- `driver`: DICT - Información del conductor
- `unit`: DICT - Información de la unidad
- `route_info`: DICT - Información de la ruta (vacío por ahora)
- `immediate_actions`: DICT - Acciones inmediatas
- `wialon_source`: DICT - Fuente Wialon

**Validaciones**:
- `distance_from_route_meters` = 0 cuando es salida de geocerca (no se calcula distancia)
- `current_location` debe incluir `latitude` y `longitude`
- `wialon_source` debe incluir `notification_id` y `external_id`

---

## Relaciones

### Viaje → Geocerca de Ruta

**Relación**: Uno a Muchos
**Tabla**: `trip_geofences`
**Cardinalidad**: Un viaje puede tener múltiples geocercas, incluyendo una geocerca de ruta

**Restricciones**:
- Un viaje puede tener solo una geocerca con `visit_type` = "route"
- La geocerca de ruta debe estar asociada al viaje en `trip_geofences`
- El `visit_type` se almacena en `trip_geofences.visit_type`

---

### Evento → Viaje

**Relación**: Muchos a Uno
**Tabla**: `events`
**Cardinalidad**: Un viaje puede tener múltiples eventos

**Restricciones**:
- Cada evento debe estar asociado a un viaje
- El evento debe tener `event_type` = "geofence_exit" para detectar desviación
- El evento debe incluir `geofence_id` para identificar la geocerca

---

### Evento → Geocerca

**Relación**: Muchos a Uno (indirecta a través de `geofence_id`)
**Tabla**: `events` → `geofences` (a través de `geofence_id` en `raw_payload`)
**Cardinalidad**: Un evento se refiere a una geocerca

**Restricciones**:
- El evento debe incluir `geofence_id` en el payload
- La geocerca debe existir en `geofences`
- La geocerca debe estar asociada al viaje en `trip_geofences`

---

## Estados y Transiciones

### Estado del Viaje

**No cambia** cuando se detecta desviación de ruta.

**Estados Posibles**:
- `en_ruta_carga`: El viaje está en ruta hacia la zona de carga
- `en_zona_carga`: El viaje está en la zona de carga
- `en_ruta_destino`: El viaje está en ruta hacia el destino
- `en_zona_descarga`: El viaje está en la zona de descarga
- `finalizado`: El viaje está completado
- `cancelado`: El viaje está cancelado

**Comportamiento**:
- La desviación de ruta NO cambia el estado del viaje
- El viaje mantiene su estado actual independientemente de la desviación
- Solo las geocercas de carga/descarga cambian el estado del viaje

---

### Estado de la Geocerca de Ruta

**Estados**:
- `inside`: El vehículo está dentro de la geocerca de ruta
- `outside`: El vehículo está fuera de la geocerca de ruta

**Transiciones**:
- `inside` → `outside`: Se detecta desviación de ruta
  - Se envía notificación WhatsApp (si no hay período de gracia activo)
  - Se envían webhooks `geofence_transition` y `route_deviation`
  - Se registra el evento en la BD
- `outside` → `inside`: El vehículo regresa a la ruta
  - Se envía webhook `geofence_transition` (solo entrada)
  - No se envía notificación WhatsApp
  - Se registra el evento en la BD

---

### Estado de la Notificación

**Estados**:
- `pending`: Notificación pendiente de envío
- `sent`: Notificación enviada
- `blocked`: Notificación bloqueada por período de gracia

**Transiciones**:
- `pending` → `sent`: Se envía notificación WhatsApp
- `pending` → `blocked`: Período de gracia activo (última notificación < 5 minutos)
- `blocked` → `sent`: Período de gracia expirado (última notificación >= 5 minutos)

---

## Validaciones y Reglas de Negocio

### Validación de Role de Geocerca

**Regla**: El role de la geocerca se obtiene desde `trip_geofences.visit_type`

**Flujo**:
1. Consultar `trip_geofences` usando `trip_id` y `geofence_id`
2. Si se encuentra, usar `visit_type` como role
3. Si no se encuentra, usar detección por nombre (fallback)
4. Buscar palabras clave: "ruta", "route" en `geofence_name`
5. Si se encuentra, establecer `role = "route"`

**Validaciones**:
- `visit_type` debe ser uno de los valores válidos: "origin", "loading", "unloading", "waypoint", "depot", "route"
- Si `visit_type` = "route", se considera desviación de ruta cuando hay salida

---

### Validación de Período de Gracia

**Regla**: Solo se envía una notificación WhatsApp cada 5 minutos por viaje

**Flujo**:
1. Verificar si existe registro en memoria para `trip_id`
2. Si no existe, enviar notificación y registrar timestamp
3. Si existe, verificar si han pasado 5 minutos desde `last_notification_time`
4. Si han pasado 5 minutos, enviar notificación y actualizar timestamp
5. Si no han pasado 5 minutos, no enviar notificación (pero sí enviar webhooks)

**Validaciones**:
- Período de gracia: 5 minutos (300 segundos) por defecto
- Período de gracia configurable mediante variable de entorno o constante
- Período de gracia solo aplica a notificaciones WhatsApp, no a webhooks

---

### Validación de Webhook route_deviation

**Regla**: El webhook `route_deviation` se envía cuando se detecta salida de geocerca de ruta

**Flujo**:
1. Detectar salida de geocerca con `visit_type` = "route"
2. Preparar datos de desviación:
   - `distance_meters` = 0 (no se calcula distancia)
   - `max_allowed` = 100 (valor por defecto)
   - `duration_seconds` = 0 (no se calcula duración)
   - `current_location` = ubicación actual del vehículo
   - `nearest_point` = {} (vacío)
3. Llamar a `WebhookService.send_route_deviation()`
4. Si falla, loggear error pero continuar con el flujo

**Validaciones**:
- `distance_meters` debe ser 0 cuando es salida de geocerca
- `current_location` debe incluir `latitude` y `longitude`
- El webhook debe incluir información de la geocerca de la cual salió el vehículo

---

## Índices y Optimizaciones

### Índices Existentes

**Tabla `trip_geofences`**:
- `idx_trip`: Índice en `trip_id`
- `idx_geofence`: Índice en `geofence_id`
- `idx_sequence`: Índice en `(trip_id, sequence_order)`

**Tabla `events`**:
- `idx_events_trip`: Índice en `(trip_id, created_at DESC)`
- `idx_events_unprocessed`: Índice en `processed` WHERE `processed = false`
- `idx_events_external`: Índice en `external_id`

### Optimizaciones Recomendadas

**Consulta de Role de Geocerca**:
- La consulta actual ya usa índices (`trip_id` y `geofence_id`)
- No se requieren índices adicionales
- La consulta es eficiente con JOIN en tablas indexadas

**Período de Gracia**:
- Almacenamiento en memoria es eficiente para operaciones O(1)
- Limpieza periódica de entradas antiguas (cada 1 hora)
- No requiere índices de BD

---

## Migraciones de Base de Datos

### No se Requieren Migraciones

**Razón**: 
- La tabla `trip_geofences` ya tiene el campo `visit_type` que almacena el role
- El campo `visit_type` ya soporta el valor "route"
- No se requieren cambios en la estructura de la BD

### Verificación Requerida

**Acción**: Verificar que el campo `visit_type` en `trip_geofences` acepta el valor "route"

**Query de Verificación**:
```sql
SELECT COLUMN_TYPE 
FROM INFORMATION_SCHEMA.COLUMNS 
WHERE TABLE_NAME = 'trip_geofences' 
  AND COLUMN_NAME = 'visit_type';
```

**Resultado Esperado**: `VARCHAR(50)` o similar que acepte el valor "route"

---

## Modelos Pydantic

### WialonEvent (Existente)

**Campos Relevantes**:
- `geofence_id`: Optional[str] - ID de la geocerca
- `geofence_name`: Optional[str] - Nombre de la geocerca
- `notification_type`: str - Tipo de notificación ("geofence_exit")
- `latitude`: float - Latitud del vehículo
- `longitude`: float - Longitud del vehículo
- `address`: Optional[str] - Dirección geocodificada

**No Requiere Cambios**: El modelo ya soporta todos los campos necesarios

---

### RouteDeviationWebhook (Existente)

**Campos Relevantes**:
- `deviation`: Dict[str, Any] - Información de la desviación
  - `distance_from_route_meters`: float - Distancia de la ruta (0 para salida de geocerca)
  - `current_location`: Dict[str, Any] - Ubicación actual del vehículo
- `wialon_source`: Dict[str, Any] - Fuente Wialon
  - `notification_id`: str - ID de la notificación
  - `notification_type`: str - Tipo de notificación

**No Requiere Cambios**: El modelo ya soporta todos los campos necesarios

---

## Constantes

### GEOFENCE_ROLES (Actualizar)

**Ubicación**: `app/core/constants.py`

**Valor Actual**:
```python
GEOFENCE_ROLES = {
    "ORIGIN": "origin",
    "LOADING": "loading",
    "UNLOADING": "unloading",
    "WAYPOINT": "waypoint",
    "DEPOT": "depot",
}
```

**Valor Actualizado**:
```python
GEOFENCE_ROLES = {
    "ORIGIN": "origin",
    "LOADING": "loading",
    "UNLOADING": "unloading",
    "WAYPOINT": "waypoint",
    "DEPOT": "depot",
    "ROUTE": "route",  # NUEVO
}
```

---

### ROUTE_DEVIATION_GRACE_PERIOD (Nuevo)

**Ubicación**: `app/core/constants.py`

**Valor**:
```python
ROUTE_DEVIATION_GRACE_PERIOD = 300  # 5 minutos en segundos
```

**Configuración**:
- Valor por defecto: 300 segundos (5 minutos)
- Configurable mediante variable de entorno: `ROUTE_DEVIATION_GRACE_PERIOD`
- Usar valor de configuración si está disponible, si no, usar constante

---

## Flujo de Datos

### Flujo de Detección de Desviación

1. **Evento Wialon** → `EventService.process_event()`
   - Recibe evento `geofence_exit` con `geofence_id`
   
2. **Consulta de Role** → `EventService._determine_action()`
   - Consulta `trip_geofences` para obtener `visit_type`
   - Si no se encuentra, usa detección por nombre
   
3. **Detección de Desviación** → `EventService._determine_action()`
   - Si `visit_type` = "route" y `notification_type` = "geofence_exit"
   - Establece `action["send_notification"] = True`
   - Establece `action["notification_message"] = "⚠️ Desviación de ruta detectada..."
   
4. **Verificación de Período de Gracia** → `EventService._check_grace_period()`
   - Verifica si han pasado 5 minutos desde la última notificación
   - Si no han pasado, no envía notificación (pero sí webhooks)
   
5. **Envío de Notificación** → `NotificationService.send_trip_notification()`
   - Envía mensaje WhatsApp al grupo del viaje
   - Registra timestamp en memoria
   
6. **Envío de Webhooks** → `EventService._send_webhooks_for_event()`
   - Envía webhook `geofence_transition` (siempre)
   - Envía webhook `route_deviation` (si es geocerca de ruta)
   
7. **Registro de Evento** → `EventRepository.create()`
   - Registra evento en la BD con `event_type` = "geofence_exit"
   - Marca evento como procesado

---

## Consideraciones de Performance

### Consultas a BD

**Impacto**: Mínimo
- La consulta de `visit_type` ya está optimizada con índices
- La consulta es O(1) con índices en `trip_id` y `geofence_id`
- No se requieren consultas adicionales

### Almacenamiento en Memoria

**Impacto**: Mínimo
- Almacenamiento en memoria para período de gracia es O(1)
- Tamaño: O(n) donde n = número de viajes activos
- Limpieza periódica de entradas antiguas (cada 1 hora)

### Envío de Webhooks

**Impacto**: Mínimo
- Webhooks se envían asincrónicamente
- Retry logic ya implementado en `WebhookService`
- Timeout configurado en `WebhookService`

---

## Testing

### Datos de Prueba

**Geocerca de Ruta**:
- `visit_type` = "route"
- `geofence_name` = "RUTA"
- `geofence_id` = "1003" (ejemplo)

**Evento de Salida**:
- `notification_type` = "geofence_exit"
- `geofence_id` = "1003"
- `geofence_name` = "RUTA"
- `latitude` = 20.9234
- `longitude` = -102.1567
- `address` = "Carretera Alterna (fuera de RUTA)"

**Resultado Esperado**:
- Notificación WhatsApp enviada
- Webhooks `geofence_transition` y `route_deviation` enviados
- Evento registrado en BD
- Estado del viaje NO cambia

---

## Seguridad

### Validación de Input

**Evento Wialon**:
- Validar `geofence_id` y `geofence_name` del evento
- Usar parámetros preparados en consultas SQL (ya implementado)
- Validar que el evento esté asociado a un viaje activo

### SQL Injection

**Protección**: Ya implementada
- Usar parámetros preparados en todas las consultas SQL
- No concatenar valores directamente en queries

### Rate Limiting

**Protección**: Período de gracia
- Previene spam de notificaciones
- Limita notificaciones a una cada 5 minutos por viaje
- Webhooks no están sujetos a período de gracia

---

## Observabilidad

### Logging

**Eventos a Registrar**:
- Detección de desviación de ruta: `route_deviation_detected`
- Envío de notificación: `route_deviation_notification_sent`
- Bloqueo por período de gracia: `route_deviation_notification_blocked`
- Envío de webhook: `route_deviation_webhook_sent`
- Error en envío de webhook: `route_deviation_webhook_error`
- Uso de fallback por nombre: `route_deviation_fallback_used`

### Métricas

**Métricas a Recolectar**:
- Número de desviaciones de ruta detectadas
- Número de notificaciones enviadas
- Número de notificaciones bloqueadas por período de gracia
- Número de webhooks `route_deviation` enviados
- Tiempo de procesamiento de eventos de desviación
- Tasa de error en envío de webhooks

---

## Conclusión

El modelo de datos actual soporta la funcionalidad de detección de desviación de ruta sin requerir cambios en la base de datos. Solo se requiere:

1. Agregar "route" a las constantes `GEOFENCE_ROLES`
2. Agregar constante `ROUTE_DEVIATION_GRACE_PERIOD`
3. Implementar lógica de detección de desviación en `EventService`
4. Implementar período de gracia para notificaciones
5. Integrar envío de webhook `route_deviation` cuando se detecta desviación

No se requieren migraciones de base de datos ni cambios en los modelos existentes.


# Research: Detección de Desviación de Ruta mediante Geocercas

## Decisiones Técnicas

### 1. Identificación del Role de Geocerca

**Decisión**: Usar el campo `visit_type` de la tabla `trip_geofences` para identificar el role de la geocerca.

**Rationale**: 
- El código actual ya consulta `visit_type` desde `trip_geofences` (línea 478 de `event_service.py`)
- La base de datos MySQL usa `visit_type` como columna en `trip_geofences`
- El payload de creación de viaje incluye `role` que se mapea a `visit_type` en la BD
- Mantiene consistencia con el código existente

**Alternatives Considered**:
- Crear una nueva columna `role` en `trip_geofences`: Rechazado porque requeriría migración de BD y el campo `visit_type` ya existe
- Usar solo detección por nombre: Rechazado porque es menos confiable que consultar desde BD

**Implementación**:
- Consultar `visit_type` desde `trip_geofences` usando `geofence_id`
- Si no se encuentra en BD, usar detección por nombre como fallback
- Agregar "route" a las constantes `GEOFENCE_ROLES` en `constants.py`

---

### 2. Período de Gracia para Notificaciones

**Decisión**: Implementar período de gracia de 5 minutos (configurable) usando almacenamiento en memoria (dict) o base de datos.

**Rationale**:
- Previene notificaciones duplicadas cuando el vehículo entra y sale rápidamente
- 5 minutos es un balance razonable entre evitar spam y no perder alertas importantes
- Debe ser configurable para ajustar según necesidades operativas
- Solo aplica a notificaciones WhatsApp, no a webhooks (los webhooks siempre se envían)

**Alternatives Considered**:
- Usar base de datos para tracking: Rechazado por overhead y complejidad innecesaria
- Usar Redis para tracking: Rechazado porque agregaría dependencia externa
- Sin período de gracia: Rechazado porque causaría spam de notificaciones

**Implementación**:
- Usar diccionario en memoria: `{trip_id: {last_notification_time: timestamp}}`
- Verificar si han pasado 5 minutos desde la última notificación de desviación para el mismo viaje
- Limpiar entradas antiguas periódicamente para evitar memory leak
- Hacer el período configurable mediante variable de entorno o constante

---

### 3. Estructura del Webhook route_deviation

**Decisión**: Usar el método `send_route_deviation` existente en `WebhookService` con distancia en metros = 0.

**Rationale**:
- El método `send_route_deviation` ya existe en `WebhookService` (línea 762)
- La especificación establece que no se requiere cálculo de distancia
- Usar 0 metros indica que se detectó desviación pero no se calculó distancia específica
- Mantiene la estructura del webhook existente sin cambios

**Alternatives Considered**:
- Calcular distancia al borde de la geocerca: Rechazado porque no es necesario según especificación
- Crear nuevo tipo de webhook: Rechazado porque `route_deviation` ya existe y es apropiado
- No enviar webhook route_deviation: Rechazado porque la especificación requiere enviarlo

**Implementación**:
- Llamar a `send_route_deviation` con `distance_meters=0`
- Incluir información de la geocerca de la cual salió el vehículo
- Incluir ubicación actual del vehículo
- Mantener estructura del webhook según `RouteDeviationWebhook` model

---

### 4. Formato del Mensaje WhatsApp

**Decisión**: Usar formato: "⚠️ Desviación de ruta detectada. El vehículo salió de [nombre_geocerca]. Ubicación actual: [dirección]"

**Rationale**:
- Formato claro e informativo según especificación
- Incluye información relevante: nombre de geocerca y ubicación actual
- Sigue el patrón de otras notificaciones del sistema
- Usa emoji para destacar la importancia (⚠️)

**Alternatives Considered**:
- Mensaje más breve: Rechazado porque perdería información importante
- Mensaje con acción requerida: Rechazado porque la especificación no requiere acción del operador
- Sin emoji: Rechazado porque el emoji ayuda a destacar la alerta

**Implementación**:
- Formatear mensaje en `EventService._determine_action()` cuando se detecta salida de geocerca de ruta
- Usar `event.geofence_name` para nombre de geocerca
- Usar `event.address` para ubicación actual
- Enviar mediante `NotificationService.send_trip_notification()`

---

### 5. No Cambiar Estado del Viaje

**Decisión**: No cambiar el estado del viaje cuando se detecta desviación de ruta.

**Rationale**:
- La especificación establece explícitamente que no se debe cambiar el estado
- La desviación de ruta es un evento, no un cambio de fase del viaje
- El viaje mantiene su estado actual (ej: "en_ruta_destino", "en_ruta_carga")
- Diferente a geocercas de carga/descarga que sí cambian el estado

**Alternatives Considered**:
- Cambiar estado a "en_desviacion": Rechazado porque la especificación no lo requiere
- Cambiar substatus: Rechazado porque la especificación establece que no se cambia el estado
- Registrar desviación en metadata: Considerado pero no necesario para cumplir requisitos

**Implementación**:
- En `EventService._determine_action()`, cuando se detecta salida de geocerca de ruta, NO establecer `action["update_status"] = True`
- Solo establecer `action["send_notification"] = True` y `action["notification_message"]`
- Mantener el estado actual del viaje sin cambios

---

### 6. Envío de Doble Webhook

**Decisión**: Enviar tanto `geofence_transition` como `route_deviation` cuando se detecta salida de geocerca de ruta.

**Rationale**:
- Mantiene consistencia con el sistema existente (todas las geocercas envían `geofence_transition`)
- Permite a Flowtify procesar ambos tipos de eventos según sus necesidades
- `geofence_transition` proporciona información general de entrada/salida
- `route_deviation` proporciona información específica de desviación de ruta

**Alternatives Considered**:
- Solo enviar `route_deviation`: Rechazado porque rompería la consistencia del sistema
- Solo enviar `geofence_transition`: Rechazado porque no cumpliría con el requisito de enviar `route_deviation`
- Crear webhook combinado: Rechazado porque requeriría cambios en la estructura existente

**Implementación**:
- En `EventService._send_webhooks_for_event()`, cuando es salida de geocerca de ruta, enviar ambos webhooks
- Primero enviar `geofence_transition` (comportamiento existente)
- Luego enviar `route_deviation` (nuevo comportamiento)
- Si falla el envío de `route_deviation`, no afectar el envío de `geofence_transition`

---

### 7. Detección por Nombre (Fallback)

**Decisión**: Implementar detección por nombre como fallback cuando no se encuentra el role en BD.

**Rationale**:
- Proporciona resiliencia cuando hay problemas con la BD o datos faltantes
- El código actual ya tiene detección por nombre para carga/descarga (líneas 348-371)
- Buscar palabras clave como "ruta", "route" en el nombre de la geocerca
- Mantiene consistencia con el patrón existente

**Alternatives Considered**:
- No implementar fallback: Rechazado porque reduciría la resiliencia del sistema
- Usar solo detección por nombre: Rechazado porque la consulta a BD es más confiable
- Lanzar error si no se encuentra role: Rechazado porque causaría fallos innecesarios

**Implementación**:
- Si `visit_type` es None o "unknown" después de consultar BD, usar detección por nombre
- Buscar palabras clave: "ruta", "route" en `event.geofence_name.lower()`
- Si se encuentra, establecer `geofence_role = "route"`
- Registrar en logs cuando se usa fallback para debugging

---

### 8. Manejo de Errores

**Decisión**: Si falla el envío del webhook `route_deviation`, no afectar el envío del webhook `geofence_transition`.

**Rationale**:
- Mantiene la funcionalidad existente funcionando incluso si hay problemas con la nueva funcionalidad
- El webhook `geofence_transition` es crítico para el funcionamiento del sistema
- El webhook `route_deviation` es adicional y no debe romper el flujo principal
- Sigue el principio de no romper funcionalidad existente

**Alternatives Considered**:
- Fallar ambos webhooks si uno falla: Rechazado porque rompería la funcionalidad existente
- Reintentar ambos webhooks: Rechazado porque el `WebhookService` ya tiene retry logic
- No enviar `geofence_transition` si falla `route_deviation`: Rechazado porque rompería funcionalidad existente

**Implementación**:
- Envolver el envío de `route_deviation` en try-except
- Loggear errores pero continuar con el flujo normal
- Asegurar que `geofence_transition` siempre se envíe independientemente del resultado de `route_deviation`
- Usar logging estructurado para debugging

---

## Tecnologías y Patrones

### Python Async/Await
- **Uso**: Todos los métodos del `EventService` son async
- **Patrón**: Usar `async/await` para operaciones de BD y webhooks
- **Justificación**: Mantiene consistencia con el código existente

### Database Queries
- **Uso**: Consultar `trip_geofences` para obtener `visit_type`
- **Patrón**: Usar `db.fetchval()` para consultas simples
- **Justificación**: Patrón existente en el código (línea 476)

### Error Handling
- **Uso**: Try-except para manejar errores en envío de webhooks
- **Patrón**: Loggear errores pero continuar con el flujo
- **Justificación**: No romper funcionalidad existente

### Configuration
- **Uso**: Período de gracia configurable (variable de entorno o constante)
- **Patrón**: Valor por defecto de 5 minutos, configurable mediante `app.config`
- **Justificación**: Flexibilidad para ajustar según necesidades operativas

---

## Dependencias Externas

### Wialon Events
- **Tipo**: Eventos `geofence_exit` con `geofence_id`
- **Formato**: Form-urlencoded según código existente
- **Campos requeridos**: `geofence_id`, `geofence_name`, `latitude`, `longitude`, `address`

### WebhookService
- **Método**: `send_route_deviation(event_id, trip_id, deviation_data)`
- **Estado**: Ya existe en el código (línea 762)
- **Uso**: Llamar con `distance_meters=0` y datos de geocerca

### NotificationService
- **Método**: `send_trip_notification(trip_id, message)`
- **Estado**: Ya existe en el código (línea 27)
- **Uso**: Enviar mensaje formateado cuando se detecta desviación

### Database
- **Tabla**: `trip_geofences`
- **Columna**: `visit_type` (mapeado a `role` en la especificación)
- **Consulta**: JOIN con `geofences` usando `geofence_id`

---

## Consideraciones de Performance

### Consultas a BD
- **Impacto**: Mínimo, ya se hace consulta similar para otras geocercas
- **Optimización**: La consulta ya tiene índices en `trip_id` y `geofence_id`
- **Caching**: No necesario, los datos cambian por viaje

### Período de Gracia
- **Almacenamiento**: Diccionario en memoria
- **Tamaño**: O(n) donde n = número de viajes activos
- **Limpieza**: Limpiar entradas después de 1 hora de inactividad

### Envío de Webhooks
- **Impacto**: Mínimo, webhooks se envían asincrónicamente
- **Retry**: Ya manejado por `WebhookService`
- **Timeout**: Configurado en `WebhookService`

---

## Testing

### Unit Tests
- **Cobertura**: `EventService._determine_action()` para detección de role "route"
- **Cobertura**: `EventService._send_webhooks_for_event()` para envío de webhooks
- **Cobertura**: Período de gracia para notificaciones

### Integration Tests
- **Cobertura**: Flujo completo desde evento Wialon hasta webhook y notificación
- **Cobertura**: Comportamiento con y sin período de gracia
- **Cobertura**: Fallback a detección por nombre

### E2E Tests
- **Cobertura**: Escenario completo de salida de geocerca de ruta
- **Cobertura**: Múltiples salidas dentro del período de gracia
- **Cobertura**: Entrada a geocerca de ruta después de desviación

---

## Seguridad

### Validación de Datos
- **Input**: Validar `geofence_id` y `geofence_name` del evento Wialon
- **SQL Injection**: Usar parámetros preparados (ya implementado)
- **XSS**: No aplica, datos no se renderizan en HTML

### Rate Limiting
- **Notificaciones**: Período de gracia previene spam
- **Webhooks**: Ya manejado por `WebhookService` con retry logic
- **BD**: Consultas limitadas por índices y timeouts

---

## Observabilidad

### Logging
- **Eventos**: Registrar cuando se detecta desviación de ruta
- **Webhooks**: Registrar envío de webhooks (ya implementado)
- **Errores**: Registrar errores en envío de webhooks o notificaciones
- **Fallback**: Registrar cuando se usa detección por nombre

### Métricas
- **Contador**: Número de desviaciones de ruta detectadas
- **Contador**: Número de notificaciones enviadas (vs bloqueadas por período de gracia)
- **Contador**: Número de webhooks `route_deviation` enviados
- **Tiempo**: Tiempo de procesamiento de eventos de desviación

---

## Conclusión

Todas las decisiones técnicas están alineadas con:
- La especificación de la funcionalidad
- El código existente y sus patrones
- Las mejores prácticas de Python async
- Los requisitos de performance y observabilidad

No se requieren cambios en la base de datos ni en las estructuras de datos existentes. La implementación se integra de manera consistente con el sistema actual.


# Tareas de Implementación: Detección de Desviación de Ruta mediante Geocercas

## Resumen

Este documento detalla las tareas concretas y accionables para implementar la detección automática de desviación de ruta cuando un vehículo sale de una geocerca con role "route".

## Fases de Implementación

### Fase 1: Preparación y Configuración
**Tiempo estimado**: 10 minutos
**Dependencias**: Ninguna

#### Tarea 1.1: Agregar constante ROUTE a GEOFENCE_ROLES
- **Archivo**: `app/core/constants.py`
- **Línea**: ~41-47
- **Descripción**: Agregar "route" a `GEOFENCE_ROLES` y agregar constante para período de gracia
- **Criterios de Aceptación**:
  - [ ] `GEOFENCE_ROLES["ROUTE"] = "route"` agregado
  - [ ] `ROUTE_DEVIATION_GRACE_PERIOD = 300` agregado (5 minutos)
  - [ ] Constantes están correctamente definidas
- **Esfuerzo**: 5 minutos
- **Estado**: Pendiente

#### Tarea 1.2: Agregar configuración route_deviation_grace_period
- **Archivo**: `app/config.py`
- **Línea**: ~87 (después de `webhooks_enabled_tenants`)
- **Descripción**: Agregar configuración para período de gracia de notificaciones
- **Criterios de Aceptación**:
  - [ ] `route_deviation_grace_period: int = 300` agregado a clase `Settings`
  - [ ] Configuración es accesible desde `settings.route_deviation_grace_period`
  - [ ] Valor por defecto es 300 segundos (5 minutos)
- **Esfuerzo**: 5 minutos
- **Estado**: Pendiente

---

### Fase 2: Implementación de Detección y Período de Gracia
**Tiempo estimado**: 45 minutos
**Dependencias**: Fase 1 completada

#### Tarea 2.1: Agregar tracking de notificaciones en EventService
- **Archivo**: `app/services/event_service.py`
- **Línea**: ~33 (después de `self.webhook_service = webhook_service`)
- **Descripción**: Agregar diccionario para rastrear notificaciones de desviación de ruta
- **Criterios de Aceptación**:
  - [ ] `self._route_deviation_notifications = {}` agregado en `__init__`
  - [ ] Diccionario tiene estructura: `{trip_id: {"last_notification_time": timestamp}}`
  - [ ] Inicialización correcta sin errores
- **Esfuerzo**: 5 minutos
- **Estado**: Pendiente

#### Tarea 2.2: Implementar método _check_grace_period
- **Archivo**: `app/services/event_service.py`
- **Ubicación**: Después de `__init__` (antes de `process_wialon_event`)
- **Descripción**: Crear método para verificar si ha pasado el período de gracia
- **Criterios de Aceptación**:
  - [ ] Método `_check_grace_period(trip_id: str, grace_period_seconds: int = 300) -> bool` implementado
  - [ ] Método retorna `True` si se puede enviar notificación, `False` si está en período de gracia
  - [ ] Método actualiza timestamp cuando se permite notificación
  - [ ] Método llama a `_cleanup_old_notifications()` para limpiar entradas antiguas
  - [ ] Método registra logs apropiados (`route_deviation_notification_allowed`, `route_deviation_notification_blocked`)
- **Esfuerzo**: 15 minutos
- **Estado**: Pendiente

#### Tarea 2.3: Implementar método _cleanup_old_notifications
- **Archivo**: `app/services/event_service.py`
- **Ubicación**: Después de `_check_grace_period`
- **Descripción**: Crear método para limpiar entradas antiguas del tracking de notificaciones
- **Criterios de Aceptación**:
  - [ ] Método `_cleanup_old_notifications(max_age_seconds: int = 3600)` implementado
  - [ ] Método elimina entradas con edad mayor a `max_age_seconds` (default: 1 hora)
  - [ ] Método registra logs cuando limpia entradas (`route_deviation_notifications_cleaned`)
  - [ ] Método no lanza excepciones si hay errores
- **Esfuerzo**: 10 minutos
- **Estado**: Pendiente

#### Tarea 2.4: Actualizar _determine_action para detectar salida de geocerca de ruta
- **Archivo**: `app/services/event_service.py`
- **Línea**: ~374 (en el bloque `elif event.notification_type == WIALON_EVENT_TYPES["GEOFENCE_EXIT"]:`)
- **Descripción**: Agregar lógica para detectar salida de geocerca de ruta y enviar notificación con período de gracia
- **Criterios de Aceptación**:
  - [ ] Se consulta el role de la geocerca desde la BD usando `geofence_id`
  - [ ] Si `geofence_role == "route"`, se detecta como desviación de ruta
  - [ ] Se verifica período de gracia antes de enviar notificación
  - [ ] Si período de gracia permite, se configura `action["send_notification"] = True`
  - [ ] Mensaje de notificación usa formato: "⚠️ Desviación de ruta detectada. El vehículo salió de {event.geofence_name}. Ubicación actual: {event.address or 'No disponible'}"
  - [ ] NO se cambia el estado del viaje (`action["update_status"]` no se establece)
  - [ ] Se registra log cuando se detecta desviación (`route_deviation_detected`)
  - [ ] Se registra log cuando se bloquea notificación por período de gracia (`route_deviation_notification_blocked_by_grace_period`)
  - [ ] Fallback a detección por nombre funciona (busca "ruta" o "route" en nombre)
  - [ ] Fallback también respeta período de gracia
  - [ ] Se registra log cuando se usa fallback (`route_deviation_detected_by_name_fallback`)
- **Esfuerzo**: 20 minutos
- **Estado**: Pendiente

---

### Fase 3: Implementación de Webhooks
**Tiempo estimado**: 25 minutos
**Dependencias**: Fase 2 completada

#### Tarea 3.1: Actualizar _send_webhooks_for_event para detectar geocerca de ruta
- **Archivo**: `app/services/event_service.py`
- **Línea**: ~473-516 (en el bloque de `GEOFENCE_ENTRY`/`GEOFENCE_EXIT`)
- **Descripción**: Agregar detección de geocerca de ruta en la sección de webhooks y fallback por nombre. Actualizar consulta para obtener `geofence_type` desde BD.
- **Criterios de Aceptación**:
  - [ ] Se actualiza la consulta para usar `fetchrow` en lugar de `fetchval` para obtener tanto `visit_type` como `geofence_type`
  - [ ] Se consulta `tg.visit_type` y `g.geofence_type` desde la BD (MySQL)
  - [ ] Si no se encuentra role en BD, se usa fallback por nombre (busca "ruta" o "route")
  - [ ] El role se asigna correctamente a `geofence_role`
  - [ ] El tipo de geocerca se asigna correctamente a `geofence_type` (obtenido desde BD o default "polygon")
  - [ ] Se mantiene el envío del webhook `geofence_transition` para todas las geocercas
- **Esfuerzo**: 10 minutos
- **Estado**: Pendiente

#### Tarea 3.2: Agregar envío de webhook route_deviation para salidas de geocerca de ruta
- **Archivo**: `app/services/event_service.py`
- **Línea**: ~516 (después de enviar `geofence_transition`)
- **Descripción**: Agregar lógica para enviar webhook `route_deviation` cuando es salida de geocerca de ruta
- **Criterios de Aceptación**:
  - [ ] Se verifica que `transition_type == "exit"` y `geofence_role == "route"`
  - [ ] Se construye `deviation_data` con estructura correcta:
    - [ ] `distance_meters = 0` (no se calcula distancia)
    - [ ] `max_allowed = 100` (valor por defecto)
    - [ ] `duration_seconds = 0` (no se calcula duración)
    - [ ] `notification_id = event.notification_id`
    - [ ] `external_id = f"wialon_route_dev_{event.unit_id}_{event.event_time}"`
    - [ ] `current_location` con `latitude`, `longitude`, `address`
    - [ ] `nearest_point = {}` (vacío porque no se calcula)
  - [ ] Se llama a `self.webhook_service.send_route_deviation()` con parámetros correctos
  - [ ] Se registra log cuando se envía webhook (`route_deviation_webhook_sent`)
  - [ ] Si falla el envío, se registra error (`route_deviation_webhook_failed`) pero NO se lanza excepción
  - [ ] El fallo del webhook `route_deviation` NO afecta el envío de `geofence_transition`
  - [ ] Webhook se envía independientemente del período de gracia (siempre se envía)
  - [ ] `geofence_type` se obtiene correctamente desde BD (no hardcodeado)
- **Esfuerzo**: 15 minutos
- **Estado**: Pendiente

---

### Fase 4: Testing
**Tiempo estimado**: 45 minutos
**Dependencias**: Fases 1-3 completadas

#### Tarea 4.1: Crear test unitario para detección de desviación de ruta
- **Archivo**: `tests/services/test_event_service.py` (o crear nuevo archivo)
- **Descripción**: Crear tests para verificar detección de desviación de ruta
- **Criterios de Aceptación**:
  - [ ] Test que verifica detección cuando `visit_type = "route"` en BD
  - [ ] Test que verifica detección por nombre (fallback) cuando nombre contiene "ruta" o "route"
  - [ ] Test que verifica que NO se cambia el estado del viaje
  - [ ] Test que verifica que se configura `action["send_notification"] = True`
  - [ ] Test que verifica que el mensaje de notificación tiene formato correcto
  - [ ] Todos los tests pasan
- **Esfuerzo**: 15 minutos
- **Estado**: Pendiente

#### Tarea 4.2: Crear test unitario para período de gracia
- **Archivo**: `tests/services/test_event_service.py`
- **Descripción**: Crear tests para verificar funcionamiento del período de gracia
- **Criterios de Aceptación**:
  - [ ] Test que verifica que se envía primera notificación
  - [ ] Test que verifica que NO se envía segunda notificación dentro del período de gracia
  - [ ] Test que verifica que SÍ se envía notificación después del período de gracia
  - [ ] Test que verifica que los webhooks siempre se envían (no afectados por período de gracia)
  - [ ] Test que verifica limpieza de entradas antiguas
  - [ ] Todos los tests pasan
- **Esfuerzo**: 15 minutos
- **Estado**: Pendiente

#### Tarea 4.3: Crear test unitario para webhook route_deviation
- **Archivo**: `tests/services/test_event_service.py`
- **Descripción**: Crear tests para verificar envío de webhook `route_deviation`
- **Criterios de Aceptación**:
  - [ ] Test que verifica que se envía webhook `route_deviation` cuando sale de geocerca de ruta
  - [ ] Test que verifica que se envía webhook `geofence_transition` también
  - [ ] Test que verifica que si falla `route_deviation`, NO afecta `geofence_transition`
  - [ ] Test que verifica que `distance_meters = 0` en `deviation_data`
  - [ ] Test que verifica estructura correcta de `deviation_data`
  - [ ] Test que verifica que `geofence_type` se obtiene correctamente desde BD
  - [ ] Test que verifica que `geofence_type` tiene valor correcto (no hardcodeado como "polygon")
  - [ ] Todos los tests pasan
- **Esfuerzo**: 10 minutos
- **Estado**: Pendiente

#### Tarea 4.4: Crear test de integración para flujo completo
- **Archivo**: `tests/test_webhook_integration_e2e.py` (o crear nuevo archivo)
- **Descripción**: Crear test de integración para flujo completo desde evento Wialon hasta webhook
- **Criterios de Aceptación**:
  - [ ] Test que procesa evento Wialon de salida de geocerca de ruta
  - [ ] Test que verifica que se envía notificación WhatsApp (si período de gracia lo permite)
  - [ ] Test que verifica que se envían ambos webhooks (`geofence_transition` y `route_deviation`)
  - [ ] Test que verifica que se registra evento en BD
  - [ ] Test que verifica que NO se cambia estado del viaje
  - [ ] Test pasa correctamente
- **Esfuerzo**: 15 minutos
- **Estado**: Pendiente

---

### Fase 5: Verificación y Documentación
**Tiempo estimado**: 20 minutos
**Dependencias**: Fases 1-4 completadas

#### Tarea 5.1: Verificar funcionalidad existente no se rompió
- **Archivo**: N/A (verificación manual)
- **Descripción**: Ejecutar tests existentes para verificar que no se rompió funcionalidad
- **Criterios de Aceptación**:
  - [ ] Tests existentes para geocercas de carga/descarga pasan
  - [ ] Tests existentes para webhooks `geofence_transition` pasan
  - [ ] No se introdujeron regresiones
  - [ ] Comportamiento existente se mantiene intacto
- **Esfuerzo**: 10 minutos
- **Estado**: Pendiente

#### Tarea 5.2: Verificación manual con viaje de prueba
- **Archivo**: N/A (verificación manual)
- **Descripción**: Crear viaje de prueba con geocerca de ruta y simular eventos. Verificar criterios de éxito medibles y cualitativos.
- **Criterios de Aceptación**:
  - [ ] Se crea viaje de prueba con geocerca de ruta (role="route")
  - [ ] Se simula evento `geofence_exit` para geocerca de ruta
  - [ ] Se verifica que se envía notificación WhatsApp con formato correcto
  - [ ] Se verifica que se envían ambos webhooks
  - [ ] Se verifica que NO se cambia el estado del viaje
  - [ ] Se verifica que el período de gracia funciona correctamente (no envía notificación duplicada)
  - [ ] Se verifica que los webhooks siempre se envían (no afectados por período de gracia)
  - [ ] Se verifica que `geofence_type` se obtiene correctamente desde BD (no hardcodeado)
  - [ ] **Criterios de Éxito Medibles**:
    - [ ] 100% de las salidas de geocercas de ruta son detectadas como desviaciones de ruta
    - [ ] 100% de las desviaciones de ruta generan notificaciones WhatsApp (respetando período de gracia)
    - [ ] 100% de las desviaciones de ruta generan webhooks `route_deviation` a Flowtify
    - [ ] El procesamiento de eventos de desviación de ruta se completa en menos de 2 segundos
    - [ ] 100% de los webhooks `route_deviation` incluyen información correcta de la geocerca
  - [ ] **Criterios de Éxito Cualitativos**:
    - [ ] Las notificaciones WhatsApp son claras y accionables para el operador
    - [ ] La funcionalidad se integra de manera consistente con el sistema existente
    - [ ] El código es fácil de mantener y extender para futuras geocercas
    - [ ] No se rompe la funcionalidad existente de geocercas de carga/descarga
- **Esfuerzo**: 10 minutos
- **Estado**: Pendiente

---

## Checklist de Verificación Final

### Funcionalidad Core
- [ ] Constantes actualizadas (`GEOFENCE_ROLES` incluye "route")
- [ ] Configuración actualizada (`route_deviation_grace_period` agregado)
- [ ] Detección de desviación implementada en `_determine_action()`
- [ ] Período de gracia implementado (`_check_grace_period()`)
- [ ] Limpieza de memoria implementada (`_cleanup_old_notifications()`)
- [ ] Webhook `route_deviation` enviado en `_send_webhooks_for_event()`

### Comportamiento Esperado
- [ ] Estado del viaje NO cambia cuando se detecta desviación
- [ ] Notificación WhatsApp enviada con formato correcto
- [ ] Período de gracia previene notificaciones duplicadas
- [ ] Webhooks siempre se envían (no afectados por período de gracia)
- [ ] Fallback a detección por nombre funciona
- [ ] Manejo de errores implementado (no afecta envío de `geofence_transition`)

### Testing
- [ ] Tests unitarios pasan
- [ ] Tests de integración pasan
- [ ] Tests existentes no se rompieron
- [ ] Verificación manual exitosa

### Logging y Monitoreo
- [ ] Logs apropiados registrados (`route_deviation_detected`, `route_deviation_notification_allowed`, etc.)
- [ ] Errores registrados correctamente (`route_deviation_webhook_failed`)
- [ ] Logs son útiles para debugging

---

## Orden de Ejecución Recomendado

1. **Fase 1**: Preparación y Configuración (10 min)
   - Tarea 1.1: Agregar constante ROUTE
   - Tarea 1.2: Agregar configuración grace period

2. **Fase 2**: Implementación de Detección (45 min)
   - Tarea 2.1: Agregar tracking de notificaciones
   - Tarea 2.2: Implementar _check_grace_period
   - Tarea 2.3: Implementar _cleanup_old_notifications
   - Tarea 2.4: Actualizar _determine_action

3. **Fase 3**: Implementación de Webhooks (25 min)
   - Tarea 3.1: Actualizar detección de geocerca de ruta en webhooks
   - Tarea 3.2: Agregar envío de webhook route_deviation

4. **Fase 4**: Testing (45 min)
   - Tarea 4.1: Test unitario de detección
   - Tarea 4.2: Test unitario de período de gracia
   - Tarea 4.3: Test unitario de webhook
   - Tarea 4.4: Test de integración

5. **Fase 5**: Verificación (20 min)
   - Tarea 5.1: Verificar funcionalidad existente
   - Tarea 5.2: Verificación manual

**Tiempo total estimado**: ~145 minutos (2 horas 25 minutos)

---

## Notas de Implementación

### Consideraciones Importantes

1. **Base de Datos**: El sistema usa **únicamente MySQL**. El campo `visit_type` en `trip_geofences` y `geofence_type` en `geofences` están disponibles en MySQL. Usar `fetchrow` para obtener ambos campos en una sola consulta.

2. **Período de Gracia**: Solo aplica a notificaciones WhatsApp, NO a webhooks. Los webhooks siempre se envían.

3. **Estado del Viaje**: NO se debe cambiar el estado del viaje cuando se detecta desviación de ruta. Solo se envían notificaciones y webhooks.

4. **Detección de Role**: Primero intentar obtener el role desde la BD usando `visit_type` desde `trip_geofences` (MySQL). Si no se encuentra, usar detección por nombre como fallback.

5. **Tipo de Geocerca**: Obtener `geofence_type` desde la tabla `geofences` usando JOIN con `trip_geofences`. Usar `fetchrow` para obtener tanto `visit_type` como `geofence_type` en una sola consulta. Si no se encuentra, usar "polygon" como default.

6. **Manejo de Errores**: Si falla el envío del webhook `route_deviation`, NO debe afectar el envío del webhook `geofence_transition`. Usar try-except para aislar errores.

7. **Limpieza de Memoria**: Implementar limpieza periódica de entradas antiguas para prevenir memory leaks.

8. **Retrocompatibilidad**: Asegurar que los cambios no rompen funcionalidad existente para geocercas de carga/descarga.

### Archivos a Modificar

1. `app/core/constants.py` - Agregar constantes
2. `app/config.py` - Agregar configuración
3. `app/services/event_service.py` - Implementar lógica principal
4. `tests/services/test_event_service.py` - Agregar tests (o crear nuevo archivo)
5. `tests/test_webhook_integration_e2e.py` - Agregar test de integración (o crear nuevo archivo)

### Archivos que NO se Modifican

- `app/services/webhook_service.py` - Ya tiene método `send_route_deviation()` implementado
- `app/models/webhooks.py` - Ya tiene modelo `RouteDeviationWebhook` definido
- `app/repositories/*.py` - No requieren cambios
- `app/models/event.py` - No requiere cambios

---

## Referencias

- **Especificación**: `specs/1-route-deviation-geofence/spec.md`
- **Plan de Implementación**: `specs/1-route-deviation-geofence/plan/implementation-plan.md`
- **Quickstart**: `specs/1-route-deviation-geofence/plan/quickstart.md`
- **Data Model**: `specs/1-route-deviation-geofence/plan/data-model.md`

---

## Seguimiento de Progreso

### Resumen por Fase

- **Fase 1**: 0/2 tareas completadas (0%)
- **Fase 2**: 0/4 tareas completadas (0%)
- **Fase 3**: 0/2 tareas completadas (0%)
- **Fase 4**: 0/4 tareas completadas (0%)
- **Fase 5**: 0/2 tareas completadas (0%)

**Total**: 0/14 tareas completadas (0%)

### Próximos Pasos

1. Comenzar con Fase 1 (Preparación y Configuración)
2. Continuar con Fase 2 (Implementación de Detección)
3. Proceder con Fase 3 (Implementación de Webhooks)
4. Ejecutar Fase 4 (Testing)
5. Finalizar con Fase 5 (Verificación)

---

## Preguntas y Respuestas

### ¿Qué hacer si falla una tarea?

1. Revisar los criterios de aceptación
2. Verificar que se cumplen todos los requisitos
3. Ejecutar tests para identificar el problema
4. Revisar logs para más información
5. Consultar la especificación si hay dudas

### ¿Cómo verificar que una tarea está completa?

1. Revisar que se cumplen todos los criterios de aceptación
2. Ejecutar tests relacionados
3. Verificar que no se introdujeron regresiones
4. Revisar código para asegurar calidad

### ¿Qué hacer si se encuentra un problema durante la implementación?

1. Documentar el problema
2. Evaluar si afecta otras tareas
3. Buscar solución en la especificación o plan
4. Si es necesario, ajustar la tarea o crear nueva tarea
5. Continuar con la implementación

---

## Historial de Cambios

- **2025-01-27**: Documento creado con 14 tareas organizadas en 5 fases
- **TBD**: Actualizar con progreso de implementación


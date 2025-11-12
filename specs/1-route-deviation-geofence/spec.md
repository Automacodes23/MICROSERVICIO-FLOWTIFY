# Especificación: Detección de Desviación de Ruta mediante Geocercas

## Resumen

Implementar detección automática de desviación de ruta cuando un vehículo sale de una geocerca con role "route". Actualmente, el sistema espera que la desviación de ruta sea una notificación separada de Wialon, pero debe detectarse automáticamente como una salida de geocerca.

## Contexto

En el payload de creación de viaje, se incluye una geocerca con role "route" que representa la ruta ideal que debe seguir el operador. El sistema debe detectar cuando el vehículo:
- **Entra** a la geocerca de ruta: Todo está correcto (comportamiento normal)
- **Sale** de la geocerca de ruta: Se considera desviación de ruta y debe generar notificaciones y webhooks

Esta funcionalidad debe funcionar de manera similar a las notificaciones de entrada y salida de geocercas de carga y descarga que ya se manejan en el sistema.

## Actores

- **Sistema de Wialon**: Envía eventos de entrada y salida de geocercas
- **EventService**: Procesa eventos de Wialon y determina acciones
- **WebhookService**: Envía webhooks a Flowtify
- **NotificationService**: Envía notificaciones WhatsApp
- **Operador/Supervisor**: Recibe alertas de desviación de ruta

## Requisitos Funcionales

### RF1: Detección de Salida de Geocerca de Ruta

**Descripción**: El sistema debe detectar cuando un vehículo sale de una geocerca con role "route" y tratarlo como desviación de ruta.

**Criterios de Aceptación**:
- Cuando ocurre un evento `geofence_exit` de Wialon para una geocerca con role "route", se debe considerar como desviación de ruta
- El sistema debe identificar correctamente el role de la geocerca desde la base de datos
- La detección debe funcionar tanto si el role se obtiene de la BD como si se detecta por nombre (fallback)
- El sistema NO debe cambiar el estado del viaje cuando se detecta desviación de ruta (solo envía notificaciones y webhooks)
- El viaje mantiene su estado actual (ej: "en_ruta_destino", "en_ruta_carga") independientemente de la desviación

### RF2: Notificación WhatsApp de Desviación

**Descripción**: Cuando se detecta una desviación de ruta, se debe enviar una notificación WhatsApp al grupo del viaje.

**Criterios de Aceptación**:
- Se envía un mensaje WhatsApp informando sobre la desviación de ruta
- El mensaje debe usar el formato: "⚠️ Desviación de ruta detectada. El vehículo salió de [nombre_geocerca]. Ubicación actual: [dirección]"
- El mensaje debe incluir el nombre de la geocerca de la cual salió el vehículo
- El mensaje debe incluir la dirección/ubicación actual del vehículo
- La notificación debe ser clara e informativa para el operador
- Se debe implementar un período de gracia (configurable, por defecto 5 minutos) para evitar notificaciones duplicadas
- Si el vehículo sale y vuelve a salir de la geocerca de ruta dentro del período de gracia, solo se envía una notificación (la primera)
- Los webhooks se envían en cada evento independientemente del período de gracia (solo las notificaciones WhatsApp están sujetas al período de gracia)

### RF3: Webhook de Desviación de Ruta

**Descripción**: Además del webhook `geofence_transition`, se debe enviar un webhook `route_deviation` a Flowtify cuando se detecta salida de geocerca de ruta.

**Criterios de Aceptación**:
- Se envía un webhook de tipo `route_deviation` a Flowtify
- El webhook debe incluir toda la información necesaria: ubicación actual, geocerca, viaje, conductor, unidad
- El webhook debe mantener la estructura definida en `RouteDeviationWebhook`
- El webhook debe incluir información sobre la geocerca de la cual salió el vehículo
- El cálculo de distancia de desviación no es necesario - solo se debe indicar que el vehículo salió de la geocerca (el campo de distancia puede ser 0 o el valor mínimo requerido por la estructura)
- Se debe mantener también el webhook `geofence_transition` para mantener consistencia

### RF4: Mantenimiento de Webhook Geofence Transition

**Descripción**: El sistema debe continuar enviando el webhook `geofence_transition` para todas las geocercas, incluyendo las de ruta.

**Criterios de Aceptación**:
- Se sigue enviando el webhook `geofence_transition` para entrada/salida de todas las geocercas
- El webhook `geofence_transition` debe incluir el role correcto de la geocerca
- Para geocercas de ruta, se deben enviar ambos webhooks: `geofence_transition` y `route_deviation`

### RF5: Identificación de Role de Geocerca

**Descripción**: El sistema debe identificar correctamente el role de una geocerca desde la base de datos o por nombre (fallback).

**Criterios de Aceptación**:
- Primero intenta obtener el role desde la tabla `trip_geofences` usando el `geofence_id`
- Si no encuentra el role en la BD, usa detección por nombre (fallback)
- La detección por nombre debe buscar palabras clave como "ruta", "route" en el nombre de la geocerca
- El role debe estar correctamente almacenado en el payload de creación de viaje

## Escenarios de Usuario

### Escenario 1: Salida de Geocerca de Ruta - Desviación Detectada

**Precondiciones**:
- Existe un viaje activo con una geocerca de ruta asignada (role="route")
- El vehículo está dentro de la geocerca de ruta
- El sistema está procesando eventos de Wialon

**Flujo**:
1. Wialon detecta que el vehículo salió de la geocerca de ruta
2. Wialon envía un evento `geofence_exit` con el `geofence_id` de la geocerca de ruta
3. El sistema procesa el evento y consulta el role de la geocerca en la BD
4. El sistema identifica que es una geocerca con role="route"
5. El sistema determina que es una desviación de ruta
6. El sistema envía una notificación WhatsApp al grupo del viaje con el formato: "⚠️ Desviación de ruta detectada. El vehículo salió de [nombre_geocerca]. Ubicación actual: [dirección]"
7. El sistema envía un webhook `geofence_transition` a Flowtify
8. El sistema envía un webhook `route_deviation` a Flowtify

**Resultado Esperado**:
- Se envía notificación WhatsApp informando sobre la desviación con nombre de geocerca y ubicación actual
- Se envían ambos webhooks (`geofence_transition` y `route_deviation`) a Flowtify
- El evento queda registrado en la base de datos
- El estado del viaje NO cambia (mantiene su estado actual, ej: "en_ruta_destino")
- El supervisor/operador recibe la alerta de desviación

### Escenario 2: Entrada a Geocerca de Ruta - Comportamiento Normal

**Precondiciones**:
- Existe un viaje activo con una geocerca de ruta asignada
- El vehículo está fuera de la geocerca de ruta (en desviación)
- El sistema está procesando eventos de Wialon

**Flujo**:
1. Wialon detecta que el vehículo entró a la geocerca de ruta
2. Wialon envía un evento `geofence_entry` con el `geofence_id` de la geocerca de ruta
3. El sistema procesa el evento y consulta el role de la geocerca
4. El sistema identifica que es una geocerca con role="route"
5. El sistema determina que el vehículo regresó a la ruta correcta
6. El sistema envía un webhook `geofence_transition` a Flowtify
7. El sistema NO envía webhook `route_deviation` (solo para salidas)

**Resultado Esperado**:
- Se envía solo el webhook `geofence_transition` a Flowtify
- No se envía notificación WhatsApp (comportamiento normal)
- El evento queda registrado en la base de datos
- El sistema puede opcionalmente registrar que el vehículo regresó a la ruta

### Escenario 3: Múltiples Salidas de Geocerca de Ruta - Período de Gracia

**Precondiciones**:
- Existe un viaje activo con una geocerca de ruta asignada (role="route")
- El vehículo está dentro de la geocerca de ruta
- El sistema está procesando eventos de Wialon
- No se ha enviado ninguna notificación de desviación en los últimos 5 minutos (período de gracia)

**Flujo**:
1. Wialon detecta que el vehículo salió de la geocerca de ruta (primera salida)
2. Wialon envía un evento `geofence_exit` con el `geofence_id` de la geocerca de ruta
3. El sistema procesa el evento y determina que es una desviación de ruta
4. El sistema envía una notificación WhatsApp (primera notificación)
5. El sistema envía ambos webhooks (`geofence_transition` y `route_deviation`) a Flowtify
6. Menos de 5 minutos después, el vehículo entra a la geocerca de ruta y sale nuevamente (segunda salida)
7. Wialon envía otro evento `geofence_exit` para la misma geocerca
8. El sistema procesa el evento y determina que es una desviación de ruta
9. El sistema NO envía notificación WhatsApp (período de gracia activo)
10. El sistema envía ambos webhooks (`geofence_transition` y `route_deviation`) a Flowtify (webhooks siempre se envían)

**Resultado Esperado**:
- Se envía solo UNA notificación WhatsApp (la primera)
- Se envían webhooks en AMBOS eventos (cada salida genera webhooks)
- El período de gracia previene notificaciones duplicadas pero no afecta los webhooks
- Los eventos quedan registrados en la base de datos

### Escenario 4: Salida de Geocerca de Carga - Comportamiento Existente

**Precondiciones**:
- Existe un viaje activo con una geocerca de carga asignada
- El vehículo está dentro de la geocerca de carga
- El sistema está procesando eventos de Wialon

**Flujo**:
1. Wialon detecta que el vehículo salió de la geocerca de carga
2. Wialon envía un evento `geofence_exit` con el `geofence_id` de la geocerca de carga
3. El sistema procesa el evento y consulta el role de la geocerca
4. El sistema identifica que es una geocerca con role="loading"
5. El sistema determina que el vehículo salió de la zona de carga
6. El sistema actualiza el estado del viaje a "en_ruta_destino"
7. El sistema envía un webhook `geofence_transition` a Flowtify
8. El sistema NO envía webhook `route_deviation` (solo para geocercas de ruta)

**Resultado Esperado**:
- Se actualiza el estado del viaje correctamente
- Se envía solo el webhook `geofence_transition` a Flowtify
- No se envía webhook `route_deviation` (comportamiento existente se mantiene)

## Criterios de Éxito

### Medibles

1. **Detección Automática**: 100% de las salidas de geocercas de ruta son detectadas como desviaciones de ruta
2. **Notificaciones Enviadas**: 100% de las desviaciones de ruta generan notificaciones WhatsApp
3. **Webhooks Enviados**: 100% de las desviaciones de ruta generan webhooks `route_deviation` a Flowtify
4. **Tiempo de Procesamiento**: El procesamiento de eventos de desviación de ruta se completa en menos de 2 segundos
5. **Consistencia de Datos**: 100% de los webhooks `route_deviation` incluyen información correcta de la geocerca

### Cualitativos

1. **Claridad de Notificaciones**: Las notificaciones WhatsApp son claras y accionables para el operador
2. **Integración Consistente**: La funcionalidad se integra de manera consistente con el sistema existente
3. **Mantenibilidad**: El código es fácil de mantener y extender para futuras geocercas
4. **Retrocompatibilidad**: No se rompe la funcionalidad existente de geocercas de carga/descarga

## Entidades Clave

### Geocerca de Ruta

- **ID**: Identificador único de la geocerca
- **Role**: "route" (definido en el payload de creación de viaje)
- **Nombre**: Nombre de la geocerca (ej: "RUTA")
- **Tipo**: Tipo de geocerca (polygon, circle, etc.)
- **Ubicación**: Coordenadas que definen la geocerca

### Evento de Desviación de Ruta

- **Tipo**: "geofence_exit" con role="route"
- **Ubicación Actual**: Coordenadas del vehículo cuando salió de la geocerca
- **Geocerca**: Información de la geocerca de la cual salió
- **Viaje**: Información del viaje asociado
- **Conductor**: Información del conductor
- **Unidad**: Información de la unidad/vehículo

### Webhook de Desviación

- **Tipo**: "route_deviation"
- **Severidad**: "critical"
- **Ubicación Actual**: Coordenadas del vehículo cuando salió de la geocerca
- **Información de Desviación**: Indica que el vehículo salió de la geocerca de ruta (no se requiere cálculo de distancia específico)
- **Acciones Inmediatas**: Notificaciones enviadas, supervisor alertado, etc.

## Suposiciones

1. **Geocercas Definidas**: Las geocercas de ruta están correctamente definidas en el payload de creación de viaje con role="route"
2. **Wialon Configurado**: Wialon está configurado para enviar eventos de entrada/salida de geocercas
3. **Base de Datos**: La tabla `trip_geofences` contiene correctamente el role de las geocercas asociadas a cada viaje
4. **WebhookService Disponible**: El `WebhookService` está disponible y configurado para enviar webhooks a Flowtify
5. **NotificationService Disponible**: El `NotificationService` está disponible y configurado para enviar notificaciones WhatsApp
6. **Retrocompatibilidad**: Los cambios no afectan el comportamiento existente para geocercas de carga/descarga

## Dependencias

1. **EventService**: Debe procesar eventos de `geofence_exit` y determinar si es una geocerca de ruta
2. **WebhookService**: Debe tener el método `send_route_deviation` disponible (ya existe)
3. **NotificationService**: Debe poder enviar notificaciones WhatsApp al grupo del viaje
4. **Base de Datos**: Debe tener acceso a la tabla `trip_geofences` para consultar el role de las geocercas
5. **Modelos**: Los modelos de eventos y webhooks deben soportar la información de desviación de ruta

## Restricciones

1. **No Cambiar Estructura de Webhooks**: Los webhooks existentes (`geofence_transition`) deben mantener su estructura actual
2. **No Romper Funcionalidad Existente**: Las geocercas de carga/descarga deben continuar funcionando como antes
3. **Compatibilidad con Wialon**: Los cambios deben ser compatibles con los eventos que Wialon puede enviar
4. **Performance**: El procesamiento adicional no debe afectar significativamente el tiempo de respuesta

## Notas de Implementación

1. **Detección de Role**: El sistema debe primero intentar obtener el role desde la BD usando el `geofence_id`. Si no se encuentra, usar detección por nombre como fallback.
2. **Doble Webhook**: Cuando se detecta salida de geocerca de ruta, se deben enviar ambos webhooks: `geofence_transition` (para mantener consistencia) y `route_deviation` (para la funcionalidad nueva).
3. **Notificación WhatsApp**: La notificación debe ser clara e informativa, similar a las notificaciones de carga/descarga.
4. **Período de Gracia**: Se debe implementar un período de gracia (configurable, por defecto 5 minutos) para evitar notificaciones duplicadas de desviación de ruta. El período de gracia solo aplica a las notificaciones WhatsApp, no a los webhooks.
5. **Registro de Eventos**: Los eventos de desviación de ruta deben quedar registrados en la base de datos con el tipo correcto.
6. **Manejo de Errores**: Si falla el envío del webhook `route_deviation`, no debe afectar el envío del webhook `geofence_transition`.

## Clarificaciones

### Session 2025-01-27

- Q: ¿Cómo calcular la distancia de desviación cuando solo se detecta salida de geocerca? → A: El cálculo de distancia no es necesario, solo determinar si se salió de la geocerca
- Q: ¿Qué contenido debe tener el mensaje de WhatsApp de desviación de ruta? → A: Mensaje informativo: "⚠️ Desviación de ruta detectada. El vehículo salió de [nombre_geocerca]. Ubicación actual: [dirección]"
- Q: ¿Debe cambiar el estado del viaje cuando se detecta desviación de ruta? → A: No cambiar el estado del viaje, solo enviar notificaciones y webhooks
- Q: ¿Cómo prevenir notificaciones duplicadas si el vehículo entra y sale rápidamente? → A: Enviar solo una notificación cada X minutos (período de gracia configurable, ej: 5 minutos)

## Preguntas Abiertas

Ninguna en este momento. La especificación es clara y completa basada en los requisitos del usuario.


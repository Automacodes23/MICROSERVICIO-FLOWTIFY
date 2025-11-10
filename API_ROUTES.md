# API Routes Documentation

This document lists all the API routes available in the logistics microservice application for trip management, WhatsApp integration, Wialon tracking, and health checks.

## Base URL
All endpoints are prefixed with `/api/v1` (configurable via `api_prefix` setting).

## 1. Trip Management Endpoints

### POST `/api/v1/trips/create`
**Purpose:** Create a new trip from Floatify
- **Description:** Receives the complete payload from Floatify and orchestrates:
  - Creation of unit and driver
  - Creation of the trip
  - Creation of geofences
  - Creation of WhatsApp group
  - Sending of welcome message
- **Request Body:** `TripCreate` model with the following actual example payload:
```json
{
  "event": "whatsapp.group.create",
  "action": "create_group",
  "tenant_id": 24,
  "trip": {
    "id": 45,
    "code": "TEST_FLOW_20241006123456",
    "status": "asignado",
    "planned_start": "2025-10-06T20:00:00-06:00",
    "planned_end": "2025-10-06T22:00:00-06:00",
    "origin": "León",
    "destination": "Jalisco"
  },
  "driver": {
    "id": 33,
    "name": "PRUEBA_FLOWTIFY",
    "phone": "+5214775589835"
  },
  "unit": {
    "id": 18,
    "floatify_unit_id": "18",
    "name": "Torton 309 41BB3T",
    "plate": "41BB3T",
    "wialon_id": "27538728",
    "imei": "863719067169228"
  },
  "customer": {
    "id": 6,
    "name": "Pañales Aurora"
  },
  "geofences": [
    {
      "role": "origin",
      "geofence_id": "685",
      "geofence_name": "PATIO TTU",
      "geofence_type": "circle",
      "order": 0
    },
    {
      "role": "loading",
      "geofence_id": "9001",
      "geofence_name": "CEDIS COPPEL LEON",
      "geofence_type": "polygon",
      "order": 1
    },
    {
      "role": "unloading",
      "geofence_id": "9002",
      "geofence_name": "BODEGA COPPEL JALISCO",
      "geofence_type": "polygon",
      "order": 2
    }
  ],
  "whatsapp_participants": [
    "+5214771817823",
    "+5214775589835"
  ],
  "metadata": {
    "tipo": "Cliente",
    "modalidad": "Renta",
    "priority": "medium"
  }
}
```
- **Response:** `TripCreatedResponse` model

### GET `/api/v1/trips/{trip_id}`
**Purpose:** Get trip information by ID
- **Description:** Retrieves information about a specific trip
- **Path Parameter:** `trip_id` (string, supports UUID)
- **Response:** SuccessResponse with trip data

### POST `/api/v1/trips/{trip_id}/complete`
**Purpose:** Complete a trip
- **Description:** Marks the trip as completed and updates the final substatus
- **Path Parameter:** `trip_id` (string, supports UUID)
- **Request Body:** `TripCompletion` model with the following actual example payload:
```json
{
  "event": "trip.completed",
  "tenant_id": 24,
  "trip_id": "12345",
  "trip_code": "TEST_FLOW_20241006123456",
  "final_status": "finalizado",
  "final_substatus": "descarga_completada",
  "timestamp": "2024-10-07T04:15:30-06:00",
  "trigger_details": {
    "trigger": "driver_message",
    "message_content": "ya termine de descargar me voy",
    "source": "whatsapp"
  },
  "completion_data": {
    "actual_end_time": "2024-10-07T04:15:30-06:00",
    "final_location": {
      "latitude": 20.6736,
      "longitude": -103.3444
    }
  }
}
```
- **Response:** SuccessResponse with trip data and completion message

### PUT `/api/v1/trips/{trip_id}/status`
**Purpose:** Update trip status
- **Description:** Updates the status and substatus of a trip
- **Path Parameters:**
  - `trip_id` (string, supports UUID)
- **Query Parameters:**
  - `status` (string) - new status to set (must be from TRIP_STATUS constants: "planned", "asignado", "en_ruta_carga", "en_zona_carga", "en_ruta_destino", "en_zona_descarga", "finalizado", "cancelado")
  - `substatus` (string) - new substatus to set (must be from TRIP_SUBSTATUS constants: "por_iniciar", "esperando_inicio_carga", "cargando", "carga_completada", "rumbo_a_descarga", "esperando_inicio_descarga", "descargando", "descarga_completada", "entregado_confirmado")
- **Example:** `/trips/12345/status?status=en_ruta_carga&substatus=rumbo_a_zona_carga`
- **Response:** SuccessResponse with updated trip data and status message

### POST `/api/v1/trips/{trip_id}/cleanup_group`
**Purpose:** Clean up WhatsApp Group (Testing)
- **Description:** Makes the bot leave the WhatsApp group associated with the trip and deactivates the conversation. For testing purposes only.
- **Path Parameter:** `trip_id` (string, supports UUID)
- **Response:** SuccessResponse with cleanup status

## 2. WhatsApp Webhook Endpoints

### POST `/api/v1/whatsapp/messages`
**Purpose:** Receive WhatsApp messages from Evolution API
- **Description:** Processes messages from drivers, analyzes them with AI, and generates responses
- **Request Body:** `WhatsAppMessage` model with the following actual example payload from Evolution API:
```json
{
  "event": "messages.upsert",
  "instance": "default_instance",
  "sender": "+5214775589835",
  "data": {
    "key": {
      "remoteJid": "120363186235823658@g.us",
      "fromMe": false,
      "id": "1234567890-1234567890"
    },
    "pushName": "PRUEBA FLOWTIFY",
    "message": {
      "conversation": "ya termine de descargar me voy"
    },
    "messageType": "conversation",
    "messageTimestamp": 1728286530
  }
}
```
- **Response:** `MessageProcessedResponse` model
- **Special Behavior:** If AI analysis determines a response is needed, sends response back to the group

## 3. Wialon Integration Endpoints

### GET `/api/v1/wialon/debug/trip/{wialon_unit_id}`
**Purpose:** Debug endpoint to verify trip lookup
- **Description:** Temporary debugging endpoint to check if trips can be found by Wialon unit ID
- **Path Parameter:** `wialon_unit_id` (string)
- **Response:** Object with debug information about unit and trip lookup

### POST `/api/v1/wialon/events`
**Purpose:** Receive Wialon events
- **Description:** Receives events from Wialon in various formats (JSON, form-encoded, text/plain), normalizes them, and processes them
- **Request Body:** Raw Wialon event data in form-urlencoded format (application/x-www-form-urlencoded) with the following actual example:
```
unit_name=Torton 309 41BB3T
&unit_id=27538728
&imei=863719067169228
&latitude=21.0505
&longitude=-101.7995
&altitude=1796
&speed=6.2
&course=270
&address=ZONA DE CARGA - PLANTA ACME, León, Gto., México
&pos_time=2024-10-07 01:28:20
&driver_name=PRUEBA FLOWTIFY
&driver_code=29
&geofence_name=PLANTA ACME - ZONA CARGA
&geofence_id=9001
&notification_type=geofence_entry
&notification_id=NOTIF_1728280100_1234
&event_time=1728280100
```
- **Content-Type:** application/x-www-form-urlencoded
- **Response:** `EventProcessedResponse` model
- **Special Behavior:** Returns 200 status to prevent Wialon from resending events, even if processing fails

## 4. Health Check Endpoints

### GET `/api/v1/health`
**Purpose:** Basic health check
- **Description:** Returns 200 if the service is alive
- **Response:** Status object with status and timestamp

### GET `/api/v1/health/detailed`
**Purpose:** Detailed health check
- **Description:** Verifies service, database, circuit breakers, and configuration
- **Response:** Detailed health status including:
  - Service information
  - Dependencies health (database)
  - Circuit breaker states
  - Overall status

### GET `/api/v1/health/ready`
**Purpose:** Kubernetes readiness check
- **Description:** Checks if the service is ready to receive traffic
- **Response:** Readiness status with individual checks

### GET `/api/v1/health/live`
**Purpose:** Kubernetes liveness check
- **Description:** Checks if the service is alive (not deadlocked)
- **Response:** Liveness status with timestamp

## 5. Root Endpoint

### GET `/`
**Purpose:** Root endpoint
- **Description:** Provides basic service information
- **Response:** Service name, version, environment, and documentation availability

## Fixed Constants

### Trip Status Values
The following are the available values for trip status:
- `"planned"`: Planificado
- `"asignado"`: Asignado
- `"en_ruta_carga"`: En ruta a carga
- `"en_zona_carga"`: En zona de carga
- `"en_ruta_destino"`: En ruta a destino
- `"en_zona_descarga"`: En zona de descarga
- `"finalizado"`: Finalizado
- `"cancelado"`: Cancelado

### Trip Substatus Values
The following are the available values for trip substatus:
- `"por_iniciar"`: Por iniciar
- `"esperando_inicio_carga"`: Esperando inicio carga
- `"cargando"`: Cargando
- `"carga_completada"`: Carga completada
- `"rumbo_a_descarga"`: Rumbo a descarga
- `"esperando_inicio_descarga"`: Esperando inicio descarga
- `"descargando"`: Descargando
- `"descarga_completada"`: Descarga completada
- `"entregado_confirmado"`: Entregado confirmado

### Geofence Roles
The following are the available values for geofence roles:
- `"origin"`: Origen
- `"loading"`: Carga
- `"unloading"`: Descarga
- `"waypoint"`: Punto intermedio
- `"depot"`: Depósito

### Message Intents (from Gemini AI)
The following are the available message intent values:
- `"waiting_turn"`: Esperando turno
- `"loading_started"`: Inicio de carga
- `"loading_complete"`: Carga completada
- `"unloading_started"`: Inicio de descarga
- `"unloading_complete"`: Descarga completada
- `"route_update"`: Actualización de ruta
- `"issue_report"`: Reporte de problema
- `"other"`: Otro

### Sender Types
The following are the available sender types:
- `"driver"`: Conductor
- `"bot"`: Bot
- `"supervisor"`: Supervisor
- `"system"`: Sistema

### Message Directions
The following are the available message directions:
- `"inbound"`: Entrante
- `"outbound"`: Saliente

## Authentication & Security

- Most endpoints do not require authentication but may use webhook secrets for verification
- The `webhook_secret` setting can be used to secure incoming webhooks
- Evolution API and other external integrations use their own authentication methods

## Error Handling

All endpoints follow a consistent error response format:
```json
{
  "success": false,
  "error": {
    "code": "ERROR_CODE",
    "message": "Error message",
    "context": { ... }
  },
  "trace_id": "request_trace_id"
}
```

## Response Models

### TripCreatedResponse
```json
{
  "success": true,
  "trip_id": "12345",
  "trip_code": "TEST_FLOW_20241006123456",
  "whatsapp_group_id": "120363186235823658@g.us",
  "welcome_message_sent": true,
  "message": "Viaje creado exitosamente"
}
```

### SuccessResponse (Generic)
```json
{
  "success": true,
  "message": "Estado actualizado exitosamente",
  "data": {
    "id": "12345",
    "code": "TEST_FLOW_20241006123456",
    "status": "en_ruta_carga",
    "substatus": "rumbo_a_zona_carga",
    "updated_at": "2024-10-07T02:15:30-06:00"
  }
}
```

### ErrorResponse
```json
{
  "success": false,
  "error": {
    "code": "TRIP_NOT_FOUND",
    "message": "Trip with id 12345 not found",
    "context": {
      "trip_id": "12345"
    }
  },
  "trace_id": "req_abc123def456"
}
```

### EventProcessedResponse
```json
{
  "success": true,
  "event_id": "event_7890",
  "trip_id": "12345",
  "message": "Evento procesado exitosamente"
}
```

### MessageProcessedResponse
```json
{
  "success": true,
  "message_id": "msg_5678",
  "ai_result": {
    "intent": "unloading_started",
    "confidence": 0.95,
    "entities": {
      "action": "descarga",
      "status": "iniciada"
    },
    "response": "Confirmado, has iniciado la descarga. Continúa con el proceso.",
    "action": "update_substatus",
    "new_substatus": "descargando"
  },
  "message": "Mensaje procesado exitosamente"
}
```

### HealthResponse
```json
{
  "status": "healthy",
  "timestamp": "2024-10-07T03:15:30Z",
  "service": "logistics-trip-service",
  "version": "1.0.0",
  "database": "connected"
}
```

## Notes

- The API prefix `/api/v1` can be changed via the `api_prefix` configuration
- WhatsApp webhook expects messages from Evolution API in the specific format
- Wialon webhook handles multiple content types and returns 200 to prevent retries
- Health endpoints are essential for container orchestration systems
- Although trip instructions mention scanning QR codes, there is no specific QR validation endpoint implemented in this API
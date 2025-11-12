"""
Constantes del sistema
"""

# Estados de viajes
TRIP_STATUS = {
    "PLANNED": "planned",
    "ASSIGNED": "asignado",
    "EN_ROUTE_LOADING": "en_ruta_carga",
    "IN_LOADING_ZONE": "en_zona_carga",
    "EN_ROUTE_DESTINATION": "en_ruta_destino",
    "IN_UNLOADING_ZONE": "en_zona_descarga",
    "COMPLETED": "finalizado",
    "CANCELLED": "cancelado",
}

# Subestados de viajes
TRIP_SUBSTATUS = {
    "TO_START": "por_iniciar",
    "WAITING_LOADING": "esperando_inicio_carga",
    "LOADING": "cargando",
    "LOADING_COMPLETE": "carga_completada",
    "HEADING_TO_UNLOAD": "rumbo_a_descarga",
    "WAITING_UNLOADING": "esperando_inicio_descarga",
    "UNLOADING": "descargando",
    "UNLOADING_COMPLETE": "descarga_completada",
    "DELIVERED": "entregado_confirmado",
}

# Tipos de eventos de Wialon
WIALON_EVENT_TYPES = {
    "GEOFENCE_ENTRY": "geofence_entry",
    "GEOFENCE_EXIT": "geofence_exit",
    "SPEED_VIOLATION": "speed_violation",
    "PANIC_BUTTON": "panic_button",
    "CONNECTION_LOST": "connection_lost",
    "ROUTE_DEVIATION": "route_deviation",
}

# Roles de geocercas
GEOFENCE_ROLES = {
    "ORIGIN": "origin",
    "LOADING": "loading",
    "UNLOADING": "unloading",
    "WAYPOINT": "waypoint",
    "DEPOT": "depot",
    "ROUTE": "route",
}

# Período de gracia para notificaciones de desviación de ruta (en segundos)
ROUTE_DEVIATION_GRACE_PERIOD = 300  # 5 minutos

# Intenciones de mensajes (Gemini AI)
MESSAGE_INTENTS = {
    "WAITING_TURN": "waiting_turn",
    "LOADING_STARTED": "loading_started",
    "LOADING_COMPLETE": "loading_complete",
    "UNLOADING_STARTED": "unloading_started",
    "UNLOADING_COMPLETE": "unloading_complete",
    "ROUTE_UPDATE": "route_update",
    "ISSUE_REPORT": "issue_report",
    "OTHER": "other",
}

# Tipos de remitentes de mensajes
SENDER_TYPES = {
    "DRIVER": "driver",
    "BOT": "bot",
    "SUPERVISOR": "supervisor",
    "SYSTEM": "system",
}

# Direcciones de mensajes
MESSAGE_DIRECTIONS = {
    "INBOUND": "inbound",
    "OUTBOUND": "outbound",
}

# Niveles de log
LOG_LEVELS = {
    "DEBUG": "DEBUG",
    "INFO": "INFO",
    "WARNING": "WARNING",
    "ERROR": "ERROR",
    "CRITICAL": "CRITICAL",
}

# Timeouts (en segundos)
TIMEOUTS = {
    "HTTP_REQUEST": 30,
    "DB_QUERY": 10,
    "GEMINI_API": 60,
}

# Retry configuration
RETRY_CONFIG = {
    "MAX_ATTEMPTS": 3,
    "INITIAL_DELAY": 1,  # segundos
    "MAX_DELAY": 10,  # segundos
    "EXPONENTIAL_BASE": 2,
}


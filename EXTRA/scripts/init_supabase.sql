-- Script de inicialización para Supabase (proyecto TESTING-FLOWTIFY)
-- Ejecutar en el SQL Editor de Supabase

-- 1. Unidades de transporte
CREATE TABLE IF NOT EXISTS units (
  id BIGSERIAL PRIMARY KEY,
  code TEXT UNIQUE NOT NULL,
  wialon_id TEXT UNIQUE,
  plate TEXT,
  imei TEXT,
  provider TEXT DEFAULT 'wialon',
  metadata JSONB DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

-- 2. Operadores/Conductores
CREATE TABLE IF NOT EXISTS drivers (
  id BIGSERIAL PRIMARY KEY,
  name TEXT NOT NULL,
  phone TEXT UNIQUE NOT NULL,
  wialon_driver_code TEXT,
  metadata JSONB DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

-- 3. Viajes
CREATE TABLE IF NOT EXISTS trips (
  id BIGSERIAL PRIMARY KEY,
  external_id TEXT UNIQUE,
  tenant_id INTEGER NOT NULL,
  code TEXT UNIQUE NOT NULL,
  unit_id BIGINT REFERENCES units(id),
  driver_id BIGINT REFERENCES drivers(id),
  customer_id INTEGER,
  
  -- Estados
  status TEXT DEFAULT 'planned',
  substatus TEXT DEFAULT 'por_iniciar',
  
  -- Información del viaje
  origin TEXT,
  destination TEXT,
  planned_start TIMESTAMPTZ,
  planned_end TIMESTAMPTZ,
  actual_start TIMESTAMPTZ,
  actual_end TIMESTAMPTZ,
  
  -- Metadata flexible
  metadata JSONB DEFAULT '{}'::jsonb,
  
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

-- Índices para trips
CREATE INDEX IF NOT EXISTS idx_trips_tenant ON trips(tenant_id);
CREATE INDEX IF NOT EXISTS idx_trips_unit ON trips(unit_id);
CREATE INDEX IF NOT EXISTS idx_trips_status ON trips(status);
CREATE INDEX IF NOT EXISTS idx_trips_external ON trips(external_id);

-- 4. Geocercas
CREATE TABLE IF NOT EXISTS geofences (
  id BIGSERIAL PRIMARY KEY,
  wialon_id TEXT UNIQUE,
  name TEXT NOT NULL,
  type TEXT,
  latitude DOUBLE PRECISION,
  longitude DOUBLE PRECISION,
  radius_m INTEGER,
  metadata JSONB DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ DEFAULT now()
);

-- 5. Relación Viaje-Geocercas
CREATE TABLE IF NOT EXISTS trip_geofences (
  id BIGSERIAL PRIMARY KEY,
  trip_id BIGINT REFERENCES trips(id) ON DELETE CASCADE,
  geofence_id BIGINT REFERENCES geofences(id),
  role TEXT NOT NULL,
  sequence INTEGER DEFAULT 0,
  entered_at TIMESTAMPTZ,
  exited_at TIMESTAMPTZ,
  metadata JSONB DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_trip_geofences_trip ON trip_geofences(trip_id);

-- 6. Eventos de Wialon
CREATE TABLE IF NOT EXISTS events (
  id BIGSERIAL PRIMARY KEY,
  external_id TEXT UNIQUE,
  trip_id BIGINT REFERENCES trips(id),
  unit_id BIGINT REFERENCES units(id),
  
  source TEXT NOT NULL DEFAULT 'wialon',
  event_type TEXT NOT NULL,
  
  -- Datos del evento
  latitude DOUBLE PRECISION,
  longitude DOUBLE PRECISION,
  speed DOUBLE PRECISION,
  address TEXT,
  
  -- Payload completo
  raw_payload JSONB DEFAULT '{}'::jsonb,
  
  -- Control de procesamiento
  processed BOOLEAN DEFAULT false,
  processed_at TIMESTAMPTZ,
  
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_events_trip ON events(trip_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_events_unprocessed ON events(processed) WHERE processed = false;
CREATE INDEX IF NOT EXISTS idx_events_external ON events(external_id);

-- 7. Conversaciones de WhatsApp
CREATE TABLE IF NOT EXISTS conversations (
  id BIGSERIAL PRIMARY KEY,
  trip_id BIGINT REFERENCES trips(id) UNIQUE,
  whatsapp_group_id TEXT UNIQUE NOT NULL,
  group_name TEXT,
  participants JSONB DEFAULT '[]'::jsonb,
  is_active BOOLEAN DEFAULT true,
  created_at TIMESTAMPTZ DEFAULT now()
);

-- 8. Mensajes
CREATE TABLE IF NOT EXISTS messages (
  id BIGSERIAL PRIMARY KEY,
  conversation_id BIGINT REFERENCES conversations(id),
  trip_id BIGINT REFERENCES trips(id),
  
  -- Identificación del mensaje
  whatsapp_message_id TEXT,
  
  -- Remitente
  sender_type TEXT,
  sender_phone TEXT,
  
  -- Contenido
  direction TEXT,
  content TEXT NOT NULL,
  transcription TEXT,
  
  -- Resultado de IA
  ai_result JSONB,
  
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_messages_conversation ON messages(conversation_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_messages_trip ON messages(trip_id, created_at DESC);

-- 9. Interacciones con IA
CREATE TABLE IF NOT EXISTS ai_interactions (
  id BIGSERIAL PRIMARY KEY,
  message_id BIGINT REFERENCES messages(id),
  trip_id BIGINT REFERENCES trips(id),
  
  input_text TEXT NOT NULL,
  response_text TEXT,
  response_metadata JSONB DEFAULT '{}'::jsonb,
  
  -- Clasificación
  intent TEXT,
  confidence DOUBLE PRECISION,
  entities JSONB DEFAULT '{}'::jsonb,
  
  created_at TIMESTAMPTZ DEFAULT now()
);

-- 10. Configuraciones dinámicas
CREATE TABLE IF NOT EXISTS configurations (
  id BIGSERIAL PRIMARY KEY,
  name TEXT NOT NULL,
  scope TEXT NOT NULL,
  scope_id INTEGER,
  
  config JSONB NOT NULL,
  is_active BOOLEAN DEFAULT true,
  
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_config_scope ON configurations(scope, scope_id, is_active);

-- 11. System Logs
CREATE TABLE IF NOT EXISTS system_logs (
  id BIGSERIAL PRIMARY KEY,
  trace_id UUID DEFAULT gen_random_uuid(),
  level TEXT NOT NULL,
  service TEXT NOT NULL,
  message TEXT NOT NULL,
  context JSONB DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_logs_level_created ON system_logs(level, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_logs_trace ON system_logs(trace_id);

-- Función para auto-actualizar updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Triggers para updated_at
CREATE TRIGGER update_units_updated_at BEFORE UPDATE ON units
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_drivers_updated_at BEFORE UPDATE ON drivers
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_trips_updated_at BEFORE UPDATE ON trips
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_configurations_updated_at BEFORE UPDATE ON configurations
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();


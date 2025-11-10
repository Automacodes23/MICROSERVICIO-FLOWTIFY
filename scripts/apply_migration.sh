#!/bin/bash
# Script para aplicar migración de webhook tables
# Uso: ./scripts/apply_migration.sh

set -e

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuración (lee del .env o usa defaults)
DB_HOST=${MYSQL_HOST:-localhost}
DB_PORT=${MYSQL_PORT:-3307}
DB_NAME=${MYSQL_DATABASE:-logistics_db}
DB_USER=${MYSQL_USER:-root}
DB_PASSWORD=${MYSQL_PASSWORD:-}

MIGRATION_FILE="./migrations/001_webhook_tables.sql"

echo -e "${YELLOW}🔄 Aplicando migración: 001_webhook_tables${NC}"
echo "   Host: $DB_HOST:$DB_PORT"
echo "   Database: $DB_NAME"
echo ""

# Verificar que el archivo de migración existe
if [ ! -f "$MIGRATION_FILE" ]; then
    echo -e "${RED}❌ Error: Archivo de migración no encontrado: $MIGRATION_FILE${NC}"
    exit 1
fi

# Preguntar confirmación
echo -e "${YELLOW}⚠️  Esta operación creará 3 nuevas tablas:${NC}"
echo "   - webhook_delivery_log"
echo "   - webhook_config"
echo "   - webhook_dead_letter_queue"
echo ""
read -p "¿Continuar con la migración? (y/N): " -n 1 -r
echo ""

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${YELLOW}⏸️  Migración cancelada${NC}"
    exit 0
fi

# Aplicar migración
echo -e "${GREEN}▶️  Aplicando migración...${NC}"

if [ -z "$DB_PASSWORD" ]; then
    # Sin password
    mysql -h "$DB_HOST" -P "$DB_PORT" -u "$DB_USER" "$DB_NAME" < "$MIGRATION_FILE"
else
    # Con password
    mysql -h "$DB_HOST" -P "$DB_PORT" -u "$DB_USER" -p"$DB_PASSWORD" "$DB_NAME" < "$MIGRATION_FILE"
fi

if [ $? -eq 0 ]; then
    echo ""
    echo -e "${GREEN}✅ Migración aplicada exitosamente!${NC}"
    echo ""
    
    # Verificar tablas creadas
    echo -e "${GREEN}📋 Verificando tablas creadas:${NC}"
    if [ -z "$DB_PASSWORD" ]; then
        mysql -h "$DB_HOST" -P "$DB_PORT" -u "$DB_USER" "$DB_NAME" -e "SHOW TABLES LIKE 'webhook%';"
    else
        mysql -h "$DB_HOST" -P "$DB_PORT" -u "$DB_USER" -p"$DB_PASSWORD" "$DB_NAME" -e "SHOW TABLES LIKE 'webhook%';"
    fi
    
    echo ""
    echo -e "${GREEN}✅ Setup de base de datos completado!${NC}"
else
    echo ""
    echo -e "${RED}❌ Error al aplicar migración${NC}"
    exit 1
fi


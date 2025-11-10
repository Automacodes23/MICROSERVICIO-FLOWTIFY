#!/bin/bash
# Script para hacer backup de la base de datos antes de migración
# Uso: ./scripts/backup_database.sh

set -e

# Configuración (ajusta según tu .env)
DB_HOST=${MYSQL_HOST:-localhost}
DB_PORT=${MYSQL_PORT:-3307}
DB_NAME=${MYSQL_DATABASE:-logistics_db}
DB_USER=${MYSQL_USER:-root}
DB_PASSWORD=${MYSQL_PASSWORD:-}

# Directorio de backups
BACKUP_DIR="./backup"
mkdir -p "$BACKUP_DIR"

# Nombre del archivo con timestamp
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="$BACKUP_DIR/database_backup_${TIMESTAMP}.sql"

echo "🔄 Creando backup de base de datos..."
echo "   Host: $DB_HOST:$DB_PORT"
echo "   Database: $DB_NAME"
echo "   Backup file: $BACKUP_FILE"

# Hacer backup (ajusta el comando según tu sistema)
if [ -z "$DB_PASSWORD" ]; then
    # Sin password (XAMPP local típicamente)
    mysqldump -h "$DB_HOST" -P "$DB_PORT" -u "$DB_USER" "$DB_NAME" > "$BACKUP_FILE"
else
    # Con password
    mysqldump -h "$DB_HOST" -P "$DB_PORT" -u "$DB_USER" -p"$DB_PASSWORD" "$DB_NAME" > "$BACKUP_FILE"
fi

echo "✅ Backup completado exitosamente!"
echo "   Archivo: $BACKUP_FILE"
echo "   Tamaño: $(du -h "$BACKUP_FILE" | cut -f1)"

# Comprimir el backup
gzip "$BACKUP_FILE"
echo "✅ Backup comprimido: ${BACKUP_FILE}.gz"


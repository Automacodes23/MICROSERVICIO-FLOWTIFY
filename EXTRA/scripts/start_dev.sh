#!/bin/bash

# Script para iniciar el servidor en modo desarrollo

echo "🚀 Iniciando servidor en modo desarrollo..."

# Activar entorno virtual si existe
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Verificar que exista .env
if [ ! -f ".env" ]; then
    echo "❌ Archivo .env no encontrado"
    echo "📝 Copia env.example a .env y configura las variables"
    exit 1
fi

# Ejecutar con reload
uvicorn app.main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --reload \
    --log-level info

# O con el comando directo de Python
# python -m app.main


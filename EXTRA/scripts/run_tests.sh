#!/bin/bash

# Script para ejecutar tests

echo "🧪 Ejecutando tests..."

# Activar entorno virtual si existe
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Ejecutar pytest con coverage
pytest tests/ \
    --cov=app \
    --cov-report=term-missing \
    --cov-report=html \
    -v \
    "$@"

# Mostrar resumen
echo ""
echo "✅ Tests completados"
echo "📊 Reporte de coverage generado en htmlcov/index.html"


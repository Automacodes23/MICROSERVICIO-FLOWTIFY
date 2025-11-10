"""
Leer los últimos logs del servidor para debugging
"""
import os
import sys

LOG_FILE = "server_logs.txt"

if not os.path.exists(LOG_FILE):
    print(f"[ERROR] El archivo de logs '{LOG_FILE}' no existe.")
    print("\n[SOLUCION] Los logs están en la terminal donde corre uvicorn.")
    print("Por favor, copia los logs de esa terminal que contengan el trace_id del error.")
    sys.exit(1)

print("=" * 80)
print("ÚLTIMOS LOGS DEL SERVIDOR")
print("=" * 80)

with open(LOG_FILE, "r", encoding="utf-8", errors="ignore") as f:
    lines = f.readlines()
    
    # Mostrar las últimas 150 líneas
    recent_lines = lines[-150:]
    
    print("\n".join(recent_lines))

print("\n" + "=" * 80)
print(f"Total de líneas en el log: {len(lines)}")
print("=" * 80)


"""Crear viaje de prueba rápido para testing"""
import requests
import json

BASE_URL = "http://localhost:8000/api/v1"

# 1. Crear viaje
print("Creando viaje de prueba...")

trip_data = {
    "floatify_trip_id": "TEST_GEOFENCE_123",
    "unit_id": "18",  # Floatify unit ID
    "driver_id": "33",  # Floatify driver ID
    "origin": "León, Gto",
    "destination": "Jalisco",
    "route_geofences": [
        {
            "wialon_geofence_id": "9001",
            "visit_order": 1,
            "visit_type": "pickup",
            "name": "ZONA CARGA TEST"
        },
        {
            "wialon_geofence_id": "9002",
            "visit_order": 2,
            "visit_type": "delivery",
            "name": "ZONA DESCARGA TEST"
        }
    ],
    "metadata": {
        "tenant_id": 24,
        "priority": "high"
    }
}

response = requests.post(f"{BASE_URL}/trips", json=trip_data)

if response.status_code == 201:
    result = response.json()
    trip = result['data']
    print(f"\nViaje creado:")
    print(f"  ID: {trip['id']}")
    print(f"  Code: {trip['floatify_trip_id']}")
    print(f"  Status: {trip['status']}")
    print(f"  Unit ID: {trip['unit_id']}")
    print(f"\nGuarda este ID para probar geofence events:")
    print(f"  TRIP_ID = '{trip['id']}'")
else:
    print(f"Error: {response.status_code}")
    print(response.text)


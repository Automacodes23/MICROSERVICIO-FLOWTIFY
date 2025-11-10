#!/bin/bash

# Script para probar el webhook con curl usando el payload real de Evolution API

GROUP_ID="120363404629424294@g.us"
TIMESTAMP=$(date +%s)

echo "================================================================================"
echo "TEST DEL WEBHOOK CON CURL - PAYLOAD REAL"
echo "================================================================================"
echo ""
echo "[INFO] Grupo: $GROUP_ID"
echo "[INFO] Mensaje: 'esperando en el anden'"
echo ""
echo "[1] Enviando request..."
echo ""

curl -X POST "http://localhost:8000/api/v1/whatsapp/messages" \
  -H "Content-Type: application/json" \
  -d "{
  \"event\": \"messages.upsert\",
  \"instance\": \"SATECH-BOT\",
  \"data\": {
    \"key\": {
      \"remoteJid\": \"$GROUP_ID\",
      \"fromMe\": false,
      \"id\": \"TEST_MSG_$TIMESTAMP\",
      \"senderLid\": \"133857336623289@lid\",
      \"participant\": \"5214771817823@s.whatsapp.net\"
    },
    \"pushName\": \"AutomaCode\",
    \"status\": \"DELIVERY_ACK\",
    \"message\": {
      \"conversation\": \"esperando en el anden\"
    },
    \"messageType\": \"conversation\",
    \"messageTimestamp\": $TIMESTAMP,
    \"instanceId\": \"7697f881-ec18-4d06-85c5-f492140ec471\",
    \"source\": \"web\"
  },
  \"sender\": \"5214771817823@s.whatsapp.net\"
}"

echo ""
echo ""
echo "================================================================================"
echo "[2] Verificar en la BD:"
echo "    python scripts/verify_message_in_db.py"
echo "================================================================================"


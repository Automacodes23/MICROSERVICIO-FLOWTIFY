# Script PowerShell para probar el webhook con el payload real de Evolution API

$GROUP_ID = "120363404629424294@g.us"
$TIMESTAMP = [int][double]::Parse((Get-Date -UFormat %s))

Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host "TEST DEL WEBHOOK CON POWERSHELL - PAYLOAD REAL" -ForegroundColor Cyan
Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "[INFO] Grupo: $GROUP_ID" -ForegroundColor Yellow
Write-Host "[INFO] Mensaje: 'esperando en el anden'" -ForegroundColor Yellow
Write-Host ""
Write-Host "[1] Enviando request..." -ForegroundColor Green
Write-Host ""

$payload = @{
    event = "messages.upsert"
    instance = "SATECH-BOT"
    data = @{
        key = @{
            remoteJid = $GROUP_ID
            fromMe = $false
            id = "TEST_MSG_$TIMESTAMP"
            senderLid = "133857336623289@lid"
            participant = "5214771817823@s.whatsapp.net"
        }
        pushName = "AutomaCode"
        status = "DELIVERY_ACK"
        message = @{
            conversation = "esperando en el anden"
        }
        messageType = "conversation"
        messageTimestamp = $TIMESTAMP
        instanceId = "7697f881-ec18-4d06-85c5-f492140ec471"
        source = "web"
    }
    sender = "5214771817823@s.whatsapp.net"
} | ConvertTo-Json -Depth 10

try {
    $response = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/whatsapp/messages" `
        -Method Post `
        -Body $payload `
        -ContentType "application/json" `
        -ErrorAction Stop
    
    Write-Host ""
    Write-Host "[OK] Respuesta exitosa:" -ForegroundColor Green
    Write-Host ($response | ConvertTo-Json -Depth 10)
    
} catch {
    Write-Host ""
    Write-Host "[ERROR] Falló el request:" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    
    if ($_.Exception.Response) {
        $reader = New-Object System.IO.StreamReader($_.Exception.Response.GetResponseStream())
        $responseBody = $reader.ReadToEnd()
        Write-Host "Response Body: $responseBody" -ForegroundColor Red
    }
}

Write-Host ""
Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host "[2] Verificar en la BD:" -ForegroundColor Yellow
Write-Host "    python scripts/verify_message_in_db.py" -ForegroundColor White
Write-Host "================================================================================" -ForegroundColor Cyan


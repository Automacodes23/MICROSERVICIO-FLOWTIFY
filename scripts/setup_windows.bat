@echo off
REM ============================================================================
REM Script de Setup Automatizado para Windows
REM Ejecuta los pasos 1-4 del setup de webhooks
REM ============================================================================

echo.
echo ============================================================================
echo   SETUP DE WEBHOOKS FLOWTIFY - AUTOMATIZADO
echo ============================================================================
echo.

REM Verificar que estamos en el directorio correcto
if not exist "migrations\001_webhook_tables.sql" (
    echo [ERROR] No se encuentra el archivo de migracion.
    echo Por favor ejecuta este script desde el directorio raiz del proyecto.
    echo.
    pause
    exit /b 1
)

REM ============================================================================
REM PASO 1: BACKUP DE BASE DE DATOS
REM ============================================================================

echo [PASO 1/4] Creando backup de base de datos...
echo.

REM Crear directorio de backup si no existe
if not exist "backup" mkdir backup

REM Obtener timestamp
for /f "tokens=2 delims==" %%I in ('wmic os get localdatetime /value') do set datetime=%%I
set TIMESTAMP=%datetime:~0,8%_%datetime:~8,6%

REM Hacer backup
set BACKUP_FILE=backup\database_backup_%TIMESTAMP%.sql

echo Ejecutando mysqldump...
mysqldump -h localhost -P 3307 -u root logistics_db > "%BACKUP_FILE%" 2>nul

if %ERRORLEVEL% EQU 0 (
    echo [OK] Backup creado: %BACKUP_FILE%
    echo.
) else (
    echo [ADVERTENCIA] No se pudo crear backup automatico.
    echo Verifica que MySQL este ejecutandose en el puerto 3307.
    echo.
    echo Presiona ENTER para continuar sin backup o CTRL+C para cancelar...
    pause >nul
)

REM ============================================================================
REM PASO 2: APLICAR MIGRACION DE BASE DE DATOS
REM ============================================================================

echo [PASO 2/4] Aplicando migracion de base de datos...
echo.

echo Creando tablas: webhook_delivery_log, webhook_config, webhook_dead_letter_queue
mysql -h localhost -P 3307 -u root logistics_db < migrations\001_webhook_tables.sql 2>nul

if %ERRORLEVEL% EQU 0 (
    echo [OK] Migracion aplicada exitosamente
    echo.
) else (
    echo [ERROR] Fallo al aplicar migracion
    echo.
    echo Posibles causas:
    echo - MySQL no esta ejecutandose
    echo - Puerto incorrecto (verifica que sea 3307)
    echo - Base de datos 'logistics_db' no existe
    echo.
    pause
    exit /b 1
)

REM Verificar tablas creadas
echo Verificando tablas creadas...
mysql -h localhost -P 3307 -u root logistics_db -e "SHOW TABLES LIKE 'webhook%%';" 2>nul
echo.

REM ============================================================================
REM PASO 3: GENERAR WEBHOOK SECRET
REM ============================================================================

echo [PASO 3/4] Generando WEBHOOK_SECRET seguro...
echo.

REM Generar secret usando Python
python -c "import secrets; print('WEBHOOK_SECRET=' + secrets.token_urlsafe(32))" > webhook_secret_temp.txt 2>nul

if %ERRORLEVEL% EQU 0 (
    echo [OK] Secret generado exitosamente
    type webhook_secret_temp.txt
    echo.
    echo IMPORTANTE: Copia esta linea a tu archivo .env
    echo.
) else (
    echo [ADVERTENCIA] No se pudo generar secret automaticamente
    echo Genera uno manualmente con: python -c "import secrets; print(secrets.token_urlsafe(32))"
    echo.
)

REM ============================================================================
REM PASO 4: INSTALAR DEPENDENCIAS PYTHON
REM ============================================================================

echo [PASO 4/4] Instalando dependencias Python...
echo.

echo Instalando httpx...
pip install httpx==0.27.0 --quiet

if %ERRORLEVEL% EQU 0 (
    echo [OK] httpx instalado
) else (
    echo [ERROR] Fallo al instalar httpx
)

echo Instalando tenacity...
pip install tenacity==8.2.3 --quiet

if %ERRORLEVEL% EQU 0 (
    echo [OK] tenacity instalado
    echo.
) else (
    echo [ERROR] Fallo al instalar tenacity
    echo.
)

REM ============================================================================
REM PASO 5: EJECUTAR VERIFICACION
REM ============================================================================

echo.
echo ============================================================================
echo   EJECUTANDO VERIFICACION FINAL
echo ============================================================================
echo.

python scripts\verify_setup.py

REM ============================================================================
REM RESUMEN Y PROXIMOS PASOS
REM ============================================================================

echo.
echo ============================================================================
echo   SETUP COMPLETADO
echo ============================================================================
echo.
echo PROXIMOS PASOS:
echo.
echo 1. Agrega las nuevas variables a tu archivo .env
echo    - Copia el contenido de env.example (lineas 65-82)
echo    - O usa el WEBHOOK_SECRET generado arriba
echo.
echo 2. Configura la URL de Flowtify:
echo    FLOWTIFY_WEBHOOK_URL=https://api.flowtify.com/webhooks
echo.
echo 3. Reinicia el servidor FastAPI para aplicar los cambios
echo.
echo 4. Coordina con el equipo de Flowtify:
echo    - Compartir el WEBHOOK_SECRET de forma segura
echo    - Confirmar endpoints disponibles
echo.
echo ============================================================================
echo.

REM Limpiar archivo temporal
if exist webhook_secret_temp.txt del webhook_secret_temp.txt

pause


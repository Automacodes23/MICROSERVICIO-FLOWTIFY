"""
Script de verificación de setup de webhooks
Ejecutar: python scripts/verify_setup.py
"""
import sys
from pathlib import Path

# Agregar path del proyecto
sys.path.insert(0, str(Path(__file__).parent.parent))


def verify_setup():
    """Verificar que el setup de webhooks esté completo"""
    print("🔍 Verificando configuración de webhooks...\n")
    
    errors = []
    warnings = []
    
    # 1. Verificar importaciones
    print("📦 Verificando dependencias Python...")
    try:
        import httpx
        print(f"   ✅ httpx instalado (v{httpx.__version__})")
    except ImportError:
        errors.append("httpx no está instalado - ejecuta: pip install httpx")
    
    try:
        import tenacity
        print(f"   ✅ tenacity instalado (v{tenacity.__version__})")
    except ImportError:
        errors.append("tenacity no está instalado - ejecuta: pip install tenacity")
    
    # 2. Verificar configuración
    print("\n⚙️  Verificando configuración...")
    try:
        from app.config import settings
        
        if settings.flowtify_webhook_url:
            print(f"   ✅ FLOWTIFY_WEBHOOK_URL: {settings.flowtify_webhook_url}")
        else:
            warnings.append("FLOWTIFY_WEBHOOK_URL no está configurado (será necesario para producción)")
        
        if settings.webhook_secret:
            print(f"   ✅ WEBHOOK_SECRET configurado (longitud: {len(settings.webhook_secret)} chars)")
            if len(settings.webhook_secret) < 32:
                warnings.append("WEBHOOK_SECRET es corto (recomendado mínimo 32 caracteres)")
        else:
            errors.append("WEBHOOK_SECRET no está configurado")
        
        print(f"   ✅ WEBHOOK_RETRY_MAX: {settings.webhook_retry_max}")
        print(f"   ✅ WEBHOOK_TIMEOUT: {settings.webhook_timeout}")
        
    except ImportError:
        errors.append("No se pudo importar app.config - verifica que el proyecto esté bien estructurado")
    except AttributeError as e:
        errors.append(f"Falta configuración en settings: {e}")
    except Exception as e:
        errors.append(f"Error al cargar configuración: {e}")
    
    # 3. Verificar base de datos
    print("\n🗄️  Verificando base de datos...")
    try:
        import aiomysql
        import asyncio
        from app.config import settings
        
        async def check_tables():
            try:
                conn = await aiomysql.connect(
                    host=settings.mysql_host,
                    port=settings.mysql_port,
                    user=settings.mysql_user,
                    password=settings.mysql_password if settings.mysql_password else "",
                    db=settings.mysql_database,
                )
                
                async with conn.cursor() as cursor:
                    # Verificar tablas
                    await cursor.execute("SHOW TABLES LIKE 'webhook%'")
                    tables = await cursor.fetchall()
                    
                    expected_tables = ['webhook_config', 'webhook_dead_letter_queue', 'webhook_delivery_log']
                    found_tables = [t[0] for t in tables]
                    
                    for table in expected_tables:
                        if table in found_tables:
                            print(f"   ✅ Tabla '{table}' existe")
                        else:
                            errors.append(f"Tabla '{table}' no existe - ejecuta: mysql < migrations/001_webhook_tables.sql")
                    
                    # Verificar configuración inicial
                    if 'webhook_config' in found_tables:
                        await cursor.execute("SELECT COUNT(*) FROM webhook_config WHERE tenant_id = 24")
                        result = await cursor.fetchone()
                        count = result[0] if result else 0
                        if count > 0:
                            print(f"   ✅ Configuración inicial encontrada ({count} registros)")
                        else:
                            warnings.append("No hay configuración de webhook para tenant 24 - se creará automáticamente")
                
                conn.close()
                
            except Exception as e:
                errors.append(f"Error de base de datos: {e}")
        
        asyncio.run(check_tables())
        
    except ImportError:
        errors.append("aiomysql no está instalado - ejecuta: pip install aiomysql")
    except Exception as e:
        errors.append(f"Error al verificar base de datos: {e}")
    
    # 4. Verificar archivos del proyecto
    print("\n📁 Verificando archivos del proyecto...")
    project_root = Path(__file__).parent.parent
    
    required_files = {
        "migrations/001_webhook_tables.sql": "Migración de base de datos",
        "docs/prd.md": "PRD (Product Requirements Document)",
        "docs/architecture.md": "Documento de arquitectura técnica",
        "docs/flowtify-integration-architecture.md": "Especificación de integración Flowtify",
    }
    
    for file_path, description in required_files.items():
        full_path = project_root / file_path
        if full_path.exists():
            print(f"   ✅ {description}: {file_path}")
        else:
            warnings.append(f"Archivo no encontrado: {file_path} ({description})")
    
    # 5. Resumen
    print("\n" + "="*70)
    if errors:
        print("❌ ERRORES ENCONTRADOS:")
        for i, error in enumerate(errors, 1):
            print(f"   {i}. {error}")
    
    if warnings:
        print("\n⚠️  ADVERTENCIAS:")
        for i, warning in enumerate(warnings, 1):
            print(f"   {i}. {warning}")
    
    if not errors and not warnings:
        print("✅ ¡SETUP COMPLETADO EXITOSAMENTE!")
        print("\n📋 Próximos pasos:")
        print("   1. Coordina con el equipo de Flowtify:")
        print("      - Confirmar URL de webhooks de producción/staging")
        print("      - Compartir WEBHOOK_SECRET de forma segura")
        print("      - Configurar endpoints en su lado")
        print("\n   2. Continúa con la implementación del código:")
        print("      - Modelos Pydantic (app/models/webhooks.py)")
        print("      - WebhookService (app/services/webhook_service.py)")
        print("      - Extender servicios existentes")
        print("      - Tests unitarios e integración")
    elif not errors:
        print("✅ Setup básico completado con advertencias")
        print("   Revisa las advertencias antes de continuar a producción")
        print("   Para desarrollo local, puedes continuar")
    else:
        print("\n❌ Corrige los errores antes de continuar")
        print("   Consulta SETUP_WEBHOOKS.md para más detalles")
    
    print("="*70)
    
    return len(errors) == 0


if __name__ == "__main__":
    try:
        success = verify_setup()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⏸️  Verificación cancelada por el usuario")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Error inesperado: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


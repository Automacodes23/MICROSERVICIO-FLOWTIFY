# 🧹 Guía de Limpieza Masiva de Grupos de WhatsApp

## 🎯 Propósito

Este script te permite sacar al bot de **todos** los grupos de WhatsApp de prueba de una sola vez, evitando los rate limits de WhatsApp.

---

## 📋 Requisitos

1. **Servidor corriendo**: `uvicorn app.main:app --reload`
2. **pymysql instalado**: `pip install pymysql`
3. **Base de datos MySQL activa**

---

## 🚀 Uso Básico

### **1. Modo Seguro (Dry Run) - Ver qué haría sin ejecutar**

```bash
python scripts/cleanup_all_test_groups.py --dry-run
```

**Recomendado para la primera vez**. Te muestra:
- ✅ Cuántos grupos se limpiarían
- ✅ Qué grupos específicamente
- ✅ NO hace cambios reales

---

### **2. Limpiar SOLO grupos de prueba (contienen "TEST")**

```bash
python scripts/cleanup_all_test_groups.py --filter-test
```

**Más seguro**. Solo limpia grupos cuyo código de viaje contenga "TEST" o "test".

---

### **3. Limpiar grupos recientes (últimos N días)**

```bash
python scripts/cleanup_all_test_groups.py --days 7
```

Solo limpia grupos creados en los últimos 7 días.

---

### **4. Combinar filtros (recomendado)**

```bash
python scripts/cleanup_all_test_groups.py --filter-test --days 7 --dry-run
```

Primero prueba con `--dry-run`, luego quítalo para ejecutar de verdad:

```bash
python scripts/cleanup_all_test_groups.py --filter-test --days 7
```

---

### **5. Limpiar TODO sin confirmar (⚠️ PELIGROSO)**

```bash
python scripts/cleanup_all_test_groups.py --confirm
```

**NO RECOMENDADO** a menos que estés 100% seguro.

---

## 📊 Ejemplo de Salida

```
================================================================================
                LIMPIEZA MASIVA DE GRUPOS DE WHATSAPP
================================================================================

[1/5] Verificando servidor...
✓ Servidor activo

[2/5] Obteniendo conversaciones de la base de datos...
   Filtro: Solo grupos con 'TEST' en el nombre
✓ 15 conversaciones encontradas

[3/5] Resumen de conversaciones:

#     Trip Code                 Grupo WhatsApp                 Creado
--------------------------------------------------------------------------------
1     TEST_FLOW_20251104...     120363405870310803@g.us        2025-11-04 10:30:15
2     TEST_FLOW_20251104...     120363405870310804@g.us        2025-11-04 11:45:22
...

Total: 15 conversaciones

[4/5] Confirmación:

⚠️  ADVERTENCIA:
  - El bot será expulsado de TODOS estos grupos
  - Las conversaciones se marcarán como inactivas
  - Esta acción NO es reversible fácilmente

¿Continuar? (escribe 'SI' para confirmar): SI

[5/5] Procesando limpieza...

[1/15] Procesando TEST_FLOW_20251104_103015... ✓ Bot ha salido del grupo
[2/15] Procesando TEST_FLOW_20251104_114522... ✓ Bot ha salido del grupo
...

================================================================================
                            RESUMEN FINAL
================================================================================

  ✓ Exitosos: 15
  ✗ Errores:   0
  Total:      15

================================================================================
¡Limpieza completada exitosamente!
================================================================================

💡 Recomendaciones:
  - Verifica que el bot haya salido de los grupos en WhatsApp
  - Revisa la base de datos: las conversaciones deben estar con status='inactive'
  - Ahora puedes crear nuevos grupos sin preocuparte por el rate limit
```

---

## 🎛️ Opciones Disponibles

| Opción | Descripción | Ejemplo |
|--------|-------------|---------|
| `--dry-run` | Solo muestra qué haría, no ejecuta | `--dry-run` |
| `--filter-test` | Solo limpia grupos con "TEST" | `--filter-test` |
| `--days N` | Solo grupos creados en últimos N días | `--days 7` |
| `--confirm` | No pide confirmación (peligroso) | `--confirm` |
| `--help` | Muestra ayuda | `--help` |

---

## 🛡️ Estrategia Recomendada

### **Primera vez - Exploración segura:**

```bash
# 1. Ver todos los grupos activos (sin hacer nada)
python scripts/cleanup_all_test_groups.py --dry-run

# 2. Ver solo grupos de prueba (sin hacer nada)
python scripts/cleanup_all_test_groups.py --filter-test --dry-run

# 3. Limpiar solo los de prueba (con confirmación)
python scripts/cleanup_all_test_groups.py --filter-test
```

### **Limpieza regular después de pruebas:**

```bash
# Limpiar grupos de prueba de los últimos 3 días
python scripts/cleanup_all_test_groups.py --filter-test --days 3
```

### **Emergencia - WhatsApp te bloqueó por crear muchos grupos:**

```bash
# 1. Primero revisa qué se va a limpiar
python scripts/cleanup_all_test_groups.py --filter-test --dry-run

# 2. Limpia todo lo de prueba
python scripts/cleanup_all_test_groups.py --filter-test --confirm
```

---

## ⚠️ Advertencias Importantes

1. **No es reversible fácilmente**: Una vez que el bot sale del grupo, necesitas agregarlo manualmente de nuevo.

2. **Evolution API debe estar funcionando**: Si la API falla, algunos grupos pueden no limpiarse.

3. **Rate Limits**: Aunque el script limpia grupos, Evolution API también puede tener rate limits. Si hay muchos grupos (50+), considera usar `--days` para hacerlo en lotes.

4. **Backup recomendado**: Antes de limpiar TODO, considera hacer backup de la BD:
   ```bash
   mysqldump -u root -p logistics_db > backup_before_cleanup.sql
   ```

---

## 🐛 Solución de Problemas

### **Error: "pymysql no está instalado"**
```bash
pip install pymysql
```

### **Error: "El servidor no está disponible"**
```bash
# Inicia el servidor
uvicorn app.main:app --reload
```

### **Error: "No se encontraron conversaciones activas"**
- Ya limpiaste todos los grupos ✅
- O no hay grupos activos en la BD

### **Error al limpiar un grupo específico**
- El grupo puede ya estar eliminado en WhatsApp
- El bot puede ya haber sido expulsado
- Evolution API puede estar fallando (revisa logs)

---

## 📝 Notas

- El script usa colores en la consola para mejor legibilidad
- Genera un resumen detallado al final
- Si hay errores, los muestra al final con detalles
- Puedes cancelar en cualquier momento con `Ctrl+C`

---

## 🎓 Ejemplos Prácticos

### **Caso 1: Hiciste 20 pruebas E2E hoy**
```bash
python scripts/cleanup_all_test_groups.py --filter-test --days 1
```

### **Caso 2: Quieres limpiar toda la semana de pruebas**
```bash
python scripts/cleanup_all_test_groups.py --filter-test --days 7
```

### **Caso 3: Quieres ver qué grupos tienes activos**
```bash
python scripts/cleanup_all_test_groups.py --dry-run
```

### **Caso 4: Limpieza total (usar con precaución)**
```bash
# Primero revisa
python scripts/cleanup_all_test_groups.py --dry-run

# Luego ejecuta si estás seguro
python scripts/cleanup_all_test_groups.py
# Te pedirá escribir "SI" para confirmar
```

---

## ✅ Checklist Post-Limpieza

Después de ejecutar el script:

- [ ] Verifica en WhatsApp que el bot salió de los grupos
- [ ] Revisa la BD: `SELECT * FROM conversations WHERE status='inactive';`
- [ ] Confirma que puedes crear nuevos grupos sin rate limit
- [ ] Guarda el resumen del script si necesitas referencia

---

¿Preguntas? Revisa el código del script en `scripts/cleanup_all_test_groups.py` - está bien documentado! 🚀


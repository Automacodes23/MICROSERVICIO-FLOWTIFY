# 🚀 Guía Rápida: Limpieza de Base de Datos

## ⏱️ Inicio Rápido (2 minutos)

### Método 1: Script Python (Recomendado) ⭐

```bash
# 1. Abre terminal en la carpeta del proyecto
cd C:\Users\capac\OneDrive\Escritorio\SHOW-SERVICE

# 2. Ejecuta el script
python scripts/reset_database.py

# 3. Cuando te pida confirmación, escribe:
ELIMINAR TODO

# 4. Espera a ver: ✅ PROCESO COMPLETADO EXITOSAMENTE

# 5. Si te pregunta si quieres verificar, escribe:
s
```

**Resultado**: Base de datos completamente limpia en ~30 segundos.

---

### Método 2: SQL Directo (Más Rápido) ⚡

```
1. Abre navegador → http://localhost/phpmyadmin
2. Click en "logistics_db" (barra izquierda)
3. Click en pestaña "SQL" (arriba)
4. Abre el archivo: scripts/reset_database_simple.sql
5. Copia TODO el contenido
6. Pega en el editor SQL de phpMyAdmin
7. Click en botón "Continuar" (abajo derecha)
8. Verás una tabla con todas las tablas en 0 registros
```

**Resultado**: Base de datos limpia en 10 segundos.

---

## 🎯 ¿Cuál método usar?

### Usa Método 1 (Python) si:
- ✅ Quieres ver el progreso detallado
- ✅ Prefieres la seguridad de confirmaciones
- ✅ Quieres logs de lo que sucede

### Usa Método 2 (SQL) si:
- ⚡ Quieres la opción MÁS rápida
- ⚡ Estás cómodo con phpMyAdmin
- ⚡ No quieres complicarte con Python

---

## ⚠️ Antes de Empezar

**SOLO ejecuta esto si:**
- ✅ Estás en tu computadora de desarrollo
- ✅ NO es una base de datos de producción
- ✅ Estás seguro de querer eliminar TODOS los datos

**NO ejecutes si:**
- ❌ Tienes datos importantes que quieres conservar
- ❌ Estás en un servidor de producción
- ❌ No estás seguro de lo que hace

---

## 🔍 Verificación Post-Limpieza

Después de ejecutar cualquier método, verifica que funcionó:

### Opción A: Desde phpMyAdmin
```sql
SELECT COUNT(*) FROM units;      -- Debe ser 0
SELECT COUNT(*) FROM drivers;    -- Debe ser 0
SELECT COUNT(*) FROM trips;      -- Debe ser 0
SELECT COUNT(*) FROM messages;   -- Debe ser 0
```

### Opción B: El script Python te preguntará automáticamente

---

## 🆘 Si Algo Sale Mal

### Error: "No se puede conectar a MySQL"
**Solución**: 
1. Abre XAMPP Control Panel
2. Asegúrate de que MySQL esté corriendo (verde)
3. Intenta de nuevo

### Error: "Access denied"
**Solución**: 
1. Abre `.env` en la raíz del proyecto
2. Verifica que tengas:
```env
MYSQL_USER=root
MYSQL_PASSWORD=
```
(password vacío si usas XAMPP por defecto)

### Error: "ModuleNotFoundError"
**Solución**:
```bash
# Asegúrate de estar en la raíz del proyecto
cd C:\Users\capac\OneDrive\Escritorio\SHOW-SERVICE

# Instala dependencias si es necesario
pip install -r requirements.txt
```

---

## 📊 Qué Datos se Eliminarán

El script eliminará TODOS los datos de:

| Tabla | Descripción | Cantidad de Registros Actual |
|-------|-------------|------------------------------|
| `units` | Unidades de transporte | Se eliminará TODO |
| `drivers` | Conductores | Se eliminará TODO |
| `trips` | Viajes | Se eliminará TODO |
| `messages` | Mensajes de WhatsApp | Se eliminará TODO |
| `conversations` | Conversaciones | Se eliminará TODO |
| `events` | Eventos de Wialon | Se eliminará TODO |
| `ai_interactions` | Interacciones con IA | Se eliminará TODO |
| `geofences` | Geocercas | Se eliminará TODO |
| `trip_geofences` | Relación viajes-geocercas | Se eliminará TODO |
| `system_logs` | Logs del sistema | Se eliminará TODO |
| `configurations` | Configuraciones | Se eliminará TODO |

**IMPORTANTE**: Las **estructuras de las tablas** (columnas, índices, foreign keys) NO se eliminan, solo los datos.

---

## ✅ Checklist

Antes de ejecutar:
- [ ] Estoy en mi computadora de desarrollo
- [ ] XAMPP está corriendo (MySQL en verde)
- [ ] He leído las advertencias
- [ ] Estoy seguro de querer eliminar todos los datos
- [ ] Tengo respaldo si necesito (opcional)

Después de ejecutar:
- [ ] Vi mensaje de éxito (✅)
- [ ] Verifiqué que las tablas están vacías
- [ ] La aplicación sigue funcionando
- [ ] Puedo crear nuevos datos de prueba

---

## 🎓 Más Información

- **Análisis completo**: Lee `docs/ANALISIS_LIMPIEZA_BASE_DATOS.md`
- **Resumen ejecutivo**: Lee `docs/RESUMEN_LIMPIEZA_BD.md`
- **Troubleshooting detallado**: Ambos documentos incluyen soluciones

---

## 🤝 ¿Necesitas Ayuda?

Si encuentras problemas:
1. Lee las secciones de troubleshooting en los documentos
2. Verifica que XAMPP esté corriendo
3. Verifica tus credenciales en `.env`
4. Intenta con el método alternativo (SQL si usaste Python, o viceversa)

---

**¡Buena suerte! 🚀**


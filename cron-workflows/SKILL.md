---
name: hermes-skills/cron-workflows
description: Use when chaining automated tasks with Hermes cron jobs. Workflow patterns.
---

# Workflows con Cron — Automatización sin webhooks

Los cron jobs de Hermes permiten encadenar acciones entre servicios sin necesidad de webhooks, APIs de eventos ni desarrollo backend. El agente monitorea cambios periódicamente y dispara la siguiente acción del flujo.

## Documentos de referencia

| Documento | Cuándo cargar |
|-----------|--------------|
| `patrones-workflow.md` | Diseñar flujos multi-paso |
| `lecciones-aprendidas.md` | Pitfalls y buenas prácticas |

## ¿Por qué cron y no webhooks?

| | Cron | Webhooks |
|---|---|---|
| **Implementación** | 1 comando en Hermes | Requiere endpoint público, autenticación, pruebas |
| **Tiempo de setup** | 2 minutos | Días/semanas |
| **Latencia** | 1-5 minutos | Instantánea (<1s) |
| **Mantenimiento** | Ninguno | SSL, disponibilidad, monitoreo |
| **Ideal para** | POC, flujos internos, automatización no crítica | Producción, alta frecuencia, cliente externo |

**Regla de oro:** Validar el flujo con cron primero. Si el equipo lo usa y aporta valor, migrar a webhooks en la aplicación propia.

## Patrón básico

```
Cron (cada 5 min)
  → Revisa estado de tareas/eventos/correos
  → Si detecta un cambio (tarea completada, correo recibido)
  → Ejecuta la acción correspondiente
  → Notifica si hubo cambios
```

## Ejemplo: Flujo de tareas entre 3 personas

```
Paso 1: Usuario A completa "Revisar documento X"
  ↓ (cron detecta en ≤5 min)
Paso 2: Usuario B recibe "Subir documento a plataforma"
  ↓ (Usuario B completa)
Paso 3: Usuario C recibe "Facturar servicio"
  ↓ (Usuario C completa)
Paso 4: Usuario A recibe notificación "Flujo completado"
```

### Implementación

```bash
# Crear el cron job en Hermes
cronjob create \
  --schedule "every 5m" \
  --skill "zoho-mcp" \
  --prompt "Monitorea tareas completadas y dispara el siguiente paso..."
```

## Verificación

```bash
# Listar cron jobs activos
cronjob list

# Ver última ejecución
cronjob list --job-id <id>

# Ejecutar manualmente para pruebas
cronjob run <id>
```

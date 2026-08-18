# Calendario y Tareas — Zoho MCP

Además de correo, Zoho MCP expone herramientas de **Calendar** y **Tasks** (lista de tareas personales). Ambos servicios se agregan desde la misma consola MCP, en el mismo servidor.

## Tasks (To-Do List)

Zoho Mail incluye un gestor de tareas personales. Las tareas son listas de pendientes, no eventos de calendario.

| Característica | Tareas | Calendario |
|---------------|--------|------------|
| ¿Tiene hora? | No, solo fecha de vencimiento | Sí, hora inicio/fin |
| ¿Participantes? | No, son personales | Sí, invitados |
| Estados | `inprogress`, `completed` | Aceptado, rechazado |
| Prioridad | `high`, `medium`, `low` | No aplica |

### Tools de Tasks (6)

| Tool | Acción |
|------|--------|
| `addPersonalTask` | Crear tarea |
| `listPersonalTasks` | Listar todas |
| `getPersonalTask` | Ver detalle |
| `editPersonalTask` | Modificar (requiere `path_variables.taskId`) |
| `getSubtasksForPersonalTask` | Subtareas de una tarea |
| `getSubtasksForGroupTask` | Subtareas de tarea grupal |

### Crear una tarea

```json
{
  "body": {
    "title": "Registro de mantenimiento - Equipo X",
    "description": "Realizar registro de mantenimiento preventivo",
    "priority": "high",
    "dueDate": "15/08/2026"
  }
}
```

⚠️ **Importante:** Usar `title` para el nombre y `description` para el detalle. Si solo se usa `description`, la tarea aparece como "No Title".

### Editar una tarea

```json
{
  "path_variables": { "taskId": "1786144542993155100" },
  "body": { "title": "Nuevo título" }
}
```

## Calendar

Zoho Calendar permite crear eventos en calendarios personales, grupales y compartidos.

### Tools de Calendar (5)

| Tool | Acción |
|------|--------|
| `add_event` | Crear evento |
| `get_event` | Obtener evento(s) por rango |
| `search_event_all_calendars` | Buscar en todos los calendarios |
| `update_event` | Modificar evento (requiere ETAG) |
| `get_calendars` | Listar calendarios disponibles |

### Crear un evento

```json
{
  "body": {
    "caluid": "XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX",
    "title": "Vacaciones Usuario 01",
    "dateandtime": {
      "start": "20260813",
      "end": "20260826",
      "timezone": "America/Bogota"
    },
    "description": "Regreso el 26 de agosto."
  }
}
```

⚠️ **Importante:**
- `caluid` usa el **`uid`** del calendario (hash hexadecimal), NO el `id` numérico
- `dateandtime` es un **objeto** `{start, end, timezone}`, no un string
- Para eventos all-day, la fecha `end` es **exclusiva**: `end: 20260826` significa "hasta el 25 inclusive"
- Formato de fechas: `yyyyMMdd` (all-day) o `yyyyMMddThhmmss` (con hora)

### Listar calendarios

```json
{
  "query_params": { "category": "all" }
}
```

Categorías: `"own"` (default, solo personales), `"group"` (grupales), `"all"` (todos).

### Tipos de calendario

| Tipo | Ejemplo | Acceso típico |
|------|---------|:------------:|
| Personal | Calendario del usuario | `owner` |
| Grupo | "Equipo", "Calidad", "Comercial" | `moderate` |
| Compartido | "Servicios Técnicos" | `moderate` o `view` |
| App | "Zoho Tasks" | `view` |

## Flujo de trabajo con Tasks + Calendar

Un patrón útil es encadenar tareas entre usuarios usando un cron job en Hermes:

```
Usuario A completa tarea "Revisar X"
  → Cron detecta → Crea tarea "Subir X" para Usuario B
    → Usuario B completa → Cron detecta → Crea evento "X completado"
```

Este POC permite validar si el flujo aporta valor antes de implementarlo en una aplicación propia con webhooks.

## Documentación oficial
- [Zoho Mail MCP Tools](https://www.zoho.com/mail/help/mcp/zoho-mail-mcp-tools.html)
- [Zoho Calendar API](https://www.zoho.com/calendar/help/api/introduction.html)
- [Zoho MCP Tool Finder](https://www.zoho.com/mail/help/mcp/zohomail-tools.html)

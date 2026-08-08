# Patrones de Workflow con Cron

Guía para diseñar flujos de trabajo automatizados usando cron jobs de Hermes como motor de orquestación.

## El modelo mental

Un workflow con cron NO es una tubería en tiempo real. Es un **monitor periódico** que:
1. **Observa** el estado actual de uno o más servicios
2. **Compara** con el estado anterior (o con una condición)
3. **Actúa** si hay cambios relevantes
4. **Registra** lo que hizo para no repetirse

```
┌──────────┐    cada 5 min    ┌──────────┐    si hay cambio    ┌──────────┐
│ Servicio │ ←─── leer ────  │  Cron    │ ──── escribir ───→ │ Servicio │
│    A     │                  │  Agent   │                    │    B     │
└──────────┘                  └──────────┘                    └──────────┘
```

## Patrón 1: Tarea completada → Nueva tarea

**Problema:** Cuando alguien termina una tarea en Zoho Tasks, otra persona debe hacer el siguiente paso. Hoy se hace manualmente (mensaje, llamada, correo).

**Solución:** El cron revisa tareas completadas en la cuenta A y crea la tarea siguiente en la cuenta B.

**Prompt para el cron:**
```
Revisa las tareas completadas en la cuenta A (accountId: XXXX).
Si encuentras una tarea con título que contenga "Revisar X" completada
en los últimos 5 minutos, crea una tarea en la cuenta B (accountId: YYYY) con:
- title: "Subir X a plataforma"
- description: "Revisado y aprobado. Proceder con la carga."
- priority: high
```

**Regla crítica:** Solo crear tareas nuevas si la tarea disparadora se completó en los últimos N minutos (donde N = intervalo del cron). Esto evita crear tareas duplicadas en cada ejecución.

## Patrón 2: Correo recibido → Tarea creada

**Problema:** Los correos de clientes con solicitudes requieren acción manual para convertirlos en tareas.

**Solución:** El cron revisa correos no leídos con ciertos criterios y crea tareas automáticamente.

**Prompt para el cron:**
```
Revisa correos no leídos en la cuenta A (accountId: XXXX).
Busca correos cuyo asunto contenga "Solicitud de cotización" o "Requiere servicio".
Para cada uno, crea una tarea con:
- title: "Cotizar: [asunto del correo]"
- description: "De: [remitente]. Recibido: [fecha]"
- priority: high
Marca el correo como leído después de crear la tarea.
```

## Patrón 3: Tarea próxima a vencer → Recordatorio

**Problema:** Las tareas con fecha de vencimiento pasan desapercibidas hasta que es tarde.

**Solución:** El cron revisa tareas que vencen en las próximas 24-48 horas y envía un recordatorio.

**Prompt para el cron:**
```
Revisa todas las tareas en la cuenta A (accountId: XXXX).
Para cada tarea con dueDate dentro de las próximas 24 horas y status != completed,
envía un resumen en tu respuesta final indicando título y fecha de vencimiento.
```

## Patrón 4: Evento de calendario próximo → Notificación

**Problema:** El equipo no revisa el calendario compartido diariamente.

**Solución:** El cron revisa eventos del día siguiente y notifica.

**Prompt para el cron:**
```
Revisa los eventos de mañana en el calendario compartido "Equipo" (caluid: XXXX).
Lista título, hora y descripción de cada uno.
```

## Patrón 5: Cadena multi-paso (A → B → C)

**Problema:** Un flujo de trabajo pasa por 3 o más personas secuencialmente.

**Solución:** Un solo cron que monitorea TODOS los pasos de la cadena.

**Estructura del prompt:**
```
PASO 1: Revisa tareas completadas en cuenta A.
Si encuentras "Revisar X" completada → crea "Subir X" en cuenta B.

PASO 2: Revisa tareas completadas en cuenta B.
Si encuentras "Subir X" completada → crea "Facturar X" en cuenta C.

PASO 3: Revisa tareas completadas en cuenta C.
Si encuentras "Facturar X" completada → notifica "Flujo X completado".
```

**IMPORTANTE:** Cada paso debe verificar que la tarea disparadora se completó en la última ventana de tiempo (últimos 5 minutos). Así el mismo cron puede manejar toda la cadena sin crear duplicados.

## Anti-patrones

### ❌ Crear tareas sin verificar si ya existen

```
MAL: "Crea una tarea 'Revisar X' para Usuario B"
BIEN: "Si la tarea 'Revisar X' está completada Y no existe ya 'Subir X' para Usuario B, créala"
```

### ❌ Intervalo de cron muy largo para flujos rápidos

Si el flujo requiere respuesta en <1 minuto, usar cron de 5 minutos frustra al usuario. Para esos casos, considerar webhooks.

### ❌ Un solo cron para 20 flujos distintos

Cada flujo debe tener su propio cron job. Si un cron maneja demasiadas responsabilidades, es difícil depurar cuándo falla.

### ❌ No registrar qué acciones se tomaron

Siempre incluir en el prompt que el agente reporte en su respuesta final qué acciones ejecutó. Esto queda en el log del cron y permite auditoría.

## Cuándo migrar de cron a webhooks

| Señal | Acción |
|-------|--------|
| El flujo se usa 10+ veces al día | Migrar a webhook |
| La latencia de 5 minutos causa quejas | Migrar a webhook |
| Se necesita trazabilidad fina (quién, cuándo, qué) | Migrar a aplicación propia |
| El flujo es estable y validado | Migrar a IIntranet/backend |

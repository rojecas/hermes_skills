# Lecciones Aprendidas — Workflows con Cron

## 1. La ventana de tiempo es crítica

**Problema:** Si el cron revisa "todas las tareas completadas" sin filtrar por tiempo, cada 5 minutos crea tareas duplicadas. En 1 hora tendrías 12 tareas idénticas.

**Solución:** Siempre filtrar por "completadas en los últimos N minutos" donde N = intervalo del cron.

```
✅ "Si la tarea se completó en los últimos 5 minutos, crear la siguiente"
❌ "Si la tarea está completada, crear la siguiente"
```

---

## 2. El agente de cron no tiene contexto de ejecuciones anteriores

**Problema:** Cada ejecución del cron es una sesión limpia. El agente no sabe qué hizo en la ejecución anterior. Si la tarea "Revisar X" se completó hace 10 minutos pero el cron se retrasó, podría crear un duplicado.

**Solución:** Usar la ventana de tiempo con margen. En vez de "últimos 5 minutos", usar "últimos 10 minutos" para absorber pequeños retrasos.

O mejor: que el agente verifique si ya existe la tarea de destino antes de crearla:
```
"Si la tarea 'Revisar X' está completada Y NO existe una tarea 'Subir X'
 en la cuenta B, crear 'Subir X'"
```

---

## 3. Los cron jobs compiten por el modelo

**Problema:** Si tienes 5 cron jobs disparando al mismo tiempo, todos compiten por el mismo modelo LLM. Si usas DeepSeek o APIs con rate limiting, algunos pueden fallar por cuota excedida.

**Solución:** Escalonar los horarios:
- Cron A: cada 5 min empezando en :00
- Cron B: cada 5 min empezando en :01
- Cron C: cada 10 min en :05

---

## 4. `deliver: local` no notifica a nadie

**Problema:** Por defecto los cron jobs guardan la salida localmente pero no avisan. Si un flujo falla, nadie se entera hasta que alguien revisa manualmente.

**Solución:** Configurar `deliver` a un canal donde el equipo vea las notificaciones:
- Telegram: `deliver: "telegram:<chat_id>"`
- Todos los canales: `deliver: "all"`
- Solo guardar: `deliver: "local"` (para watchdogs silenciosos)

---

## 5. Un cron por flujo, no un mega-cron

**Problema:** Poner 10 flujos distintos en un solo cron job hace imposible depurar. Si falla, no sabes cuál de los 10 fue.

**Solución:** Un cron job por flujo de trabajo. Nombres descriptivos:
- `flujo-revision-calibracion`
- `flujo-recordatorio-vencimientos`
- `flujo-cotizaciones-pendientes`

---

## 6. Los scripts son más eficientes que los agentes para tareas simples

**Problema:** Un cron que solo verifica si un share está montado no necesita un agente IA completo. Gastar tokens de LLM para `mountpoint -q /mnt/shares/docs` es un desperdicio.

**Solución:** Usar `no_agent: true` + `script` para tareas puramente mecánicas:

```bash
# script: watchdog-montajes.sh
#!/bin/bash
for mount in /mnt/shares/*/; do
  mountpoint -q "$mount" || echo "CAIDO: $mount"
done
# Si no imprime nada, el cron no notifica (silencioso = todo bien)
```

---

## 7. Probar con `cronjob run` antes de esperar

**Problema:** Programar un cron y esperar 5 minutos para ver si funciona es lento para iterar.

**Solución:** Ejecutar manualmente para pruebas:
```bash
cronjob run <job_id>
```

---

## 8. Documentar la cadena de dependencias

Si un flujo depende de 3 crons encadenados, documentarlo explícitamente:

```
flujo-revision (cada 5 min) → completa tarea A
  ↓ dispara
flujo-carga (cada 5 min) → completa tarea B
  ↓ dispara
flujo-facturacion (cada 5 min) → completa tarea C
  ↓ notifica
canal Telegram
```

Sin esta documentación, en 3 meses nadie recuerda cómo funciona.

---

## 9. Un agente LLM en cron puede entrar en bucle y quemar el saldo

**Problema:** Un monitor con agente LLM completo (cada 5 min, con tools de terminal + archivo) se descontroló: en lugar de responder rápido cuando no había nada que procesar, cada corrida hacía 10-30 tool calls (ejecutar scripts, leer/escribir archivos de estado grandes). El contexto de entrada crecía de ~8K a ~73K tokens dentro de UNA corrida, y con ~290 corridas en 2 días se consumieron decenas de millones de tokens. La cuenta API quedó sin saldo (HTTP 402 en todas las llamadas siguientes) y los servicios dependientes cayeron.

**Causa raíz:** el prompt pedía "revisa y actúa" con acceso total a terminal/archivo. El agente "trabajaba" en cada corrida aunque no hubiera nada que hacer, y cada tool result se re-enviaba completo al proveedor en la siguiente llamada del mismo turno (eso es lo que factura: el input de CADA request, no solo el primero).

**Solución:**
- Todo lo mecánico (consultas, creación de tareas, dedupe) → script con costo $0 + `monitor` (ver Patrón 6).
- El LLM solo despierta cuando el output del script cambia.
- Si el agente es imprescindible: limitar `enabled_toolsets` a lo mínimo y el prompt debe decir explícitamente "si no hay nada que procesar, responde [SILENT]".
- Vigilar el consumo diario (panel del proveedor o el registro de uso del agente): un día normal es ~1-2M tokens; un día de decenas de millones con cientos de entradas del mismo job = bucle.

**Señal de alarma:** en el registro de uso (o el panel del proveedor), un día con decenas de millones de tokens y cientos de ejecuciones del mismo job.

---

## Resumen rápido

| Síntoma | Causa | Solución |
|---------|-------|----------|
| Tareas duplicadas cada 5 min | Sin filtro de tiempo | "completadas en últimos 5 min" |
| Flujo no se dispara | Tarea completada justo después de la ejecución | Aumentar ventana a 10 min |
| Cron fails sin aviso | `deliver: local` | Cambiar a Telegram/Discord |
| Rate limit del modelo | Múltiples crons simultáneos | Escalonar horarios |
| Imposible depurar | Mega-cron con 10 flujos | Un cron por flujo |
| Gasto innecesario de tokens | Agente para tarea mecánica | `no_agent: true` + script |
| Consumo explosivo / saldo agotado | Agente LLM en bucle con tools de terminal/archivo | Script mecánico + `monitor` (Patrón 6) |

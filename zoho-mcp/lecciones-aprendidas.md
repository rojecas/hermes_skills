# Lecciones Aprendidas — Zoho MCP + Hermes

## 1. Transporte: `npx mcp-remote` es obligatorio

**Problema:** Usar HTTP directo (`url:` en config) descubre las tools pero todas las llamadas API fallan.

**Solución:** Usar `npx mcp-remote` con `--transport http-only` (transporte stdio).

```yaml
# ✅ CORRECTO
mcp_servers:
  zoho_mi_cuenta:
    command: "npx"
    args:
      - "mcp-remote"
      - "https://.../message"
      - "--transport"
      - "http-only"

# ❌ INCORRECTO
mcp_servers:
  zoho_mi_cuenta:
    url: "https://.../message"
```

**Referencia:** El JSON config snippet de Zoho muestra este formato. Zoho MCP usa Streamable HTTP y requiere el proxy `mcp-remote` para manejar la sesión OAuth.

---

## 2. `sampling: { enabled: false }` es OBLIGATORIO

**Problema:** Hermes envía `capabilities.sampling.tools` en el handshake MCP. Zoho MCP (implementado en Java) no reconoce este campo y rechaza la conexión.

**Error:** `Unrecognized field "tools" (class ClientCapabilities$Sampling)`

**Solución:** Deshabilitar sampling en la config:

```yaml
sampling:
  enabled: false
```

---

## 3. `accountId` ≠ User ID ≠ Email

**Problema:** Se intentó usar User IDs de Zoho (`8069XXXXX`) y direcciones de correo como `accountId`. Ambos fallan.

**Errores:**
- User ID numérico: `Account id X is invalid` (404)
- Email: `URL_RULE_NOT_CONFIGURED` (404)

**Solución:** El `accountId` es un ID interno (formato `XXXXXXXXXXXXX8002`) que solo se obtiene con `getMailAccounts` o `fetchOrgUsersDetails`.

**Falso positivo:** `listEmails` retorna HTTP 200 con `data: []` incluso para accountIds inválidos. `getAllFolders` es el validador confiable (retorna 404 para IDs inválidos).

---

## 4. MCP es por buzón, no por organización

**Problema:** Se asumió que un servidor MCP autorizado por el Super Admin daría acceso a todas las cuentas de la organización. No es así.

**Realidad:** Cada buzón de correo necesita su propio servidor MCP con su propio URL. "Authorization via Connection" comparte los tokens OAuth a nivel organización, pero cada cuenta requiere su servidor.

**Implicación:** 5 cuentas = 5 servidores MCP = 5 entradas en `config.yaml`.

---

## 5. `getAllFolders` debe agregarse manualmente

**Problema:** Al agregar tools de Zoho Mail, `getAllFolders` NO viene en el conjunto predeterminado. Sin esta tool, no se pueden descubrir los `folderId` y `listEmails` queda ciego.

**Solución:** Buscar y agregar `getAllFolders` manualmente en la consola MCP.

---

## 6. Estructura de argumentos anidada

**Problema:** Zoho MCP usa `path_variables`, `query_params` y `body` como grupos separados. Pasar argumentos como flat key-value falla.

**Solución:** Respetar la estructura:

```json
{
  "path_variables": { "accountId": "XXXX" },
  "query_params": { "fields": "subject,fromAddress", "limit": 5 }
}
```

Hermes maneja esto automáticamente. Solo es relevante al depurar con `curl`.

---

## 7. Calendar: `caluid` usa `uid`, no `id`

**Problema:** `get_calendars` devuelve cada calendario con dos identificadores: `id` (numérico) y `uid` (hash hexadecimal). Usar `id` en `add_event` produce "Calendar not found".

**Solución:** Usar siempre `uid` como `caluid`.

```json
// ❌ caluid: "5060130000000009003"  (id)
// ✅ caluid: "616278b200df4924b83bcb9ea156b7f6"  (uid)
```

---

## 8. Calendar: `dateandtime` es un objeto, no string

**Problema:** Pasar `dateandtime` como string (`"20260813T000000/20260825T235900"`) produce error de parseo JSON.

**Solución:** `dateandtime` es un objeto con `start`, `end` y `timezone`:

```json
{
  "dateandtime": {
    "start": "20260813",
    "end": "20260826",
    "timezone": "America/Bogota"
  }
}
```

Para eventos all-day, la fecha `end` es exclusiva (sumar 1 día).

---

## 9. Tasks: usar `title` + `description`

**Problema:** `addPersonalTask` con solo `description` crea tareas con título "No Title".

**Solución:** Usar ambos campos:
- `title`: nombre visible de la tarea
- `description`: cuerpo/detalle

---

## 10. `sendEmail`: cuerpo vacío en entregas internas Zoho→Zoho

**Problema:** Correos enviados vía API a destinatarios en la misma organización Zoho pueden aparecer sin cuerpo en algunas vistas de la interfaz web.

**Solución:** No es un bug real — el cuerpo SÍ se envía (verificar en vista completa del mensaje o en cliente externo). La vista previa de Zoho Mail a veces no muestra correctamente el contenido de correos enviados por API.

---

## 11. `get_calendars` default es `category: "own"`

**Problema:** `get_calendars` sin parámetros solo devuelve el calendario personal del usuario. Los calendarios grupales y compartidos no aparecen.

**Solución:** Usar `query_params: { category: "all" }` para ver todos los calendarios.

---

## 12. Documentación de Zoho fragmentada

La información relevante está dispersa en múltiples sitios:
- [mcp.zoho.com](https://mcp.zoho.com) — consola de administración
- [zoho.com/mail/help/mcp/](https://www.zoho.com/mail/help/mcp/configure-mcp.html) — guías de configuración
- [help.zoho.com/kb/mcp/](https://help.zoho.com/portal/en/kb/mcp/getting-started/articles/zoho-mcp-help-documentation) — documentación general
- [zoho.com/mail/help/api/](https://www.zoho.com/mail/help/api/overview.html) — REST API (diferente a MCP)
- [zoho.com/calendar/help/api/](https://www.zoho.com/calendar/help/api/introduction.html) — Calendar API

El MCP URL mostrado en docs (`mcp.zoho.com/v1/servers/<id>/mcp`) no coincide con el formato real (`<nombre>.<id>.zohomcp.com/mcp/<key>/message`).

---

## 13. `update_event` requiere ETAG

**Problema:** Modificar un evento existente requiere el header `ETAG` del evento, que debe obtenerse primero con `get_event`.

**Solución:** Para cambios simples, es más práctico eliminar el evento viejo y crear uno nuevo que gestionar el ETAG.

---

## Resumen rápido para depuración

| Síntoma | Causa probable | Solución |
|---------|---------------|----------|
| `✗ Connection failed` | Falta `sampling: enabled: false` | Agregarlo a la config |
| Tools descubiertas = 0 | `npx mcp-remote` no instalado | `npx` lo instala automáticamente |
| `Account id X is invalid` | Usando User ID como accountId | Usar `getMailAccounts` para descubrirlo |
| `URL_RULE_NOT_CONFIGURED` | Usando email como accountId | Usar `getMailAccounts` para descubrirlo |
| `Calendar not found` | Usando `id` en vez de `uid` | Usar `get_calendars` y tomar `uid` |
| `JSON parser error` | `dateandtime` como string | Usar objeto `{start, end, timezone}` |
| Tarea "No Title" | Solo se usó `description` | Agregar `title` |
| Cuerpo de correo vacío | Vista previa de Zoho Mail | Abrir mensaje completo o revisar en otro cliente |

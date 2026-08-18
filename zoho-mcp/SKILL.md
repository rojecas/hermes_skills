---
name: hermes-skills/zoho-mcp
description: Use when integrating Zoho Mail, Calendar, or Tasks via MCP in Hermes.
---

# Integración Zoho MCP para Hermes Agent

Conecta Zoho Mail, Calendar y Tasks a Hermes Agent usando MCP (Model Context Protocol). Permite a tu agente IA leer/redactar correos, gestionar tareas y crear eventos de calendario.

## Documentos de referencia

Carga estos archivos cuando necesites detalle específico:

| Documento | Cuándo cargar |
|-----------|--------------|
| `configuracion-mcp.md` | Configuración paso a paso |
| `mapeo-cuentas.md` | Descubrir accountIds |
| `calendario-tareas.md` | Integración Calendar + Tasks |
| `lecciones-aprendidas.md` | Errores comunes y soluciones |

## Arquitectura

```
Agente IA → npx mcp-remote → Zoho MCP Server → APIs de Zoho (Mail, Calendar, Tasks)
           ↑ mcp__zoho_*__ZohoMail_* / ZohoCalendar_* tools
```

## Configuración Mínima

```yaml
mcp_servers:
  zoho_mi_cuenta:
    command: "npx"
    args:
      - "mcp-remote"
      - "https://<nombre-server>-<id>.zohomcp.com/mcp/<api-key>/message"
      - "--transport"
      - "http-only"
    timeout: 120
    connect_timeout: 60
    sampling:
      enabled: false   # OBLIGATORIO
```

## Account ID

El `accountId` NO es el User ID ni el email. Formato: `XXXXXXXXXXXXX8002`. Se descubre con `getMailAccounts` + `fetchOrgUsersDetails`. Ver `mapeo-cuentas.md`.

## Tools por servicio

Los nombres reales de las tools llevan el prefijo del servicio (`ZohoMail_`).

### Mail (8)
`ZohoMail_listEmails`, `ZohoMail_SearchEmails`, `ZohoMail_getMessageContent`, `ZohoMail_getMessageAttachmentInfo`, `ZohoMail_sendEmail`, `ZohoMail_sendReplyEmail`, `ZohoMail_getAllFolders`, `ZohoMail_getMessageDetails`

### Tasks (6)
`ZohoMail_addPersonalTask`, `ZohoMail_listPersonalTasks`, `ZohoMail_getPersonalTask`, `ZohoMail_editPersonalTask`, `ZohoMail_getSubtasksForPersonalTask`, `ZohoMail_getSubtasksForGroupTask`

### Calendar (5)
`add_event`, `get_event`, `search_event_all_calendars`, `update_event`, `get_calendars`

### Admin (solo para descubrimiento inicial)
`getMailAccounts`, `getAccountDetails`, `getOrgDetails`, `fetchOrgUsersDetails`

## Reglas de uso

- **Enviar correo:** `ZohoMail_sendEmail` requiere `path_variables.accountId` + `body.fromAddress` (OBLIGATORIO, debe ser la cuenta autenticada) + `body.toAddress` + `body.subject` + `body.content` (el cuerpo). NO existe `body.body`.
- **Cuentas de terceros:** `ZohoMail_sendEmail` en modo borrador (`mode: "draft"`)
- **Calendar:** `caluid` usa `uid`, `dateandtime` es objeto `{start, end, timezone}`
- **Tasks:** usar `title` + `description`, no solo `description`
- **MCP por buzón:** cada cuenta necesita su propio servidor MCP

## Verificación

```bash
hermes -p <perfil> mcp test zoho_mi_cuenta
```

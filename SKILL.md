---
name: zoho-mcp-integration
description: Use when integrating Zoho Mail, Calendar, or Tasks via MCP in Hermes.
---

# Integración Zoho MCP para Hermes Agent

Conecta Zoho Mail, Calendar y Tasks a Hermes Agent usando MCP (Model Context Protocol). Permite a tu agente IA leer/redactar correos, gestionar tareas y crear eventos de calendario.

## Arquitectura

```
Agente IA → npx mcp-remote → Zoho MCP Server → APIs de Zoho (Mail, Calendar, Tasks)
           ↑ mcp__zoho_*__ZohoMail_* / ZohoCalendar_* tools
```

## Configuración Mínima

```yaml
# ~/.hermes/profiles/<perfil>/config.yaml
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
      enabled: false   # OBLIGATORIO — Zoho no soporta sampling.tools
```

## Tools Recomendadas

### Mail (8 tools)
`listEmails`, `SearchEmails`, `getMessageContent`, `getMessageAttachmentInfo`, `sendEmail`, `sendReplyEmail`, `getAllFolders`, `getMessageDetails`

### Tasks (6 tools)
`addPersonalTask`, `listPersonalTasks`, `getPersonalTask`, `editPersonalTask`, `getSubtasksForPersonalTask`, `getSubtasksForGroupTask`

### Calendar (5 tools)
`add_event`, `get_event`, `search_event_all_calendars`, `update_event`, `get_calendars`

## Descubrimiento de Account IDs

El `accountId` NO es el User ID de Zoho ni el email. Es un ID interno que solo se obtiene vía API:

1. Agregar `getMailAccounts` + `fetchOrgUsersDetails` temporalmente
2. `getMailAccounts` → obtener `zoid` del campo `policyId.zoid`
3. `fetchOrgUsersDetails` con ese `zoid` → lista todos los usuarios con sus `accountId`
4. Guardar el mapeo y remover las tools admin

## Uso por Cuenta

| Herramienta | Cuenta propia | Cuentas de terceros |
|-------------|:------------:|:-------------------:|
| `sendEmail` | Envío directo | Modo borrador (`mode: "draft"`) |
| `addPersonalTask` | ✅ | ✅ |
| `add_event` | ✅ | ✅ (en calendarios compartidos) |

## Verificación

```bash
hermes -p <perfil> mcp test zoho_mi_cuenta
# Esperado: ✓ Connected ✓ Tools discovered: 14-19
```

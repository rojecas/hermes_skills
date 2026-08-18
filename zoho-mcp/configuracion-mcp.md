# Guía de Configuración — Zoho MCP + Hermes

Guía paso a paso para conectar servicios Zoho con Hermes Agent vía MCP.

## Paso 1: Crear el servidor MCP en Zoho

1. Entrar a https://mcp.zoho.com con la cuenta Zoho que controlará el agente
2. Clic en **Create MCP Server** → asignar nombre (ej: "MiAgente")
3. Clic en **Add Tools** → seleccionar la app Zoho deseada:
   - **Zoho Mail** — correo y tareas personales
   - **Zoho Calendar** — eventos y calendarios
4. Seleccionar las tools individualmente. **Recomendado mínimo:**
   - Mail: `listEmails`, `SearchEmails`, `getMessageContent`, `getMessageAttachmentInfo`, `sendEmail`, `sendReplyEmail`, `getAllFolders`, `getMessageDetails`
   - Tasks: `addPersonalTask`, `listPersonalTasks`, `getPersonalTask`, `editPersonalTask`, `getSubtasksForPersonalTask`, `getSubtasksForGroupTask`
   - Calendar: `add_event`, `get_event`, `search_event_all_calendars`, `update_event`, `get_calendars`
5. Clic en **Add Now**

## Paso 2: Configurar Autorización

En la pestaña **Connection**:

- **Authorization via Connection** (recomendado para equipos): El Super Admin autoriza una vez. Los tokens OAuth se comparten con todos los miembros de la organización. Cada cuenta de correo necesita su propio servidor MCP.
- **Authorization on Demand** (default): Cada usuario se autentica individualmente. Requiere abrir el navegador para completar OAuth.

⚠️ **Importante:** La configuración MCP es **por buzón, no por organización**. Si necesitas que el agente acceda a múltiples cuentas, debes crear un servidor MCP por cada una.

## Paso 3: Obtener el MCP URL

1. Ir a **Connect** en el menú lateral
2. Copiar el **MCP URL**. Formato:
   ```
   https://<nombre-server>-<id>.zohomcp.com/mcp/<api-key>/message
   ```
3. **Tratar el URL como contraseña.** La API key está embebida en la ruta.
4. Si necesitas regenerar: clic en **Regenerate API Key**

## Paso 4: Configurar Hermes

Agregar al archivo `~/.hermes/profiles/<perfil>/config.yaml`:

```yaml
mcp_servers:
  zoho_usuario01:
    command: "npx"
    args:
      - "mcp-remote"
      - "https://usuario01-XXXX.zohomcp.com/mcp/XXXX/message"
      - "--transport"
      - "http-only"
    timeout: 120
    connect_timeout: 60
    sampling:
      enabled: false
```

**CRÍTICO:**
- Usar `npx mcp-remote` (transporte stdio), NO HTTP directo
- `sampling: { enabled: false }` es OBLIGATORIO

## Paso 5: Verificar

```bash
hermes -p <perfil> mcp test zoho_usuario01
# Esperado: ✓ Connected (3-4s) ✓ Tools discovered: 14-19
```

## Múltiples cuentas

Para acceder a varias cuentas, repetir pasos 1-4 por cada buzón. La config tendrá múltiples entradas:

```yaml
mcp_servers:
  zoho_usuario01:
    command: "npx"
    args: ["mcp-remote", "https://.../message", "--transport", "http-only"]
    timeout: 120
    connect_timeout: 60
    sampling: { enabled: false }
  zoho_usuario02:
    command: "npx"
    args: ["mcp-remote", "https://.../message", "--transport", "http-only"]
    timeout: 120
    connect_timeout: 60
    sampling: { enabled: false }
```

### Documentación oficial relevante:
- [Configure Zoho MCP server](https://www.zoho.com/mail/help/mcp/configure-mcp.html)
- [Zoho MCP Authorization](https://help.zoho.com/portal/en/kb/mcp/getting-started/articles/zoho-mcp-help-documentation#Robust_Authorization_With_Flexible_Options)

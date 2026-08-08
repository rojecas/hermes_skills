# Mapeo de Account IDs — Zoho MCP

## El problema

Las herramientas de Zoho Mail MCP requieren un `accountId` como `path_variables` en cada llamada a la API. Pero este `accountId` **NO es**:

- ❌ El **User ID** de Zoho (visible en `accounts.zoho.com` → Usuarios → `8069XXXXX`)
- ❌ El **Organization ID** (visible en la consola MCP → `806941623`)
- ❌ La **dirección de correo** (ej: `usuario@dominio.com`)

Usar cualquiera de estos valores produce errores:
- IDs numéricos (User ID): `Account id X is invalid` (404)
- Emails: `URL_RULE_NOT_CONFIGURED` (404)

## La solución

El `accountId` es un ID interno generado por Zoho al añadir la cuenta al servidor MCP. Formato: `XXXXXXXXXXXXX8002` (19 dígitos). Solo se puede descubrir vía API.

### Procedimiento de descubrimiento

**Paso 1:** Agregar temporalmente estas tools admin al servidor MCP:
- `getMailAccounts`
- `getAccountDetails`
- `getOrgDetails`
- `fetchOrgUsersDetails`

**Paso 2:** Llamar a `getMailAccounts` (sin parámetros):
```json
// Respuesta incluye:
{
  "policyId": { "zoid": 806941623 },
  "zuid": 806942252,        // ← User ID (NO usar como accountId)
  "accountId": "2057888000000008002"  // ← ESTE es el accountId real
}
```

**Paso 3:** Para listar TODOS los usuarios de la organización, usar `fetchOrgUsersDetails` con el `zoid`:
```json
// Respuesta incluye para cada usuario:
{
  "displayName": "Usuario Uno",
  "accountId": "2239525000000008002",
  "primaryEmailAddress": "usuario01@dominio.com",
  "role": "member"
}
```

**Paso 4:** Guardar el mapeo y remover las 4 tools admin (no se necesitan en operación diaria).

## Mapeo de ejemplo (anonimizado)

| Usuario | Email | accountId |
|---------|-------|-----------|
| Admin TI | admin@organizacion.com | `2057888000000008002` |
| Usuario 01 | usuario01@organizacion.com | `2239525000000008002` |
| Usuario 02 | usuario02@organizacion.com | `2233514000000008002` |
| Usuario 03 | usuario03@organizacion.com | `2237958000000008002` |
| Usuario 04 | usuario04@organizacion.com | `2230561000000008002` |

## Uso en herramientas

Todas las herramientas de Zoho Mail que operan sobre una cuenta requieren `accountId` como `path_variables`:

```json
{
  "path_variables": { "accountId": "2239525000000008002" },
  "query_params": { "fields": "subject,fromAddress,receivedTime", "limit": 5 }
}
```

Las herramientas de Calendar usan `caluid` (el `uid` del calendario, no el `id`):

```json
{
  "body": {
    "caluid": "e34bd4c00f3c411f9bcf589436789fd9",
    "title": "Evento de prueba",
    "dateandtime": {
      "start": "20260813",
      "end": "20260826",
      "timezone": "America/Bogota"
    }
  }
}
```

## Estructura de argumentos MCP de Zoho

Zoho MCP usa una estructura de argumentos anidada (NO flat key-value):

```json
{
  "path_variables": { "accountId": "XXXX" },
  "query_params": { "fields": "subject,fromAddress", "limit": 5 },
  "body": { "fromAddress": "...", "toAddress": "...", "subject": "...", "content": "..." }
}
```

Cada tool especifica en su schema qué grupo de parámetros requiere. Hermes maneja esto automáticamente, pero al depurar con `curl` directo hay que respetar el anidamiento.

## Documentación oficial
- [Zoho Mail MCP Tools](https://www.zoho.com/mail/help/mcp/zoho-mail-mcp-tools.html) — lista completa de tools con sus parámetros
- [Zoho MCP Help Documentation](https://help.zoho.com/portal/en/kb/mcp/getting-started/articles/zoho-mcp-help-documentation)

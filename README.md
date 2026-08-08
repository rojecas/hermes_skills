# Hermes Skills — Colección de Integraciones

Skills, guías y patrones para integrar servicios con [Hermes Agent](https://github.com/NousResearch/hermes-agent). Cada capítulo documenta una integración completa: configuración, herramientas, pitfalls y flujos de trabajo.

## Capítulos

| Capítulo | Descripción |
|----------|-------------|
| [📧 Zoho MCP](zoho-mcp/) | Mail, Calendar y Tasks vía MCP |

## Próximos capítulos (planeados)

- 🔍 **Hermes Indexer** — indexación de archivos en shares de red (CIFS/Samba) con búsqueda FTS5
- 💬 **Noósfera Chat** — chat web con Laravel + Hermes como backend
- ⏰ **Workflows con Cron** — automatización de flujos entre servicios
- 🧾 **Facturación Electrónica** — integración con sistemas tributarios

## Estructura

```
hermes_skills/
├── README.md              ← este archivo
├── SKILL.md               ← índice para agentes IA
└── <capitulo>/
    ├── SKILL.md           ← skill para el agente
    ├── configuracion.md   ← paso a paso
    ├── lecciones.md       ← pitfalls y soluciones
    └── ...                ← documentos específicos
```

## Uso

Cada capítulo incluye un `SKILL.md` listo para copiar a `~/.hermes/skills/<capitulo>/` y ser usado por Hermes como skill. Las guías en `.md` son para humanos.

## Licencia

MIT — Usa, modifica y comparte libremente.

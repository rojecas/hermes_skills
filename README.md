# Hermes Skills — Colección de Integraciones

Skills, guías y patrones para integrar servicios con [Hermes Agent](https://github.com/NousResearch/hermes-agent). Cada capítulo documenta una integración completa: el problema que resuelve, configuración paso a paso, herramientas involucradas, pitfalls y flujos de trabajo validados.

## Capítulos

| Capítulo | ¿Qué problema resuelve? |
|----------|------------------------|
| [📧 Zoho MCP](zoho-mcp/) | Conectar Hermes al correo empresarial de Zoho para que un agente IA lea, redacte y responda correos, gestione tareas y cree eventos de calendario — sin que el equipo tenga que cambiar de herramienta. |
| [🗄️ Samba/CIFS](samba-cifs/) | Montar shares de red Windows/Samba en el servidor Linux de Hermes, indexar 100,000+ archivos con SQLite FTS5 y lograr búsquedas en <50ms vs los 60+ segundos que toma buscar directo sobre CIFS. |
| [⏰ Workflows con Cron](cron-workflows/) | Encadenar tareas entre servicios usando cron jobs de Hermes. Cuando alguien completa una tarea en Zoho, el cron detecta el cambio y dispara la siguiente acción automáticamente — sin webhooks ni desarrollo. |
| [📑 SeedDMS Automation](seeddms-automation/) | Automatizar SeedDMS vía REST API: autenticación, CRUD de documentos y carpetas, backup y restauración. Patrones para sistemas de gestión documental ISO. |
| [🎤 Deck Presentations](deck-presentations/) | Construir presentaciones HTML narradas con TTS (text-to-speech). Slides auto-play con audio por slide, navegación con teclado, estilo corporativo personalizable. |
| [🔄 Hermes + OpenCode SDD Harness](hermes-opencode-harness/) | Integrar Hermes con OpenCode CLI para Spec-Driven Development. Hermes orquesta el ciclo completo (intake → spec → implement → review → release), OpenCode ejecuta con subagentes especializados. Aprendizajes sobre pitfalls del spec-validator, ciclo SDD no lineal, y protocolo de intake campo por campo. |

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

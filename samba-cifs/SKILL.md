---
name: hermes-skills/samba-cifs
description: Use when connecting Hermes to Windows/Samba file shares for indexing.
---

# Integración Samba/CIFS — Conectar Hermes a la red empresarial

Guía para integrar Hermes Agent en la infraestructura de TI de una empresa, permitiendo que el agente acceda a archivos en shares de red Windows/Samba, los indexe y los busque eficientemente.

## Documentos de referencia

| Documento | Cuándo cargar |
|-----------|--------------|
| `montaje-shares.md` | Configuración de montaje CIFS/SMB |
| `hermes-indexer.md` | Indexación y búsqueda FTS5 |
| `lecciones-aprendidas.md` | Pitfalls y soluciones |

## Arquitectura típica

```
Servidor Linux (Hermes)                    Servidor Windows / NAS
├── /mnt/shares/                           ├── Share: Documentos (\\server\docs)
│   ├── docs/          ←── CIFS ──→       ├── Share: Tecnico (\\server\tecnico)
│   ├── tecnico/       ←── CIFS ──→       ├── Share: Calidad (\\server\calidad)
│   └── comercial/     ←── CIFS ──→       └── Share: Comercial (\\server\comercial)
│
├── Hermes Agent
│   └── hermes-indexer → indexa /mnt/shares/ → SQLite FTS5
│
└── Hermes Index Query → búsquedas <50ms vs CIFS directo (>30s)
```

## Flujo de trabajo

1. **Montar** los shares Windows/Samba en el servidor Linux de Hermes vía CIFS
2. **Indexar** con `hermes-indexer` — genera índices JSON + base SQLite FTS5
3. **Consultar** con `hermes-index-query` — búsquedas en <50ms
4. **Automatizar** con cron — reindexación diaria nocturna

## Por qué indexar en vez de buscar directo en CIFS

| Método | Velocidad | Razón |
|--------|:---------:|-------|
| Búsqueda directa CIFS | 30-120s | Latencia de red, protocolo SMB lento en búsqueda recursiva |
| Índice FTS5 (SQLite) | <50ms | Búsqueda full-text local |
| Índice JSON | ~1-5s | Búsqueda secuencial en archivo |

## Verificación

```bash
# Verificar montajes
mount | grep cifs

# Verificar índices
ls -lh /ruta/indices/
hermes-index-query --count

# Buscar
hermes-index-query --query "palabra clave"
```

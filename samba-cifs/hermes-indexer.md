# Hermes Indexer — Indexación y búsqueda FTS5

Una vez montados los shares de red, el siguiente paso es indexarlos para que Hermes pueda buscar archivos instantáneamente sin depender de la lenta búsqueda directa sobre CIFS.

## El problema

Buscar archivos recursivamente sobre un share CIFS montado puede tomar **30-120 segundos** por consulta. Esto hace inviable que un agente IA interactúe con los archivos en tiempo real.

## La solución

Indexar los shares localmente usando SQLite con FTS5 (Full-Text Search):

```
                         ┌─→ /ruta/indices/share_docs.json
/mnt/shares/docs/ ──→ indexer ──→ /ruta/indices/share_tecnico.json
/mnt/shares/tecnico/ ──→        ──→ /ruta/indices/indices.db (SQLite FTS5)
```

## Instalación

```bash
# Requisitos
pip install hermes-indexer  # o copiar hermes-indexer a ~/.local/bin/

# Verificar
hermes-indexer --help
hermes-index-query --help
```

## Configuración: el archivo `.indexrules`

`.indexrules` es un archivo **JSON** que le dice al indexador **qué carpetas del share debe indexar** y **cómo organizar los resultados en particiones**. Se coloca en la raíz del share o unidad de red (ej: `W:\.indexrules`), no en el proyecto.

### ¿Por qué existe?

Un share de red empresarial puede tener 100,000+ archivos en cientos de subcarpetas. Sin `.indexrules`, el indexador tendría que procesar todo como una sola masa — las búsquedas serían lentas y no se podría filtrar por área (calidad, técnico, comercial, etc.).

`.indexrules` divide el share en **particiones lógicas**: cada partición es una carpeta raíz que se indexa por separado y produce su propio archivo JSON de índice.

### Estructura

```json
// .indexrules — define qué carpetas indexar, cuáles ignorar y cómo particionarlas
// Cada clave bajo 'partitions' define una partición independiente
{
  "description": "Descripción humana de la unidad",
  "root_path": "//192.168.1.10/Share",        // (opcional) default: //192.168.1.10/{letra}
  "exclude": {                                  // (opcional)
    "dirs": ["Temp", "Carpeta"],
    "patterns": [".0*", "*_archivos"]
  },
  "partitions": {
    "V_iso9001": {
      "root": "ISO 9001",                      // subdirectorio, o "." para raíz
      "description": "Sistema de Gestión de Calidad ISO 9001",
      "include_only": ["Sub1", "Sub2"]         // solo con root="."
    }
  }
}
```

### ¿Qué va en cada campo?

| Campo | Obligatorio | Descripción |
|-------|:----------:|-------------|
| `description` | ✅ | Nombre descriptivo de la unidad. Aparece en logs y `_meta.json` |
| `root_path` | ❌ | Ruta UNC del share. Default: `//192.168.1.10/{letra}` |
| `exclude.dirs` | ❌ | Nombres exactos de carpetas a excluir |
| `exclude.patterns` | ❌ | Patrones glob (`.0*` = archivo muerto) |
| `partitions.{n}.root` | ✅ | Subdirectorio a indexar, o `"."` para la raíz |
| `partitions.{n}.description` | ❌ | Texto libre para documentar |
| `partitions.{n}.include_only` | ❌ | Solo con `root: "."` — lista de carpetas a incluir |

### Ejemplo real

```json
{
  "description": "Calidad, ISO, SST (SIC)",
  "root_path": "//192.168.1.10/SIC",
  "exclude": {"dirs": ["Temp", "temp"], "patterns": []},
  "partitions": {
    "V_iso9001": {"root": "ISO 9001", "description": "Sistema de Gestión de Calidad ISO 9001"},
    "V_iso17025": {"root": "ISO 17025", "description": "Acreditación de Laboratorios ISO 17025"},
    "V_iso45001": {"root": "ISO 45001", "description": "Seguridad y Salud en el Trabajo ISO 45001"},
    "V_bpl_oms": {"root": "BPL OMS", "description": "Buenas Prácticas de Laboratorio OMS"}
  }
}
```

**Nota:** para agrupar varias carpetas pequeñas de la raíz en una sola partición, usar `root: "."` con `include_only`:

```json
"X_admin": {
  "root": ".",
  "description": "Carpetas administrativas agrupadas",
  "include_only": ["Administracion", "Area Fisica", "Papeleria", "Plantillas"]
}
```

### ¿Qué produce cada partición?

Para la configuración anterior, el indexador genera un JSON por partición:

```
/ruta/indices/
├── V_iso9001.json      ← metadatos + lista de archivos de /mnt/inasc/V/ISO 9001
├── V_iso17025.json     ← metadatos + lista de archivos de /mnt/inasc/V/ISO 17025
├── V_iso45001.json     ← metadatos + lista de archivos de /mnt/inasc/V/ISO 45001
├── V_bpl_oms.json      ← metadatos + lista de archivos de /mnt/inasc/V/BPL OMS
├── _meta.json          ← metadatos globales (unidades, total de archivos, duración)
└── hermes_index.sqlite ← base SQLite FTS5 consolidada (búsquedas <50ms)
```

Cada JSON contiene:
- `meta`: unit, partition, total_files, version
- `files[]`: array con `relative_path`, `filename`, `prefix`, `document_type`, `size_bytes`, `last_modified`, `year`, `client`, `tags`…
- `directories[]`: estructura de carpetas

## Indexación

```bash
# Primera indexación (completa) — escanea todas las unidades con .indexrules
hermes-indexer --output /ruta/indices --verbose

# Indexar solo una unidad (V, X, Y, W)
hermes-indexer --output /ruta/indices --unit V --verbose

# Reindexar forzando (ignora el índice anterior)
hermes-indexer --output /ruta/indices --force

# Generar base SQLite FTS5 para búsqueda rápida (migra los JSON ya existentes)
hermes-indexer --output /ruta/indices --build-db
```

**Tiempos típicos** para ~120,000 archivos:
- Indexación completa: 5-15 minutos
- Generación SQLite: 30-90 segundos
- Tamaño de la base: ~60-80 MB

## Consultas

```bash
# Búsqueda FTS5 (más rápida, <50ms)
hermes-index-query --query "informe calibracion HPLC"

# Buscar por cliente
hermes-index-query --client "NOMBRE_CLIENTE"

# Buscar por año
hermes-index-query --year 2026 --query "certificado"

# Filtrar por unidad/share
hermes-index-query --unit V --query "matriz legal"

# Filtrar por tipo de archivo
hermes-index-query --type pdf --query "procedimiento"

# Listar archivos recientes
hermes-index-query --recent

# Solo contar resultados
hermes-index-query --query "calibracion" --count

# Buscar por prefijo de documento
hermes-index-query --prefix DC --year 2026 --client "CLIENTE_X"
```

## Automatización con cron

Reindexar dos veces al día, en horas laborales, para mantener los índices actualizados:

```bash
# En crontab del sistema (NO a las 2 AM — el servidor NAS se apaga de noche)
0 13 * * * hermes-indexer --output /ruta/indices --build-db
0 16 * * * hermes-indexer --output /ruta/indices --build-db
```

**⚠️ Lección aprendida:** NO programar de noche (2 AM). El servidor NAS (uwa) se apaga de noche (~8pm–7:30am), así que un cron nocturno falla con "No route to host". Programar en horas laborales (13:00 y 16:00), cuando el NAS está encendido.

## Uso desde Hermes

Con el índice disponible, el agente puede:

1. Buscar archivos instantáneamente: "¿cuántas cotizaciones enviamos en agosto?"
2. Encontrar documentos por cliente: "busca todos los certificados de CLIENTE_X"
3. Verificar vencimientos: "¿qué documentos ISO vencen este mes?"
4. Navegar la estructura: "¿qué carpetas hay en el share de calidad?"

## Referencia de flags

### `hermes-index-query` (búsquedas)

| Flag | Descripción |
|------|-------------|
| `--query` | Búsqueda FTS5 (full-text) |
| `--client` | Filtrar por nombre de cliente |
| `--year` | Filtrar por año |
| `--unit` | Filtrar por letra de unidad (V, W, X, Y) |
| `--type` | Filtrar por tipo de documento (Procedimiento, Formato, Manual…) |
| `--prefix` | Filtrar por prefijo de documento (GC, AD, ST, DC…) |
| `--recent` | Archivos más recientes (N días) |
| `--count` | Solo mostrar conteo |
| `--limit` | Máximo de resultados |
| `--format` | `json` (default) o `text` |

### `hermes-indexer` (indexación)

| Flag | Descripción |
|------|-------------|
| `--output <dir>` | Directorio de salida de los JSON (obligatorio) |
| `--unit` | Indexar solo una unidad (V, X, Y, W) |
| `--force` | Forzar aunque el índice esté vigente |
| `--verbose` | Mostrar progreso en stderr |
| `--hash` | Calcular MD5 (lento en CIFS) |
| `--build-db` | Migrar JSONs a SQLite FTS5 tras indexar |
| `--build-db-only` | Solo construir SQLite desde JSONs existentes |

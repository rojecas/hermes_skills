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

`.indexrules` es un archivo YAML que le dice al indexador **qué carpetas del share debe indexar** y **cómo organizar los resultados en particiones**. Se coloca en la raíz del proyecto o en `~/.hermes/`.

### ¿Por qué existe?

Un share de red empresarial puede tener 100,000+ archivos en cientos de subcarpetas. Sin `.indexrules`, el indexador tendría que procesar todo como una sola masa — las búsquedas serían lentas y no se podría filtrar por área (calidad, técnico, comercial, etc.).

`.indexrules` divide el share en **particiones lógicas**: cada partición es una carpeta raíz que se indexa por separado y produce su propio archivo JSON de índice.

### Estructura

```yaml
# .indexrules
# Cada entrada bajo 'partitions' define una partición independiente
partitions:
  - name: nombre_corto        # Identificador único para esta partición
    path: /ruta/a/la/carpeta  # Ruta absoluta en el sistema de archivos
    prefix: GC, AD            # (opcional) Solo indexar archivos que empiecen con estos prefijos
    description: Descripción  # (opcional) Para documentar qué contiene
```

### ¿Qué va en cada campo?

| Campo | Obligatorio | Descripción |
|-------|:----------:|-------------|
| `name` | ✅ | Nombre corto, sin espacios. Se usa en `--partition` y como nombre del archivo JSON |
| `path` | ✅ | Ruta absoluta a la carpeta raíz de esta partición |
| `prefix` | ❌ | Lista de prefijos separados por coma. Solo indexa archivos cuyo nombre empiece con uno de estos. Ej: `GC, AD, SS` |
| `description` | ❌ | Texto libre para documentar. Aparece en los metadatos del índice |

### Ejemplo real (anonimizado)

```yaml
partitions:
  - name: calidad
    path: /mnt/shares/calidad
    prefix: GC, AD, SS
    description: Sistema de Gestión de Calidad — ISO 9001, 17025, 45001

  - name: tecnico
    path: /mnt/shares/tecnico
    prefix: ST, CS, CT
    description: Servicio Técnico (ST), Metrología (CS), Soporte Técnico (CT)

  - name: comercial
    path: /mnt/shares/comercial
    prefix: DC
    description: División Comercial — cotizaciones, órdenes de compra, clientes

  - name: documentos
    path: /mnt/shares/documentos
    description: Documentos generales (sin filtro de prefijo)
```

**Nota:** La última partición (`documentos`) no tiene `prefix`, así que indexa **todos** los archivos de esa carpeta. Esto es útil para shares de propósito general donde no aplica un sistema de prefijos.

### ¿Qué produce cada partición?

Para la configuración anterior, el indexador genera:

```
/ruta/indices/
├── calidad.json       ← metadatos + lista de archivos de /mnt/shares/calidad
├── tecnico.json       ← metadatos + lista de archivos de /mnt/shares/tecnico
├── comercial.json     ← metadatos + lista de archivos de /mnt/shares/comercial
├── documentos.json    ← metadatos + lista de archivos de /mnt/shares/documentos
└── indices.db         ← base SQLite FTS5 consolidada (búsquedas <50ms)
```

Cada JSON contiene:
- `meta`: nombre, ruta, prefijos, fecha de generación, total de archivos
- `files`: array con `[ruta_relativa, nombre, extensión, tamaño, fecha_modificación]` de cada archivo

## Indexación

```bash
# Primera indexación (completa)
hermes-indexer --all

# Indexar solo una partición
hermes-indexer --partition tecnico

# Reindexar todo (útil al agregar particiones nuevas)
hermes-indexer --all --force

# Generar base SQLite FTS5 para búsqueda rápida
hermes-indexer --build-db
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

Reindexar cada noche para mantener los índices actualizados:

```bash
# En Hermes: cronjob create
hermes-indexer --all --force && hermes-indexer --build-db
```

Programar a las 2:00 AM (cuando no hay actividad en los shares):
```
0 2 * * * cd /ruta/indices && hermes-indexer --all --force && hermes-indexer --build-db
```

## Uso desde Hermes

Con el índice disponible, el agente puede:

1. Buscar archivos instantáneamente: "¿cuántas cotizaciones enviamos en agosto?"
2. Encontrar documentos por cliente: "busca todos los certificados de CLIENTE_X"
3. Verificar vencimientos: "¿qué documentos ISO vencen este mes?"
4. Navegar la estructura: "¿qué carpetas hay en el share de calidad?"

## Referencia de flags

| Flag | Descripción |
|------|-------------|
| `--query` | Búsqueda FTS5 (full-text) |
| `--client` | Filtrar por nombre de cliente |
| `--year` | Filtrar por año |
| `--unit` | Filtrar por letra de unidad (V, W, X, Y) |
| `--type` | Filtrar por extensión (pdf, xlsx, docx) |
| `--prefix` | Filtrar por prefijo de documento (GC, AD, ST, DC...) |
| `--recent` | Archivos más recientes |
| `--count` | Solo mostrar conteo |
| `--build-db` | Reconstruir índice SQLite FTS5 |
| `--all` | Indexar todas las particiones |
| `--partition` | Indexar una partición específica |
| `--force` | Forzar reindexación completa |

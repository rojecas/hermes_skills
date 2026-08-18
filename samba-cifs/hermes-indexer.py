#!/usr/bin/env python3
"""hermes-indexer v2.1 — Indexa unidades Samba con particiones por dominio.

Las reglas de indexado se definen en .indexrules (JSON) en la raíz de cada unidad.
Sin configuración hardcodeada — auto-descubrimiento.

Uso:
    hermes-indexer --output <dir> [--force] [--verbose] [--unit V|X|Y|W]

Formato de .indexrules:
    {
      "description": "...",
      "root_path": "//server/...",
      "exclude": {"dirs": ["Temp"], "patterns": []},
      "partitions": {
        "U_nombre": {"root": "Carpeta", "description": "...", "include_only": [...]}
      }
    }
"""

import argparse
import hashlib
import json
import os
import re
import sys
import time
from datetime import datetime, timezone, timedelta

VERSION = "2.2"
COLOMBIA_TZ = timezone(timedelta(hours=-5))

# ═══════════════════════════════════════════════════════════════════════════════
# Configuración de unidades y particiones
# ═══════════════════════════════════════════════════════════════════════════════

# Exclusiones globales de archivos (no se indexan nunca)
EXCLUDE_FILES = {
    "Thumbs.db", ".DS_Store", "desktop.ini",
}

EXCLUDE_EXTENSIONS = {".tmp", ".bak"}

EXCLUDE_FILE_PATTERNS = ["~$*"]  # archivos temporales de Office

# Directorios excluidos globalmente
EXCLUDE_DIRS_GLOBAL = {"$RECYCLE.BIN", ".Trash", "System Volume Information"}

# Directorios excluidos (nombres exactos o patrones glob)
EXCLUDE_DIR_PATTERNS = [
    "*_archivos",   # artefactos de páginas web guardadas
]

# ═══════════════════════════════════════════════════════════════════════════════
# Descubrimiento de unidades vía .indexrules
# ═══════════════════════════════════════════════════════════════════════════════

MOUNTS_BASE = "/mnt/shares"


def _load_rules(path: str) -> dict | None:
    """Carga y valida un archivo .indexrules."""
    try:
        with open(path) as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        print(f"  Error leyendo {path}: {e}", file=sys.stderr)
        return None


def discover_units(unit_filter: str | None = None) -> dict:
    """Descubre unidades que tengan .indexrules en su raíz.

    Retorna {letter: config_dict}.
    """
    units = {}
    if not os.path.isdir(INASC_MOUNTS):
        return units

    for entry in sorted(os.listdir(INASC_MOUNTS)):
        letter = entry.upper()
        if unit_filter and letter != unit_filter.upper():
            continue

        mount = os.path.join(INASC_MOUNTS, entry)
        if not os.path.isdir(mount):
            continue

        rules_path = os.path.join(mount, ".indexrules")
        if not os.path.isfile(rules_path):
            continue

        rules = _load_rules(rules_path)
        if rules is None:
            continue

        units[letter] = {
            "mount": mount,
            "description": rules.get("description", letter),
            "root_path": rules.get("root_path", f"//server/{letter}"),
            "exclude_dirs": set(rules.get("exclude", {}).get("dirs", [])),
            "exclude_patterns": rules.get("exclude", {}).get("patterns", []),
            "partitions": rules.get("partitions", {}),
        }

    return units

# ═══════════════════════════════════════════════════════════════════════════════
# Extensiones a indexar
# ═══════════════════════════════════════════════════════════════════════════════

EXTENSIONS = {".xlsx", ".xls", ".xlsm", ".doc", ".docx", ".pdf", ".csv", ".zip",
              ".jpg", ".jpeg", ".png", ".dwg", ".dxf", ".pptx", ".ppt", ".txt",
              ".xml", ".html", ".msg", ".eml"}

# ═══════════════════════════════════════════════════════════════════════════════
# Inferencia semántica (igual que v1.1)
# ═══════════════════════════════════════════════════════════════════════════════

AREA_PREFIXES = ["AD", "GC", "DC", "ST", "CS", "AC", "RH", "CF", "SS", "CT"]

DOC_TYPES = {
    "FR": "Formato", "PR": "Procedimiento", "MT": "Matriz",
    "MA": "Manual",  "PL": "Plan",          "PT": "Protocolo",
    "PG": "Programa","P": "Política",       "R": "Reglamento", "A": "Apoyo",
}

TAG_KEYWORDS = {
    "calibración": ["calibracion", "calibración", "metrologia", "metrología"],
    "mantenimiento": ["mantenimiento", "servicio técnico", "servicio tecnico", "reparacion", "reparación"],
    "calidad": ["calidad", "iso 9001", "iso9001", "sgc"],
    "sst": ["sst", "iso 45001", "iso45001", "seguridad", "salud"],
    "comercial": ["comercial", "cotizacion", "cotización", "ventas", "oc", "factura"],
    "contable": ["contable", "contabilidad", "finanza", "financier", "banco", "pago"],
    "legal": ["legal", "contrato", "abogado"],
    "personal": ["personal", "empleado", "rh", "hoja de vida"],
    "compras": ["compra", "proveedor", "almacen", "inventario"],
    "capacitacion": ["capacitacion", "capacitación", "formacion", "formación"],
    "iso17025": ["17025", "iso 17025"],
    "indice": ["indice", "índice"],
    "registro": ["registro", "regmto", "regcal"],
}

CLIENTS = [
    "Cliente Uno", "Cliente Dos", "Cliente Tres", "Cliente Cuatro", "Cliente Cinco",
    "Cliente Seis", "Cliente Siete", "Cliente Ocho", "Cliente Nueve", "Cliente Diez",
    "Cliente Once", "Empresa Propia",
]

EQUIPMENT_PATTERNS = [
    r"HACH\s*DR\d+", r"Agilent\s*\d+", r"Espectrofotómetro",
    r"Cromatógrafo", r"Balanza", r"Termómetro",
    r"pHmetro", r"Conductímetro", r"Multímetro",
]


def infer_prefix(filename: str) -> str | None:
    name = os.path.splitext(filename)[0].upper().replace(" ", "").replace("-", "").replace("_", "")
    m = re.match(r"^([A-Z]{2})([A-Z]{1,2})(\d{2,4})", name)
    if m and m.group(1) in AREA_PREFIXES and m.group(2) in DOC_TYPES:
        return f"{m.group(1)}{m.group(2)}{m.group(3)}"
    for prefix in AREA_PREFIXES:
        if name.startswith(prefix):
            rest = name[len(prefix):]
            m2 = re.match(r"^([A-Z]{1,2})(\d+)", rest)
            return f"{prefix}{m2.group(1)}{m2.group(2)}" if m2 else prefix
    if name.startswith("IS") or "IS-" in name:
        return "IS"
    return None


def infer_document_type(filename: str, prefix: str | None) -> str | None:
    if prefix and len(prefix) >= 4 and prefix[2:4] in DOC_TYPES:
        return DOC_TYPES[prefix[2:4]]
    for code, desc in DOC_TYPES.items():
        if code in filename.upper():
            return desc
    return None


def infer_year(filename: str, path: str) -> int | None:
    for text in (filename, path):
        m = re.search(r"(20\d{2})", text)
        if m and 2000 <= int(m.group(1)) <= 2099:
            return int(m.group(1))
    return None


def infer_revision_date(filename: str) -> str | None:
    m = re.search(r"[_\-]?(20\d{2})[_-]?(0[1-9]|1[0-2])", filename)
    if m:
        return f"{m.group(1)}-{m.group(2)}"
    m = re.search(r"(20\d{2})", filename)
    return m.group(1) if m else None


def infer_status(revision_date: str | None, year: int | None) -> str | None:
    if not revision_date or not year:
        return None
    now = datetime.now(COLOMBIA_TZ)
    if year < now.year:
        return "posible_vencido"
    if year == now.year:
        m = re.match(r"(\d{4})-(\d{2})", revision_date)
        if m:
            rev_month = int(m.group(2))
            if rev_month < now.month - 2:
                return "posible_vencido"
            if rev_month <= now.month:
                return "vigente"
        return "vigente"
    return "proximo_vencer"


def infer_client(path: str) -> str | None:
    for client in CLIENTS:
        if client.lower() in path.lower():
            return client
    return None


def infer_equipment(filename: str, path: str) -> str | None:
    for pat in EQUIPMENT_PATTERNS:
        m = re.search(pat, filename + " " + path, re.IGNORECASE)
        if m:
            return m.group(0)
    return None


def infer_tags(path: str, filename: str) -> list[str]:
    text = (path + " " + filename).lower()
    return [tag for tag, kws in TAG_KEYWORDS.items() if any(kw in text for kw in kws)]


# ═══════════════════════════════════════════════════════════════════════════════
# Filtros de exclusión
# ═══════════════════════════════════════════════════════════════════════════════

def should_exclude_dir(dirname: str, exclude_dirs: set, exclude_patterns: list[str]) -> bool:
    """True si el directorio debe ser excluido."""
    import fnmatch
    if dirname in EXCLUDE_DIRS_GLOBAL:
        return True
    if dirname in exclude_dirs:
        return True
    for pat in EXCLUDE_DIR_PATTERNS + exclude_patterns:
        if fnmatch.fnmatch(dirname, pat):
            return True
    return False


def should_exclude_file(filename: str) -> bool:
    """True si el archivo debe ser excluido."""
    import fnmatch
    if filename in EXCLUDE_FILES:
        return True
    ext = os.path.splitext(filename)[1].lower()
    if ext in EXCLUDE_EXTENSIONS:
        return True
    for pat in EXCLUDE_FILE_PATTERNS:
        if fnmatch.fnmatch(filename, pat):
            return True
    return False


# ═══════════════════════════════════════════════════════════════════════════════
# Indexado de particiones
# ═══════════════════════════════════════════════════════════════════════════════

def index_partition(unit: str, mount: str, partition_name: str, partition_root: str,
                    exclude_dirs: set, exclude_patterns: list[str],
                    verbose: bool, do_hash: bool = False,
                    include_only: list[str] | None = None,
                    global_exclude_dirs: set | None = None) -> dict | None:
    """Indexa una partición (subdirectorio) de una unidad.

    Si include_only no es None, solo se indexan los subdirectorios listados
    (útil para particiones que agrupan carpetas dispersas).
    global_exclude_dirs: directorios a excluir incluso en include_only (ej: ELibrary).
    """
    root_path = os.path.join(mount, partition_root)
    if not os.path.isdir(root_path):
        if verbose:
            print(f"  [{partition_name}] No encontrado: {root_path}", file=sys.stderr)
        return None

    # Si hay include_only, filtrar directorios de primer nivel
    if include_only is not None:
        top_level_roots = []
        for name in include_only:
            p = os.path.join(mount, name)
            if os.path.isdir(p):
                top_level_roots.append(p)
        if not top_level_roots:
            if verbose:
                print(f"  [{partition_name}] Ningún subdirectorio include_only encontrado", file=sys.stderr)
            return None
    else:
        top_level_roots = [root_path]

    files = []
    dirs_seen = {}
    file_count = 0
    start = time.time()

    for top_root in top_level_roots:
        for walk_root, dirnames, filenames in os.walk(top_root):
            # Filtrar directorios excluidos
            dirnames[:] = [d for d in dirnames
                           if not should_exclude_dir(d, exclude_dirs, exclude_patterns)]

            rel_root = os.path.relpath(walk_root, mount)
            if rel_root == ".":
                rel_root = ""

            # Filtrar archivos
            valid_files = [f for f in filenames
                           if not should_exclude_file(f)
                           and os.path.splitext(f)[1].lower() in EXTENSIONS]

            if not valid_files and not dirnames:
                continue

            # Registrar directorio
            if rel_root:
                dirs_seen[rel_root] = {
                    "path": rel_root,
                    "name": os.path.basename(walk_root),
                    "file_count": 0,
                }

            for fname in valid_files:
                full_path = os.path.join(walk_root, fname)
                rel_path = os.path.join(rel_root, fname) if rel_root else fname

                try:
                    st = os.stat(full_path)
                    size = st.st_size
                    mtime = datetime.fromtimestamp(st.st_mtime, tz=COLOMBIA_TZ).isoformat()
                except OSError:
                    continue

                hash_md5 = "0" * 32
                if do_hash and size <= 5 * 1024 * 1024:
                    try:
                        h = hashlib.md5()
                        with open(full_path, "rb") as fh:
                            for chunk in iter(lambda: fh.read(65536), b""):
                                h.update(chunk)
                        hash_md5 = h.hexdigest()
                    except OSError:
                        pass

                file_id = hashlib.md5(rel_path.encode()).hexdigest()[:10]
                prefix = infer_prefix(fname)
                doc_type = infer_document_type(fname, prefix)
                year = infer_year(fname, rel_path)
                rev_date = infer_revision_date(fname)
                status = infer_status(rev_date, year)

                files.append({
                    "id": file_id,
                    "relative_path": rel_path,
                    "filename": fname,
                    "prefix": prefix,
                    "document_type": doc_type,
                    "size_bytes": size,
                    "last_modified": mtime,
                    "hash_md5": hash_md5,
                    "revision_date": rev_date,
                    "status": status,
                    "client": infer_client(rel_path),
                    "equipment": infer_equipment(fname, rel_path),
                    "year": year,
                    "tags": infer_tags(rel_path, fname),
                })

                if rel_root in dirs_seen:
                    dirs_seen[rel_root]["file_count"] += 1

                file_count += 1
                if verbose and file_count % 500 == 0:
                    elapsed = int(time.time() - start)
                    print(f"  [{partition_name}] {file_count} archivos ({elapsed}s)...", file=sys.stderr)

    duration_ms = int((time.time() - start) * 1000)
    if verbose:
        print(f"  [{partition_name}] {file_count} archivos en {duration_ms}ms", file=sys.stderr)

    return {
        "files": files,
        "directories": sorted(dirs_seen.values(), key=lambda d: d["path"]),
        "file_count": file_count,
        "duration_ms": duration_ms,
    }


def build_root_directories(partitions: dict) -> list[dict]:
    """Construye el mapa root_directories replicado en cada partición."""
    result = []
    for pname, pconfig in partitions.items():
        result.append({
            "name": pconfig["root"] if pconfig["root"] != "." else "(raíz)",
            "partition": f"{pname}.json",
            "description": pconfig.get("description", ""),
        })
    return result


# ═══════════════════════════════════════════════════════════════════════════════
# Escritura atómica
# ═══════════════════════════════════════════════════════════════════════════════

def atomic_write_json(path: str, data: dict):
    tmp = path + ".tmp"
    bak = path + ".bak"
    if os.path.exists(path):
        try:
            os.rename(path, bak)
        except OSError:
            pass
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.rename(tmp, path)


# ═══════════════════════════════════════════════════════════════════════════════
# Build SQLite
# ═══════════════════════════════════════════════════════════════════════════════

def build_sqlite_db(output_dir: str, db_path: str, verbose: bool = False):
    """Migra todos los JSON de índice a una base SQLite."""
    import sqlite3

    if os.path.exists(db_path):
        os.remove(db_path)

    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA cache_size=-16000")

    conn.execute("""
        CREATE TABLE partitions (
            id TEXT PRIMARY KEY,
            unit TEXT NOT NULL,
            name TEXT NOT NULL,
            description TEXT,
            total_files INTEGER,
            generated_at TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE files (
            id TEXT NOT NULL,
            partition_id TEXT NOT NULL,
            relative_path TEXT NOT NULL,
            filename TEXT NOT NULL,
            prefix TEXT,
            document_type TEXT,
            size_bytes INTEGER,
            last_modified TEXT,
            revision_date TEXT,
            status TEXT,
            client TEXT,
            equipment TEXT,
            year INTEGER,
            tags TEXT,
            PRIMARY KEY (partition_id, id)
        )
    """)
    conn.execute("""
        CREATE TABLE directories (
            partition_id TEXT NOT NULL,
            path TEXT NOT NULL,
            name TEXT NOT NULL,
            file_count INTEGER DEFAULT 0,
            PRIMARY KEY (partition_id, path)
        )
    """)
    conn.execute("""
        CREATE TABLE root_directories (
            partition_id TEXT NOT NULL,
            name TEXT NOT NULL,
            target_partition TEXT NOT NULL,
            description TEXT
        )
    """)
    conn.execute("CREATE INDEX idx_files_prefix ON files(prefix)")
    conn.execute("CREATE INDEX idx_files_year ON files(year)")
    conn.execute("CREATE INDEX idx_files_client ON files(client)")
    conn.execute("CREATE INDEX idx_files_status ON files(status)")
    conn.execute("CREATE INDEX idx_files_doc_type ON files(document_type)")
    conn.execute("CREATE INDEX idx_files_filename ON files(filename)")

    # FTS5: búsqueda full-text sobre filename, path, cliente, equipo, tags
    conn.execute("""
        CREATE VIRTUAL TABLE files_fts USING fts5(
            filename,
            relative_path,
            client,
            equipment,
            tags,
            content='files',
            content_rowid='rowid'
        )
    """)

    json_files = sorted(
        f for f in os.listdir(output_dir)
        if f.endswith('.json') and f != '_meta.json' and not f.endswith('.bak')
    )

    total_files = 0
    for jf in json_files:
        path = os.path.join(output_dir, jf)
        try:
            with open(path) as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            continue

        meta = data.get('meta', {})
        partition_id = meta.get('partition', jf.replace('.json', ''))
        unit = meta.get('unit', '?')

        conn.execute(
            "INSERT INTO partitions VALUES (?,?,?,?,?,?)",
            (partition_id, unit, partition_id,
             meta.get('partition_description', ''),
             meta.get('total_files', 0),
             meta.get('generated_at', ''))
        )

        files = data.get('files', [])
        for f in files:
            conn.execute(
                "INSERT INTO files VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (f['id'], partition_id, f['relative_path'], f['filename'],
                 f.get('prefix'), f.get('document_type'), f.get('size_bytes'),
                 f.get('last_modified'), f.get('revision_date'), f.get('status'),
                 f.get('client'), f.get('equipment'), f.get('year'),
                 json.dumps(f.get('tags', [])))
            )

        dirs = data.get('directories', [])
        for d in dirs:
            conn.execute(
                "INSERT INTO directories VALUES (?,?,?,?)",
                (partition_id, d['path'], d['name'], d.get('file_count', 0))
            )

        for r in data.get('root_directories', []):
            conn.execute(
                "INSERT INTO root_directories VALUES (?,?,?,?)",
                (partition_id, r['name'], r.get('partition', ''),
                 r.get('description', ''))
            )

        total_files += len(files)
        if verbose:
            print(f"  {jf}: {len(files):,} archivos → SQLite", file=sys.stderr)

    conn.execute("ANALYZE")
    conn.execute("INSERT INTO files_fts(files_fts) VALUES('rebuild')")
    conn.commit()
    conn.close()

    size_mb = os.path.getsize(db_path) / (1024 * 1024)
    if verbose:
        print(f"\n  SQLite: {total_files:,} archivos en {size_mb:.1f} MB", file=sys.stderr)
    else:
        print(f"✓ SQLite: {total_files:,} archivos en {size_mb:.1f} MB")


# ═══════════════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="hermes-indexer v2.0 — Índice semántico")
    parser.add_argument("--output", required=True, help="Directorio de salida")
    parser.add_argument("--unit", help="Indexar solo una unidad (V, X, Y, W)")
    parser.add_argument("--force", action="store_true", help="Forzar aunque índice vigente")
    parser.add_argument("--verbose", action="store_true", help="Mostrar progreso")
    parser.add_argument("--hash", action="store_true", help="Calcular MD5 (lento en CIFS)")
    parser.add_argument("--build-db", nargs="?", const=True,
                        help="Migrar JSONs a SQLite después de indexar")
    parser.add_argument("--build-db-only", nargs="?", const=True,
                        help="Solo migrar JSONs existentes a SQLite (sin indexar)")
    args = parser.parse_args()

    output_dir = args.output
    os.makedirs(output_dir, exist_ok=True)

    units_to_process = discover_units(args.unit)

    if not units_to_process:
        print("No se encontraron unidades con .indexrules.", file=sys.stderr)
        print(f"Escanea {INASC_MOUNTS}/*/ en busca de .indexrules.", file=sys.stderr)
        return

    if args.verbose:
        print(f"hermes-indexer v{VERSION}", file=sys.stderr)
        print(f"Destino: {output_dir}", file=sys.stderr)

    # --build-db-only: saltar indexado, solo construir SQLite
    if args.build_db_only:
        db_path = args.build_db_only if isinstance(args.build_db_only, str) else os.path.join(output_dir, "hermes_index.sqlite")
        build_sqlite_db(output_dir, db_path, args.verbose)
        return

    start_total = time.time()
    all_results = {}
    total_files = 0

    for unit, config in units_to_process.items():
        mount = config["mount"]

        if not os.path.isdir(mount):
            if args.verbose:
                print(f"\n[{unit}] No montado en {mount}", file=sys.stderr)
            all_results[unit] = {"status": "unavailable", "partitions": {}}
            continue

        if args.verbose:
            print(f"\n[{unit}] {config['description']}", file=sys.stderr)

        root_dirs = build_root_directories(config["partitions"])
        now_iso = datetime.now(COLOMBIA_TZ).isoformat()
        partition_results = {}

        for pname, pconfig in config["partitions"].items():
            if args.verbose:
                print(f"  → {pname}: {pconfig['root']}", file=sys.stderr)

            data = index_partition(
                unit=unit,
                mount=mount,
                partition_name=pname,
                partition_root=pconfig["root"],
                exclude_dirs=config["exclude_dirs"],
                exclude_patterns=config["exclude_patterns"],
                verbose=args.verbose,
                do_hash=args.hash,
                include_only=pconfig.get("include_only"),
            )

            if data is None:
                partition_results[pname] = {"status": "not_found", "files": 0}
                continue

            doc = {
                "meta": {
                    "generated_at": now_iso,
                    "generator_version": VERSION,
                    "source": "hermes-fs-indexer",
                    "unit": unit,
                    "partition": pname,
                    "partition_description": pconfig["description"],
                    "total_files": data["file_count"],
                },
                "root_directories": root_dirs,
                "files": data["files"],
                "directories": data["directories"],
            }

            out_path = os.path.join(output_dir, f"{pname}.json")
            atomic_write_json(out_path, doc)

            size_mb = os.path.getsize(out_path) / (1024 * 1024)
            partition_results[pname] = {
                "status": "ok",
                "file": f"{pname}.json",
                "files": data["file_count"],
                "size_mb": round(size_mb, 2),
            }
            total_files += data["file_count"]

        all_results[unit] = {"status": "ok", "partitions": partition_results}

    # _meta.json global
    total_dur = int((time.time() - start_total) * 1000)
    meta_doc = {
        "generated_at": datetime.now(COLOMBIA_TZ).isoformat(),
        "generator_version": VERSION,
        "source": "hermes-fs-indexer",
        "total_files": total_files,
        "total_duration_ms": total_dur,
        "units": all_results,
    }
    atomic_write_json(os.path.join(output_dir, "_meta.json"), meta_doc)

    if args.verbose:
        print(f"\n✓ {total_files} archivos en {total_dur}ms", file=sys.stderr)
    else:
        print(f"✓ {total_files} archivos en {total_dur}ms")

    # --build-db: migrar JSONs a SQLite después de indexar
    if args.build_db:
        db_path = args.build_db if isinstance(args.build_db, str) else os.path.join(output_dir, "hermes_index.sqlite")
        build_sqlite_db(output_dir, db_path, args.verbose)


if __name__ == "__main__":
    main()

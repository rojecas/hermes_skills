#!/usr/bin/env python3
"""hermes-index-query — Consulta el índice SQLite de archivos INASC.

Permite buscar archivos por código, cliente, año, tipo, texto libre (FTS5),
fecha reciente, y más. Diseñado para ser llamado por Hermes como herramienta
rápida antes de recurrir a find/grep sobre CIFS.

Uso:
    hermes-index-query --prefix STFR002
    hermes-index-query --client Providencia --year 2026
    hermes-index-query --query "tratamiento aguas"
    hermes-index-query --recent 7 --unit Y
    hermes-index-query --type Procedimiento --unit V --count

Flags de filtro (AND lógico entre ellos):
    --prefix <código>   Código de documento (STFR002, CSFR047, etc.)
    --client <nombre>   Cliente (búsqueda LIKE %nombre%)
    --year <año>        Año del documento
    --type <tipo>        Tipo de documento (Formato, Procedimiento, etc.)
    --unit <letra>       Unidad (Y, X, W, V); se traduce a partition_id LIKE
    --query <texto>      Búsqueda FTS5 (full-text) en filename, path, cliente, equipo, tags
    --recent <dias>      Archivos modificados en los últimos N días
    --status <estado>    Filtrar por estado (vigente, posible_vencido, etc.)

Flags de salida:
    --count              Solo devuelve el conteo, no los archivos
    --limit <N>          Máximo de resultados (default: 50, max: 500)
    --format json|text   Formato de salida (default: json)

Comportamiento:
    - Si no hay resultados, exit code 1 + stderr: "SIN_RESULTADOS"
    - Si DB no existe, exit code 2 + stderr: "DB_NO_ENCONTRADA"
    - Si hay resultados, exit code 0 + JSON a stdout
"""

import argparse
import json
import os
import sqlite3
import sys
from datetime import datetime, timezone, timedelta

DB_PATH = "/home/rojecas/noosfera-chat/storage/app/hermes_index/hermes_index.sqlite"
COL_TZ = timezone(timedelta(hours=-5))

UNIT_TO_PARTITION = {
    "Y": "Y_%",
    "X": "X_%",
    "W": "W_%",
    "V": "V_%",
    "U": "U_%",
}


def query_index(db_path: str, args) -> dict:
    """Ejecuta la consulta SQL y devuelve resultados + meta."""
    if not os.path.exists(db_path):
        print("DB_NO_ENCONTRADA", file=sys.stderr)
        sys.exit(2)

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    # Construir cláusulas WHERE
    where_parts = []
    params = []

    # Mapear prefijos comunes a sus particiones para optimizar
    prefix_to_unit = {
        "ST": "Y_%",  # Servicio Técnico → Y
        "CS": "X_%",  # Metrología → X
        "GC": "V_%",  # Calidad → V
        "DC": "W_%",  # Comercial → W
        "AD": "V_%",  # Alta Dirección → V
        "RH": "W_%",  # Recursos Humanos → W
        "CF": "W_%",  # Contable/Financiera → W
        "SS": "V_%",  # SST → V
        "AC": "W_%",  # Almacén/Compras → W
        "CT": "Y_%",  # Soporte Técnico → Y
    }

    # En lugar de combinar con OR, hacer una consulta unificada
    # Primero resolvemos partition_id
    partition_filter = None
    if args.unit:
        partition_filter = UNIT_TO_PARTITION.get(args.unit.upper(), f"{args.unit.upper()}_%")
    elif args.prefix and len(args.prefix) >= 2:
        # Optimización: inferir partición por prefijo
        inferred = prefix_to_unit.get(args.prefix[:2])
        if inferred:
            partition_filter = inferred

    if partition_filter:
        where_parts.append("f.partition_id LIKE ?")
        params.append(partition_filter)

    if args.prefix:
        where_parts.append("f.prefix = ?")
        params.append(args.prefix.upper())

    if args.client:
        where_parts.append("f.client LIKE ?")
        params.append(f"%{args.client}%")

    if args.year:
        where_parts.append("f.year = ?")
        params.append(int(args.year))

    if args.doc_type:
        where_parts.append("f.document_type = ?")
        params.append(args.doc_type)

    if args.status:
        where_parts.append("f.status = ?")
        params.append(args.status)

    if args.recent:
        cutoff = (datetime.now(COL_TZ) - timedelta(days=int(args.recent))).isoformat()
        where_parts.append("f.last_modified > ?")
        params.append(cutoff)

    # Construir query
    use_fts = bool(args.query)

    if use_fts:
        # FTS5 con JOIN a files. Agregar * para búsqueda por prefijo
        fts_query = args.query.strip()
        if not fts_query.endswith('*') and not fts_query.startswith('"'):
            if ' ' in fts_query:
                # Multi-palabra: aplicar * a cada término
                terms = [f'"{t}"*' if not t.startswith('"') else t for t in fts_query.split()]
                fts_query = ' '.join(terms)
            else:
                fts_query = f'"{fts_query}"*'
        where_fts = "files_fts MATCH ?"
        fts_params = [fts_query]

        if where_parts:
            where_clause = "WHERE " + " AND ".join(where_parts) + f" AND {where_fts}"
            all_params = params + fts_params
        else:
            where_clause = f"WHERE {where_fts}"
            all_params = fts_params

        if args.count:
            sql = f"""
                SELECT COUNT(*) as cnt
                FROM files_fts
                JOIN files f ON files_fts.rowid = f.rowid
                {where_clause}
            """
        else:
            limit = min(args.limit, 500)
            sql = f"""
                SELECT f.filename, f.relative_path, f.prefix, f.document_type,
                       f.size_bytes, f.last_modified, f.client, f.year,
                       f.status, f.partition_id
                FROM files_fts
                JOIN files f ON files_fts.rowid = f.rowid
                {where_clause}
                ORDER BY f.last_modified DESC
                LIMIT ?
            """
            all_params.append(limit)
    else:
        if where_parts:
            where_clause = "WHERE " + " AND ".join(where_parts)
        else:
            where_clause = ""

        if args.count:
            sql = f"SELECT COUNT(*) as cnt FROM files f {where_clause}"
        else:
            limit = min(args.limit, 500)
            sql = f"""
                SELECT f.filename, f.relative_path, f.prefix, f.document_type,
                       f.size_bytes, f.last_modified, f.client, f.year,
                       f.status, f.partition_id
                FROM files f
                {where_clause}
                ORDER BY f.last_modified DESC
                LIMIT ?
            """
            params.append(limit)

    cursor = conn.execute(sql, params if not use_fts else all_params)

    if args.count:
        row = cursor.fetchone()
        count = row["cnt"] if row else 0
        conn.close()
        return {"count": count, "query_type": "count"}

    rows = cursor.fetchall()
    conn.close()

    results = []
    for r in rows:
        results.append({
            "filename": r["filename"],
            "relative_path": r["relative_path"],
            "prefix": r["prefix"],
            "document_type": r["document_type"],
            "size_bytes": r["size_bytes"],
            "last_modified": r["last_modified"],
            "client": r["client"],
            "year": r["year"],
            "status": r["status"],
            "partition_id": r["partition_id"],
        })

    return {"results": results, "total_returned": len(results), "query_type": "search"}


def main():
    parser = argparse.ArgumentParser(
        description="hermes-index-query — Consulta el índice SQLite de archivos INASC"
    )
    parser.add_argument("--prefix", help="Código de documento (STFR002, CSFR047...)")
    parser.add_argument("--client", help="Cliente (LIKE %%nombre%%)")
    parser.add_argument("--year", type=int, help="Año del documento")
    parser.add_argument("--type", dest="doc_type", help="Tipo de documento (Formato, Procedimiento...)")
    parser.add_argument("--unit", help="Unidad (Y, X, W, V)")
    parser.add_argument("--query", "-q", help="Búsqueda FTS5 (filename, path, cliente, equipo, tags)")
    parser.add_argument("--recent", type=int, help="Archivos modificados en últimos N días")
    parser.add_argument("--status", help="Estado (vigente, posible_vencido...)")
    parser.add_argument("--count", action="store_true", help="Solo devolver conteo")
    parser.add_argument("--limit", type=int, default=50, help="Máximo de resultados (default: 50)")
    parser.add_argument("--format", choices=["json", "text"], default="json", help="Formato de salida")
    parser.add_argument("--db", default=DB_PATH, help="Ruta a la BD SQLite")

    args = parser.parse_args()

    # Validar que al menos un filtro esté presente
    if not any([args.prefix, args.client, args.year, args.doc_type,
                args.unit, args.query, args.recent, args.status]):
        print("ERROR: Se requiere al menos un filtro (--prefix, --client, --year, --type, --unit, --query, --recent, --status)",
              file=sys.stderr)
        sys.exit(3)

    # Pasar DB path a la función
    result = query_index(args.db, args)

    if result["query_type"] == "count":
        count = result["count"]
        if args.format == "text":
            print(count)
        else:
            print(json.dumps({"count": count}, ensure_ascii=False))
        if count == 0:
            print("SIN_RESULTADOS", file=sys.stderr)
            sys.exit(1)
    else:
        items = result["results"]
        if not items:
            print("SIN_RESULTADOS", file=sys.stderr)
            sys.exit(1)

        if args.format == "text":
            for item in items:
                print(f"{item['filename']}")
                print(f"  Ruta:    {item['relative_path']}")
                print(f"  Código:  {item['prefix'] or 'N/A'}")
                print(f"  Tipo:    {item['document_type'] or 'N/A'}")
                print(f"  Cliente: {item['client'] or 'N/A'}")
                print(f"  Año:     {item['year'] or 'N/A'}")
                print(f"  Estado:  {item['status'] or 'N/A'}")
                print(f"  Unidad:  {item['partition_id']}")
                print(f"  Tamaño:  {item['size_bytes']:,} bytes")
                print(f"  Modif:   {item['last_modified']}")
                print()
        else:
            print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()

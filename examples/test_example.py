#!/usr/bin/env python3
"""Validación de example.ttl contra las 14 consultas VCOM."""
import re
import sys
from pathlib import Path
from rdflib import Graph, Namespace

BASE = Path(__file__).resolve().parent.parent
EXAMPLE = BASE / "examples" / "example.ttl"
REQ_DIR = BASE / "requirements"

g = Graph()
g.parse(str(EXAMPLE), format="turtle")
print(f"Gráfico cargado: {len(g)} triples")

# Mapeo de placeholders → URIs reales (coinciden con el grafo)
PLACEHOLDERS = {
    "URI_DEL_VEHICULO": "https://edint.es/def/vehiculos-compartidos#EcoScooter001",
    "URI_ORGANIZACION": "https://edint.es/def/vehiculos-compartidos#OrgBikeShare",
    "URI_WP1": "https://edint.es/def/vehiculos-compartidos#WP001",
    "URI_WP2": "https://edint.es/def/vehiculos-compartidos#WP002",
    "URI_WP3": "https://edint.es/def/vehiculos-compartidos#WP004",
    "URI_ESTADO_X": "https://edint.es/def/vehiculos-compartidos#VehicleStateActive",
    "URI_PROPULSION_Y": "https://edint.es/def/vehiculos-compartidos#PropulsionElectric",
    "URI_TIPO_Z": "https://edint.es/def/vehiculos-compartidos#TypeEScooter",
    "URI_ESTADO_DISPONIBLE": "https://edint.es/def/vehiculos-compartidos#DockStateFree",
}

REPLACE_MAP = {
    "VCOM02": "URI_DEL_VEHICULO",
    "VCOM06": "URI_ORGANIZACION",
    "VCOM07": "URI_WP1",
    "VCOM09": "URI_ESTADO_X",
    "VCOM10": "URI_ESTADO_DISPONIBLE",
}

results = []
for i in range(1, 16):
    vcom_id = f"VCOM{i:02d}"
    qfile = REQ_DIR / f"{vcom_id}.sparql"

    if not qfile.exists():
        results.append((vcom_id, "ERROR", "archivo no encontrado", None))
        continue

    content = qfile.read_text(encoding="utf-8")

    # Separar en blocks: cada bloque con SELECT es una query
    blocks = []
    current = []
    for line in content.splitlines():
        stripped = line.strip()
        if stripped.startswith("PREFIX") or stripped.startswith("SELECT"):
            if current and any("SELECT" in l for l in current):
                blocks.append("\n".join(current))
                current = []
        current.append(line)
    if current:
        blocks.append("\n".join(current))

    # Tomar el primer bloque con SELECT
    query_text = None
    for b in blocks:
        if "SELECT" in b:
            query_text = b
            break

    if not query_text:
        results.append((vcom_id, "ERROR", "no se encontró SELECT", None))
        continue

    # Reemplazar placeholders por URIs
    query_resolved = query_text
    if vcom_id in REPLACE_MAP:
        ph = REPLACE_MAP[vcom_id]
        uri = PLACEHOLDERS[ph]
        query_resolved = query_resolved.replace(f"<{ph}>", f"<{uri}>")

    if vcom_id == "VCOM09":
        for ph_key in ["URI_ESTADO_X", "URI_PROPULSION_Y", "URI_TIPO_Z"]:
            old = f"<{ph_key}>"
            new = PLACEHOLDERS[ph_key]
            query_resolved = query_resolved.replace(old, f"<{new}>")

    if vcom_id == "VCOM07":
        for ph_key in ["URI_WP1", "URI_WP2", "URI_WP3"]:
            old = f"<{ph_key}>"
            new = PLACEHOLDERS[ph_key]
            query_resolved = query_resolved.replace(old, f"<{new}>")

    # Ejecutar query
    try:
        rows = list(g.query(query_resolved))
        results.append((vcom_id, "OK", f"{len(rows)} filas", len(rows)))
    except Exception as e:
        results.append((vcom_id, "PARSE_ERROR", str(e), None))

# Imprimir resultados
print("\n" + "=" * 70)
print(f"{'VCOM':<8} {'Estado':<14} {'Detalle'}")
print("=" * 70)
passed = 0
for vcom_id, status, detail, nrows in results:
    if status == "OK" and nrows > 0:
        passed += 1
        mark = "✓"
    elif status == "OK" and nrows == 0:
        mark = "⚠"
    else:
        mark = "✗"
    print(f"{mark} {vcom_id:<6} {status:<14} {detail}")

print("-" * 70)
print(f"Resultado: {passed}/14 consultas con filas (≥12 requeridas)")

vcom03_ok = any(r[0] == "VCOM03" and r[1] == "OK" for r in results)
vcom10_ok = any(r[0] == "VCOM10" and r[1] == "OK" for r in results)
print(f"\nVCOM03 parseable y ejecutable: {'✓' if vcom03_ok else '✗'}")
print(f"VCOM10 parseable y ejecutable: {'✓' if vcom10_ok else '✗'}")

sys.exit(0 if passed >= 12 else 1)

#!/usr/bin/env python3
"""GeoPackage -> GeoJSON (WGS84) sin dependencias externas.

Uso:
    python3 scripts/gpkg_a_geojson.py "Distritos de riego..gpkg" \
        --salida web/data/districts.geojson --simplificar 100

Lee el .gpkg con sqlite3 (un GeoPackage es una base SQLite), decodifica la
geometria WKB, simplifica en metros, reproyecta de UTM a lat/lon y escribe un
FeatureCollection. Pensado para maquinas sin GDAL/geopandas.

Si tienes GDAL a la mano, el equivalente es:
    ogr2ogr -f GeoJSON -t_srs EPSG:4326 -simplify 0.001 salida.geojson entrada.gpkg <capa>
"""

import argparse
import json
import math
import os
import sqlite3
import struct
import sys

# ---------- WKB ----------

WKB_POINT, WKB_LINESTRING, WKB_POLYGON = 1, 2, 3
WKB_MULTIPOINT, WKB_MULTILINESTRING, WKB_MULTIPOLYGON, WKB_COLLECTION = 4, 5, 6, 7

ENVELOPE_SIZES = {0: 0, 1: 32, 2: 48, 3: 48, 4: 64}


class Lector:
    """Cursor sobre los bytes del WKB."""

    def __init__(self, data, pos=0):
        self.data, self.pos = data, pos

    def leer(self, fmt):
        valores = struct.unpack_from(fmt, self.data, self.pos)
        self.pos += struct.calcsize(fmt)
        return valores


def _cabecera_gpkg(blob):
    """Devuelve (srs_id, offset del WKB) saltando la cabecera del GeoPackage."""
    if blob[:2] != b"GP":
        return None, 0  # ya es WKB crudo
    flags = blob[3]
    orden = "<" if flags & 1 else ">"
    srs_id = struct.unpack_from(orden + "i", blob, 4)[0]
    env = (flags >> 1) & 0x07
    if env not in ENVELOPE_SIZES:
        raise ValueError("indicador de envelope desconocido: %d" % env)
    return srs_id, 8 + ENVELOPE_SIZES[env]


def _anillo(r):
    (n,) = r.leer(r.orden + "I")
    return [r.leer(r.orden + "dd") for _ in range(n)]


def _geometria(r):
    (orden_byte,) = r.leer("B")
    r.orden = "<" if orden_byte == 1 else ">"
    (tipo,) = r.leer(r.orden + "I")
    base = tipo % 1000  # 1000/2000/3000 = Z/M/ZM; ignoramos la tercera dimension

    if base == WKB_POINT:
        return {"type": "Point", "coordinates": list(r.leer(r.orden + "dd"))}
    if base == WKB_LINESTRING:
        return {"type": "LineString", "coordinates": [list(c) for c in _anillo(r)]}
    if base == WKB_POLYGON:
        (n,) = r.leer(r.orden + "I")
        return {"type": "Polygon", "coordinates": [[list(c) for c in _anillo(r)] for _ in range(n)]}
    if base in (WKB_MULTIPOINT, WKB_MULTILINESTRING, WKB_MULTIPOLYGON, WKB_COLLECTION):
        (n,) = r.leer(r.orden + "I")
        partes = [_geometria(r) for _ in range(n)]
        if base == WKB_COLLECTION:
            return {"type": "GeometryCollection", "geometries": partes}
        nombre = {WKB_MULTIPOINT: "MultiPoint", WKB_MULTILINESTRING: "MultiLineString",
                  WKB_MULTIPOLYGON: "MultiPolygon"}[base]
        return {"type": nombre, "coordinates": [p["coordinates"] for p in partes]}
    raise ValueError("tipo de geometria WKB no soportado: %d" % tipo)


def wkb_a_geojson(blob):
    srs_id, offset = _cabecera_gpkg(blob)
    return srs_id, _geometria(Lector(blob, offset))


# ---------- Proyeccion ----------

A = 6378137.0            # semieje mayor WGS84
F = 1 / 298.257223563    # achatamiento
K0 = 0.9996


def utm_a_lonlat(x, y, zona, sur=False):
    """Inversa de la Transversa de Mercator (WGS84). Precision sub-milimetrica."""
    e2 = F * (2 - F)
    e1 = (1 - math.sqrt(1 - e2)) / (1 + math.sqrt(1 - e2))
    ep2 = e2 / (1 - e2)

    x = x - 500000.0
    if sur:
        y = y - 10000000.0

    m = y / K0
    mu = m / (A * (1 - e2 / 4 - 3 * e2 ** 2 / 64 - 5 * e2 ** 3 / 256))
    phi1 = (mu
            + (3 * e1 / 2 - 27 * e1 ** 3 / 32) * math.sin(2 * mu)
            + (21 * e1 ** 2 / 16 - 55 * e1 ** 4 / 32) * math.sin(4 * mu)
            + (151 * e1 ** 3 / 96) * math.sin(6 * mu)
            + (1097 * e1 ** 4 / 512) * math.sin(8 * mu))

    sin1, cos1, tan1 = math.sin(phi1), math.cos(phi1), math.tan(phi1)
    c1 = ep2 * cos1 ** 2
    t1 = tan1 ** 2
    n1 = A / math.sqrt(1 - e2 * sin1 ** 2)
    r1 = A * (1 - e2) / (1 - e2 * sin1 ** 2) ** 1.5
    d = x / (n1 * K0)

    lat = phi1 - (n1 * tan1 / r1) * (
        d ** 2 / 2
        - (5 + 3 * t1 + 10 * c1 - 4 * c1 ** 2 - 9 * ep2) * d ** 4 / 24
        + (61 + 90 * t1 + 298 * c1 + 45 * t1 ** 2 - 252 * ep2 - 3 * c1 ** 2) * d ** 6 / 720)
    lon = (d
           - (1 + 2 * t1 + c1) * d ** 3 / 6
           + (5 - 2 * c1 + 28 * t1 - 3 * c1 ** 2 + 8 * ep2 + 24 * t1 ** 2) * d ** 5 / 120) / cos1

    lon0 = math.radians((zona - 1) * 6 - 180 + 3)
    return math.degrees(lon0 + lon), math.degrees(lat)


def crear_reproyector(srs_id):
    """Devuelve (funcion xy->lonlat, etiqueta del CRS de origen)."""
    if srs_id in (4326, 0, -1, None):
        return (lambda x, y: (x, y)), "EPSG:4326"
    if 32601 <= srs_id <= 32660:
        zona = srs_id - 32600
        return (lambda x, y: utm_a_lonlat(x, y, zona, False)), "EPSG:%d" % srs_id
    if 32701 <= srs_id <= 32760:
        zona = srs_id - 32700
        return (lambda x, y: utm_a_lonlat(x, y, zona, True)), "EPSG:%d" % srs_id
    raise SystemExit(
        "CRS EPSG:%s no soportado por este script (solo WGS84 y UTM/WGS84).\n"
        "Convierte con ogr2ogr -t_srs EPSG:4326 o con QGIS." % srs_id)


# ---------- Simplificacion ----------

def _distancia_a_segmento(p, a, b):
    (px, py), (ax, ay), (bx, by) = p, a, b
    dx, dy = bx - ax, by - ay
    if dx == 0 and dy == 0:
        return math.hypot(px - ax, py - ay)
    t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))


def douglas_peucker(puntos, tol):
    if tol <= 0 or len(puntos) < 3:
        return puntos
    dmax, idx = 0.0, 0
    for i in range(1, len(puntos) - 1):
        d = _distancia_a_segmento(puntos[i], puntos[0], puntos[-1])
        if d > dmax:
            dmax, idx = d, i
    if dmax <= tol:
        return [puntos[0], puntos[-1]]
    izq = douglas_peucker(puntos[:idx + 1], tol)
    der = douglas_peucker(puntos[idx:], tol)
    return izq[:-1] + der


def simplificar_anillo(anillo, tol):
    """Simplifica conservando el cierre y un minimo de 4 vertices."""
    cerrado = len(anillo) > 3 and anillo[0] == anillo[-1]
    base = anillo[:-1] if cerrado else anillo
    salida = douglas_peucker(base, tol)
    if cerrado:
        if len(salida) < 3:
            salida = base  # el anillo degeneraria: lo dejamos tal cual
        salida = salida + [salida[0]]
    return salida


def _mapear_anillos(coords, nivel, fn):
    if nivel == 0:
        return fn(coords)
    return [_mapear_anillos(c, nivel - 1, fn) for c in coords]


NIVEL_ANILLO = {"LineString": 0, "MultiLineString": 1, "Polygon": 1, "MultiPolygon": 2}


def transformar(geom, tol, proyectar, decimales):
    """Simplifica en las unidades de origen (metros) y luego reproyecta."""
    tipo = geom["type"]
    if tipo == "GeometryCollection":
        geom["geometries"] = [transformar(g, tol, proyectar, decimales) for g in geom["geometries"]]
        return geom

    def punto(c):
        lon, lat = proyectar(c[0], c[1])
        return [round(lon, decimales), round(lat, decimales)]

    if tipo == "Point":
        geom["coordinates"] = punto(geom["coordinates"])
        return geom
    if tipo == "MultiPoint":
        geom["coordinates"] = [punto(c) for c in geom["coordinates"]]
        return geom

    nivel = NIVEL_ANILLO.get(tipo)
    if nivel is None:
        raise ValueError("tipo de geometria no soportado: %s" % tipo)
    coords = _mapear_anillos(geom["coordinates"], nivel, lambda r: simplificar_anillo(r, tol))
    geom["coordinates"] = _mapear_anillos(coords, nivel, lambda r: [punto(c) for c in r])
    return geom


# ---------- Lectura del GeoPackage ----------

def listar_capas(con):
    filas = con.execute(
        "SELECT table_name, data_type, srs_id FROM gpkg_contents WHERE data_type = 'features'"
    ).fetchall()
    return [(f[0], f[2]) for f in filas]


def columna_geometria(con, capa):
    fila = con.execute(
        "SELECT column_name FROM gpkg_geometry_columns WHERE table_name = ?", (capa,)
    ).fetchone()
    return fila[0] if fila else "geom"


def valor_json(v):
    """bytes y tipos raros -> algo serializable; los demas se conservan."""
    if isinstance(v, bytes):
        return v.decode("utf-8", "replace")
    if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
        return None
    return v


def leer_capa(con, capa, tol, decimales, campos_omitidos):
    col_geom = columna_geometria(con, capa)
    cols = [r[1] for r in con.execute('PRAGMA table_info("%s")' % capa)]
    atributos = [c for c in cols if c != col_geom and c not in campos_omitidos]

    features, srs_visto, vacias = [], None, 0
    consulta = 'SELECT "%s", %s FROM "%s"' % (
        col_geom, ", ".join('"%s"' % c for c in atributos), capa)
    for fila in con.execute(consulta):
        blob = fila[0]
        if blob is None:
            vacias += 1
            continue
        srs_id, geom = wkb_a_geojson(blob)
        if srs_visto is None:
            srs_visto = srs_id
        proyectar, _ = crear_reproyector(srs_visto)
        props = {c: valor_json(v) for c, v in zip(atributos, fila[1:])}
        features.append({
            "type": "Feature",
            "properties": props,
            "geometry": transformar(geom, tol, proyectar, decimales),
        })
    return features, srs_visto, vacias


# ---------- CLI ----------

def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("gpkg", help="ruta del archivo .gpkg")
    ap.add_argument("--capa", help="capa a exportar (por defecto, la primera)")
    ap.add_argument("--salida", default="web/data/districts.geojson")
    ap.add_argument("--simplificar", type=float, default=100.0,
                    help="tolerancia en las unidades del CRS de origen (metros en UTM). 0 = sin simplificar")
    ap.add_argument("--decimales", type=int, default=5)
    ap.add_argument("--omitir", default="",
                    help="campos a excluir del GeoJSON, separados por coma")
    ap.add_argument("--solo-listar", action="store_true",
                    help="imprime capas, campos y ejemplos, y termina")
    args = ap.parse_args()

    if not os.path.exists(args.gpkg):
        raise SystemExit("No existe el archivo: %s" % args.gpkg)

    con = sqlite3.connect(args.gpkg)
    capas = listar_capas(con)
    if not capas:
        raise SystemExit("El GeoPackage no tiene capas de tipo 'features'.")

    if args.solo_listar:
        for nombre, srs in capas:
            total = con.execute('SELECT COUNT(*) FROM "%s"' % nombre).fetchone()[0]
            print("Capa: %s  (EPSG:%s, %d features)" % (nombre, srs, total))
            for r in con.execute('PRAGMA table_info("%s")' % nombre):
                ejemplo = con.execute(
                    'SELECT "%s" FROM "%s" WHERE "%s" IS NOT NULL LIMIT 1' % (r[1], nombre, r[1])
                ).fetchone()
                v = valor_json(ejemplo[0]) if ejemplo else None
                if isinstance(v, str) and len(v) > 40:
                    v = v[:40] + "..."
                print("  - %-12s %-12s ej: %s" % (r[1], r[2], "<geometria>" if isinstance(v, bytes) else v))
        return

    capa = args.capa or capas[0][0]
    if capa not in [c[0] for c in capas]:
        raise SystemExit("La capa '%s' no esta en el GeoPackage. Disponibles: %s"
                         % (capa, ", ".join(c[0] for c in capas)))

    omitidos = {c.strip() for c in args.omitir.split(",") if c.strip()}
    features, srs_id, vacias = leer_capa(con, capa, args.simplificar, args.decimales, omitidos)
    if not features:
        raise SystemExit("La capa '%s' no tiene geometrias." % capa)

    _, crs_origen = crear_reproyector(srs_id)
    fc = {
        "type": "FeatureCollection",
        "source": {
            "layer": capa,
            "file": os.path.basename(args.gpkg),
            "crs_origen": crs_origen,
            "simplify_m": args.simplificar,
            "features": len(features),
        },
        "features": features,
    }

    os.makedirs(os.path.dirname(args.salida) or ".", exist_ok=True)
    with open(args.salida, "w", encoding="utf-8") as fh:
        json.dump(fc, fh, ensure_ascii=False, separators=(",", ":"))

    tam = os.path.getsize(args.salida)
    print("Capa '%s' (%s) -> %s" % (capa, crs_origen, args.salida))
    print("  %d features, %.0f KB, tolerancia %g m" % (len(features), tam / 1024, args.simplificar))
    if vacias:
        print("  %d registros sin geometria, omitidos" % vacias)
    if tam > 3 * 1024 * 1024:
        print("  Aviso: pasa de 3 MB. Sube --simplificar (p. ej. 250) para bajar el peso.",
              file=sys.stderr)


if __name__ == "__main__":
    main()

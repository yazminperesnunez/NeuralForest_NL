#!/usr/bin/env python3
"""Prueba cuánto dependen las zonas de prioridad alta de los pesos del índice.

    python3 scripts/robustez_pesos.py                    # 5,000 sorteos, semilla 1
    python3 scripts/robustez_pesos.py --n 20000          # más sorteos
    python3 scripts/robustez_pesos.py --salida otra.json

Lee web/data/zones.geojson (las propiedades que exporta gee/infiltration_priority.js)
y escribe web/data/robustez.json.

Qué hace: recalcula los cinco factores de cada zona con las mismas fórmulas que el
script de GEE, sortea juegos de pesos al azar (distribución uniforme sobre los
pesos que suman 1) y cuenta en qué porcentaje de los sorteos cada zona queda en
prioridad alta (el tercio superior del ranking, como las clases del mapa).

    robustez alta  → la zona es prioritaria con casi cualquier ponderación
    robustez baja  → su lugar depende de los pesos que elija el especialista

Límites (también en web/metodologia.html):
  - Solo mide la incertidumbre de los pesos. No cubre los umbrales (pendiente
    ideal, tope de incendios), la calidad de los datos ni la resolución de 3 km.
  - Los factores se normalizan con los percentiles 2 y 98 de los valores POR ZONA.
    GEE los normaliza con una muestra de píxeles, así que el score recalculado
    puede diferir un poco del `score` exportado. El script reporta la
    concordancia de rangos (rho de Spearman) para que se vea cuánto.
  - Con las zonas de demostración ("mock": true) el resultado es ilustrativo.
"""

import argparse
import json
import math
import os
import random
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ZONAS = os.path.join(RAIZ, "web", "data", "zones.geojson")
SALIDA = os.path.join(RAIZ, "web", "data", "robustez.json")

# Mismos valores que WEIGHTS y las constantes de gee/infiltration_priority.js.
PESOS_BASE = {"ndvi": 0.30, "ndmi": 0.20, "slope": 0.20, "sand": 0.15, "fire": 0.15}
SLOPE_PEAK_PCT = 20.0
SLOPE_HALF_WIDTH = 40.0
FIRE_CAP = 3.0
FACTORES = list(PESOS_BASE)
# Propiedad de zones.geojson que alimenta cada factor.
ENTRADA = {"ndvi": "ndvi", "ndmi": "ndmi", "slope": "slope_pct", "sand": "sand_pct", "fire": "burned_years"}
UMBRAL_ROBUSTA = 80.0   # % de sorteos en alta para llamarla robusta
UMBRAL_SENSIBLE = 50.0  # entre este y el anterior: sensible; debajo: frágil


def percentil(valores, p):
    """Percentil con interpolación lineal (p en 0..100)."""
    v = sorted(valores)
    if not v:
        raise ValueError("sin valores")
    if len(v) == 1:
        return v[0]
    k = (len(v) - 1) * p / 100.0
    lo, hi = int(math.floor(k)), int(math.ceil(k))
    return v[lo] + (v[hi] - v[lo]) * (k - lo)


def escalar(valores):
    """Normaliza a 0..1 con los percentiles 2 y 98 (como robustScale en GEE)."""
    lo, hi = percentil(valores, 2), percentil(valores, 98)
    if hi - lo < 1e-12:
        return [0.5] * len(valores)
    return [min(1.0, max(0.0, (x - lo) / (hi - lo))) for x in valores]


def factores_disponibles(props):
    """Factores cuya propiedad existe en TODAS las zonas (el export de GEE trae los cinco)."""
    return [k for k in FACTORES if all(p.get(ENTRADA[k]) is not None for p in props)]


def calcular_factores(props, usados):
    """Devuelve una lista de dicts {factor: 0..1}, uno por zona (1 = más prioridad)."""
    esc = {}
    for k in ("ndvi", "ndmi", "sand"):
        if k in usados:
            esc[k] = escalar([p[ENTRADA[k]] for p in props])
    out = []
    for i, p in enumerate(props):
        f = {}
        if "ndvi" in usados:
            f["ndvi"] = 1.0 - esc["ndvi"][i]   # menos cobertura, más prioridad
        if "ndmi" in usados:
            f["ndmi"] = 1.0 - esc["ndmi"][i]   # más seco, más prioridad
        if "slope" in usados:
            f["slope"] = min(1.0, max(0.0, 1.0 - abs(p["slope_pct"] - SLOPE_PEAK_PCT) / SLOPE_HALF_WIDTH))
        if "sand" in usados:
            f["sand"] = esc["sand"][i]         # más arena, más infiltración
        if "fire" in usados:
            f["fire"] = min(p["burned_years"], FIRE_CAP) / FIRE_CAP
        out.append(f)
    return out


def pesos_base(usados):
    """Pesos de GEE renormalizados a los factores disponibles."""
    t = sum(PESOS_BASE[k] for k in usados)
    return {k: PESOS_BASE[k] / t for k in usados}


def puntajes(factores, pesos):
    return [sum(f[k] * w for k, w in pesos.items()) for f in factores]


def rangos(scores):
    """Rango 1 = mejor. Empates comparten el rango menor."""
    orden = sorted(range(len(scores)), key=lambda i: -scores[i])
    r = [0] * len(scores)
    for pos, i in enumerate(orden):
        r[i] = pos + 1
        if pos > 0 and scores[i] == scores[orden[pos - 1]]:
            r[i] = r[orden[pos - 1]]
    return r


def spearman(a, b):
    ra, rb = rangos(a), rangos(b)
    n = len(a)
    if n < 3:
        return None
    ma, mb = sum(ra) / n, sum(rb) / n
    cov = sum((x - ma) * (y - mb) for x, y in zip(ra, rb))
    va = math.sqrt(sum((x - ma) ** 2 for x in ra))
    vb = math.sqrt(sum((y - mb) ** 2 for y in rb))
    return cov / (va * vb) if va and vb else None


def pesos_al_azar(rng, usados):
    """Dirichlet(1,…,1): uniforme sobre los pesos que suman 1."""
    e = [rng.expovariate(1.0) for _ in usados]
    s = sum(e)
    return {k: x / s for k, x in zip(usados, e)}


def simular(factores, usados, n_sorteos, semilla):
    """Para cada zona: % de sorteos en alta y distribución de su rango."""
    n = len(factores)
    k_alta = max(1, round(n / 3))  # el tercio superior, como las clases del mapa
    rng = random.Random(semilla)
    en_alta = [0] * n
    rangos_zona = [[] for _ in range(n)]
    for _ in range(n_sorteos):
        sc = puntajes(factores, pesos_al_azar(rng, usados))
        orden = sorted(range(n), key=lambda i: -sc[i])
        for pos, i in enumerate(orden):
            rangos_zona[i].append(pos + 1)
            if pos < k_alta:
                en_alta[i] += 1
    return k_alta, en_alta, rangos_zona


def lectura(alta_en_base, pct):
    if alta_en_base:
        if pct >= UMBRAL_ROBUSTA:
            return "robusta"
        if pct >= UMBRAL_SENSIBLE:
            return "sensible a los pesos"
        return "frágil"
    return "no alta en base, pero sube con otros pesos" if pct >= UMBRAL_SENSIBLE else "no alta"


def analizar(fc, n_sorteos=5000, semilla=1):
    feats = fc["features"]
    props = [f["properties"] for f in feats]
    if len(props) < 6:
        raise ValueError("se necesitan al menos 6 zonas para que la prueba tenga sentido")
    usados = factores_disponibles(props)
    if len(usados) < 2:
        raise ValueError("zones.geojson no trae propiedades suficientes (%s)" % ", ".join(ENTRADA.values()))

    factores = calcular_factores(props, usados)
    pb = pesos_base(usados)
    base = puntajes(factores, pb)
    rango_base = rangos(base)
    k_alta, en_alta, rz = simular(factores, usados, n_sorteos, semilla)
    exportado = [p.get("score") for p in props]
    rho = spearman(base, exportado) if all(x is not None for x in exportado) else None

    zonas = {}
    for i, p in enumerate(props):
        pct = 100.0 * en_alta[i] / n_sorteos
        alta_base = rango_base[i] <= k_alta
        r = sorted(rz[i])
        zonas[str(p.get("id", i))] = {
            "robustez_pct": round(pct, 1),
            "alta_en_base": alta_base,
            "prioridad_exportada": p.get("priority"),
            "rango_base": rango_base[i],
            "rango_p05": r[int(0.05 * (len(r) - 1))],
            "rango_p50": r[len(r) // 2],
            "rango_p95": r[int(math.ceil(0.95 * (len(r) - 1)))],
            "lectura": lectura(alta_base, pct),
        }
    meta = {
        "fuente": "scripts/robustez_pesos.py",
        "sorteos": n_sorteos,
        "semilla": semilla,
        "zonas": len(props),
        "criterio_alta": "tercio superior del ranking (%d de %d zonas) en cada sorteo" % (k_alta, len(props)),
        "factores_usados": usados,
        "factores_faltantes": [k for k in FACTORES if k not in usados],
        "pesos_base": {k: round(v, 4) for k, v in pb.items()},
        "sorteo_de_pesos": "uniforme sobre pesos que suman 1 (Dirichlet con todos los parámetros en 1)",
        "concordancia_rho_con_score": None if rho is None else round(rho, 3),
        "normalizacion": "percentiles 2 y 98 de los valores por zona (aproxima la muestra de píxeles de GEE)",
        "mock": bool(fc.get("mock")),
        "alcance": "solo incertidumbre de pesos; no cubre umbrales, datos ni resolución",
    }
    return {"meta": meta, "zonas": zonas}


def imprimir(res):
    m, z = res["meta"], res["zonas"]
    print("Robustez de los pesos · %d zonas · %d sorteos · semilla %s" % (m["zonas"], m["sorteos"], m["semilla"]))
    print("Criterio:", m["criterio_alta"])
    if m["concordancia_rho_con_score"] is not None:
        print("Concordancia de rangos con el score exportado (rho): %s" % m["concordancia_rho_con_score"])
        if m["concordancia_rho_con_score"] < 0.9:
            print("  AVISO: rho < 0.9. El score recalculado difiere del exportado; revisa que zones.geojson "
                  "sea el export de GEE y no datos de demostración.")
    if m["factores_faltantes"]:
        print("AVISO: faltan los factores %s en zones.geojson; se usan %s con pesos renormalizados."
              % (", ".join(m["factores_faltantes"]), ", ".join(m["factores_usados"])))
    if m["mock"]:
        print("AVISO: zones.geojson es de demostración (mock). Resultado ilustrativo.")
    print()
    print("%-6s %9s %6s %12s  %s" % ("zona", "robustez", "base", "rango p5-p95", "lectura"))
    for zid, d in sorted(z.items(), key=lambda kv: -kv[1]["robustez_pct"]):
        print("%-6s %8.1f%% %6d %9d-%-3d  %s" % (zid, d["robustez_pct"], d["rango_base"],
                                                 d["rango_p05"], d["rango_p95"], d["lectura"]))


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--zonas", default=ZONAS, help="GeoJSON de zonas (default: web/data/zones.geojson)")
    ap.add_argument("--salida", default=SALIDA, help="JSON de salida (default: web/data/robustez.json)")
    ap.add_argument("--n", type=int, default=5000, help="número de sorteos de pesos (default 5000)")
    ap.add_argument("--semilla", type=int, default=1, help="semilla; con la misma semilla el resultado se repite")
    args = ap.parse_args()
    if args.n < 100:
        sys.exit("--n debe ser al menos 100")
    with open(args.zonas, encoding="utf-8") as fh:
        fc = json.load(fh)
    try:
        res = analizar(fc, args.n, args.semilla)
    except ValueError as e:
        sys.exit("Error: %s" % e)
    with open(args.salida, "w", encoding="utf-8") as fh:
        json.dump(res, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
    imprimir(res)
    print("\nEscrito en", os.path.relpath(args.salida, RAIZ))


if __name__ == "__main__":
    main()

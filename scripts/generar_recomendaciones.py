#!/usr/bin/env python3
"""Pre-genera web/data/recommendations.json a partir de web/data/zones.geojson.

    python3 scripts/generar_recomendaciones.py                # usa el LLM
    python3 scripts/generar_recomendaciones.py --solo-reglas  # sin LLM
    python3 scripts/generar_recomendaciones.py --forzar       # rehace las existentes

Con esto el demo funciona aunque el servidor o la API se caigan: la pagina lee
las recomendaciones guardadas y las marca como tales. Las zonas que fallen dos
veces caen a la recomendacion por reglas y se reportan al final.
"""

import argparse
import json
import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, "server"))

import recomendador  # noqa: E402  (necesita el sys.path de arriba)
from app import cargar_env  # noqa: E402

ZONAS = os.path.join(RAIZ, "web", "data", "zones.geojson")
SALIDA = os.path.join(RAIZ, "web", "data", "recommendations.json")
TAMANO_LOTE = 5  # lotes chicos = respuestas cortas y mas confiables


def leer_zonas(ruta):
    with open(ruta, encoding="utf-8") as fh:
        fc = json.load(fh)
    zonas = []
    for i, f in enumerate(fc.get("features", [])):
        props = dict(f.get("properties") or {})
        props.setdefault("id", "Z%02d" % (i + 1))
        zonas.append(props)
    return zonas


def en_lotes(items, n):
    for i in range(0, len(items), n):
        yield items[i:i + n]


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--zonas", default=ZONAS)
    ap.add_argument("--salida", default=SALIDA)
    ap.add_argument("--solo-reglas", action="store_true", help="no llama al LLM")
    ap.add_argument("--forzar", action="store_true", help="regenera las que ya existen")
    ap.add_argument("--lote", type=int, default=TAMANO_LOTE)
    args = ap.parse_args()

    cargar_env(os.path.join(RAIZ, "server", ".env"))
    cargar_env(os.path.join(RAIZ, ".env"))
    import importlib
    importlib.reload(recomendador)  # relee las variables de entorno

    if not os.path.exists(args.zonas):
        raise SystemExit("No existe %s. Exporta las zonas desde GEE primero." % args.zonas)
    zonas = leer_zonas(args.zonas)
    if not zonas:
        raise SystemExit("%s no trae features." % args.zonas)

    existentes = {}
    if os.path.exists(args.salida) and not args.forzar:
        with open(args.salida, encoding="utf-8") as fh:
            existentes = json.load(fh)

    pendientes = [z for z in zonas if z["id"] not in existentes]
    print("%d zonas en total, %d ya tenían recomendación, %d por generar."
          % (len(zonas), len(zonas) - len(pendientes), len(pendientes)))

    usar_llm = not args.solo_reglas and recomendador.llm_configurado()
    if not args.solo_reglas and not usar_llm:
        print("Aviso: falta LLM_API_KEY o LLM_MODEL. Se generan por reglas "
              "(ver server/.env.example).")

    fichas = dict(existentes)
    por_reglas = []
    for lote in en_lotes(pendientes, max(1, args.lote)):
        ids = [z["id"] for z in lote]
        if usar_llm:
            try:
                nuevas, _ = recomendador.recomendar_lote(lote)
                fichas.update(nuevas)
                print("  %s: Grok" % ", ".join(ids))
                continue
            except recomendador.ErrorLLM as e:
                print("  %s: falló el LLM (%s). Se usan las reglas." % (", ".join(ids), e))
        for z in lote:
            fichas[z["id"]] = recomendador.ficha_por_reglas(z)
            por_reglas.append(z["id"])
        if not usar_llm:
            print("  %s: reglas" % ", ".join(ids))

    ordenadas = {zid: fichas[zid] for zid in [z["id"] for z in zonas] if zid in fichas}
    ordenadas.update({k: v for k, v in fichas.items() if k not in ordenadas})

    os.makedirs(os.path.dirname(args.salida) or ".", exist_ok=True)
    with open(args.salida, "w", encoding="utf-8") as fh:
        json.dump(ordenadas, fh, ensure_ascii=False, indent=2)
        fh.write("\n")

    print("Escrito %s con %d recomendaciones." % (args.salida, len(ordenadas)))
    if por_reglas:
        print("Generadas por reglas (revisar antes del pitch): %s" % ", ".join(por_reglas))


if __name__ == "__main__":
    main()

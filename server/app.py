#!/usr/bin/env python3
"""Servidor del demo: archivos estaticos de web/ + POST /api/recommend.

    python3 server/app.py            # http://localhost:8000
    python3 server/app.py --port 9000

Sirve `web/` y la API desde el mismo origen, que es justo lo que espera
`web/app.js` (API_BASE = ''). Solo biblioteca estandar: no hay que instalar
nada. Si no hay LLM configurado, la API responde con la recomendacion por
reglas en vez de fallar, para que el demo nunca se quede en blanco.
"""

import argparse
import json
import os
import sys
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

RAIZ = os.path.dirname(os.path.abspath(__file__))
WEB = os.path.join(os.path.dirname(RAIZ), "web")
sys.path.insert(0, RAIZ)

MAX_CUERPO = 64 * 1024  # el body es una zona: 64 KB sobran


def cargar_env(ruta):
    """Lee un .env sencillo (CLAVE=valor) sin dependencias."""
    if not os.path.exists(ruta):
        return
    with open(ruta, encoding="utf-8") as fh:
        for linea in fh:
            linea = linea.strip()
            if not linea or linea.startswith("#") or "=" not in linea:
                continue
            clave, valor = linea.split("=", 1)
            os.environ.setdefault(clave.strip(), valor.strip().strip('"').strip("'"))


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=WEB, **kwargs)

    def log_message(self, formato, *args):
        sys.stderr.write("%s - %s\n" % (self.address_string(), formato % args))

    # -- utilidades ------------------------------------------------------
    def responder_json(self, codigo, carga):
        cuerpo = json.dumps(carga, ensure_ascii=False).encode("utf-8")
        self.send_response(codigo)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(cuerpo)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(cuerpo)

    def error_json(self, codigo, mensaje):
        self.responder_json(codigo, {"error": mensaje})

    # -- rutas -----------------------------------------------------------
    def do_POST(self):
        if self.path.rstrip("/") != "/api/recommend":
            self.error_json(404, "Ruta no encontrada: %s" % self.path)
            return

        try:
            largo = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            self.error_json(400, "Content-Length inválido.")
            return
        if largo <= 0:
            self.error_json(400, "El cuerpo viene vacío. Manda las properties de la zona en JSON.")
            return
        if largo > MAX_CUERPO:
            self.error_json(413, "El cuerpo es demasiado grande (máximo %d bytes)." % MAX_CUERPO)
            return

        try:
            zona = json.loads(self.rfile.read(largo).decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as e:
            self.error_json(400, "El cuerpo no es JSON válido: %s" % e)
            return
        if not isinstance(zona, dict) or not zona.get("id"):
            self.error_json(400, "Falta el campo 'id' de la zona.")
            return

        import recomendador  # tarde a proposito: toma el entorno ya cargado
        try:
            ficha = recomendador.recomendar_zona(zona)
        except Exception as e:  # el demo no se cae por un error del proveedor
            self.log_message("error al recomendar %s: %s", zona.get("id"), e)
            self.error_json(502, "No se pudo generar la recomendación: %s" % e)
            return
        self.responder_json(200, ficha)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--port", type=int, default=8000)
    ap.add_argument("--host", default="127.0.0.1")
    args = ap.parse_args()

    cargar_env(os.path.join(RAIZ, ".env"))
    cargar_env(os.path.join(os.path.dirname(RAIZ), ".env"))

    import recomendador
    if recomendador.llm_configurado():
        estado = "Grok activo (%s)" % recomendador.LLM_MODEL
    else:
        estado = "sin LLM: /api/recommend responde con las reglas (copia server/.env.example a server/.env)"

    print("Sirviendo %s en http://%s:%d" % (WEB, args.host, args.port))
    print("API: POST /api/recommend — %s" % estado)
    servidor = ThreadingHTTPServer((args.host, args.port), Handler)
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        print("\nServidor detenido.")
    finally:
        servidor.server_close()


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Motor de recomendacion de obra: reglas + LLM (Grok).

Lo usan tanto `server/app.py` (en vivo, POST /api/recommend) como
`scripts/generar_recomendaciones.py` (pre-generadas, sin servidor).
Solo biblioteca estandar.

Contrato de salida (el mismo que lee web/app.js y que guarda
web/data/recommendations.json). `source` es opcional y solo sirve para
etiquetar el origen en la interfaz:

    { "zone_id": "Z01", "work": "...", "why": "...",
      "alternatives": ["..."], "caveats": "...", "source": "grok" | "reglas" }
"""

import json
import os
import urllib.error
import urllib.request

# ---------------------------------------------------------------------------
# Configuracion por variables de entorno. La llave nunca llega al navegador.
# ---------------------------------------------------------------------------
LLM_BASE_URL = os.environ.get("LLM_BASE_URL", "https://api.x.ai/v1")
LLM_API_KEY = os.environ.get("LLM_API_KEY", "")
LLM_MODEL = os.environ.get("LLM_MODEL", "")
LLM_TIMEOUT_S = float(os.environ.get("LLM_TIMEOUT_S", "60"))

# ---------------------------------------------------------------------------
# Reglas de tipo de obra. Umbrales calibrados a la distribucion del export
# real de GEE (14 oct 2026); son PROVISIONALES hasta que Pronatura los valide.
# slope_pct viene en porcentaje (no en grados): 12 grados = 21 %, 15 = 27 %.
# ---------------------------------------------------------------------------
REGLAS = {
    "pendiente_media_pct": 20,       # desde aqui, obra transversal ligera
    "pendiente_fuerte_pct": 25,      # desde aqui, obra firme de piedra
    "pendiente_muy_fuerte_pct": 45,  # desde aqui, obra pesada no es segura
    "ndvi_desnudo": 0.35,            # debajo: cobertura muy baja
    "ndvi_conservado": 0.50,         # desde aqui: conviene conservar
    "arena_alta_pct": 40,            # suelo relativamente arenoso
    "incendios_con_material": 1,     # anios con incendio en la serie de MODIS
}

OBRAS = [
    "barreras de piedra acomodada",
    "barreras de material vegetal muerto",
    "zanjas trinchera",
    "reforestación con especies nativas",
    "conservar y monitorear",
]

AVISO_CIENTIFICO = (
    "Índice de potencial relativo. No mide volumen de agua infiltrada. "
    "Requiere validación en campo."
)


def _num(zona, campo, por_defecto=None):
    v = zona.get(campo)
    return v if isinstance(v, (int, float)) and not isinstance(v, bool) else por_defecto


def obra_por_reglas(zona):
    """Devuelve (obra, motivo, seguro) sin llamar al LLM.

    `seguro` es False cuando ninguna regla aplica y la obra es solo un
    valor por defecto razonable.
    """
    pendiente = _num(zona, "slope_pct", 0) or 0
    ndvi = _num(zona, "ndvi", 0) or 0
    arena = _num(zona, "sand_pct", 0) or 0
    incendios = _num(zona, "burned_years", 0) or 0

    if ndvi >= REGLAS["ndvi_conservado"]:
        return ("conservar y monitorear",
                "la cobertura vegetal ya es alta (NDVI %.2f): conviene protegerla antes que intervenir" % ndvi,
                True)
    if incendios >= REGLAS["incendios_con_material"] and pendiente >= REGLAS["pendiente_media_pct"]:
        return ("barreras de material vegetal muerto",
                "hay material quemado disponible (%g años con incendio) y la pendiente de %.1f %% exige una obra ligera que no remueva suelo"
                % (incendios, pendiente),
                True)
    if pendiente >= REGLAS["pendiente_muy_fuerte_pct"]:
        return ("reforestación con especies nativas",
                "pendiente muy fuerte (%.1f %%): las obras pesadas no son seguras y la vegetación hace el trabajo"
                % pendiente,
                True)
    if pendiente >= REGLAS["pendiente_fuerte_pct"]:
        return ("barreras de piedra acomodada",
                "pendiente fuerte (%.1f %%): se necesita una obra firme que resista el escurrimiento"
                % pendiente,
                True)
    if pendiente >= REGLAS["pendiente_media_pct"]:
        return ("barreras de material vegetal muerto",
                "pendiente media (%.1f %%): una obra transversal ligera frena el escurrimiento sin remover suelo"
                % pendiente,
                True)
    if arena >= REGLAS["arena_alta_pct"]:
        return ("zanjas trinchera",
                "pendiente suave (%.1f %%) y suelo relativamente arenoso (%.0f %% de arena): la zanja capta el escurrimiento y lo infiltra"
                % (pendiente, arena),
                True)
    if ndvi < REGLAS["ndvi_desnudo"]:
        return ("reforestación con especies nativas",
                "pendiente suave (%.1f %%) y poca cobertura (NDVI %.2f): la raíz y la hojarasca hacen el trabajo"
                % (pendiente, ndvi),
                True)
    if not any(_num(zona, c) is not None for c in ("slope_pct", "ndvi")):
        return ("barreras de material vegetal muerto",
                "faltan datos de pendiente y NDVI; es una obra ligera y reversible mientras se valida en campo",
                False)
    return ("zanjas trinchera",
            "pendiente suave (%.1f %%) y cobertura parcial (NDVI %.2f): la zanja capta el escurrimiento"
            % (pendiente, ndvi),
            True)


def ficha_por_reglas(zona):
    """Recomendacion completa sin LLM (modo --solo-reglas y respaldo)."""
    obra, motivo, seguro = obra_por_reglas(zona)
    zid = zona.get("id", "?")
    atributos = ", ".join(filter(None, [
        "pendiente %.1f %%" % _num(zona, "slope_pct") if _num(zona, "slope_pct") is not None else "",
        "NDVI %.2f" % _num(zona, "ndvi") if _num(zona, "ndvi") is not None else "",
        "arena %.0f %%" % _num(zona, "sand_pct") if _num(zona, "sand_pct") is not None else "",
        "%g años con incendio" % _num(zona, "burned_years") if _num(zona, "burned_years") is not None else "",
        "%g m s.n.m." % _num(zona, "elev_m") if _num(zona, "elev_m") is not None else "",
    ]))
    alternativas = [o for o in OBRAS if o != obra][:2]
    confianza = "Recomendación generada por reglas" if seguro else \
                "Recomendación por defecto: ninguna regla aplicó con claridad (confianza baja)"
    return {
        "zone_id": zid,
        "source": "reglas",
        "work": obra,
        "why": "%s (%s). Se sugiere %s porque %s." % (
            "Zona " + str(zid), atributos or "sin atributos", obra, motivo),
        "alternatives": alternativas,
        "caveats": "%s, no por un especialista. %s Verificar en campo: disponibilidad de material, "
                   "presencia de cárcavas, acceso, tenencia de la tierra y presencia de ganado."
                   % (confianza, AVISO_CIENTIFICO),
    }


# ---------------------------------------------------------------------------
# LLM
# ---------------------------------------------------------------------------
PROMPT_SISTEMA = """Eres especialista en restauración de cuencas y conservación de suelos de la \
Sierra Madre Oriental (Nuevo León, México). Recibirás zonas priorizadas para restaurar suelos y \
favorecer la infiltración en las partes altas que abastecen a la Zona Metropolitana de Monterrey.

Reglas:
1. Usa SOLO los atributos de cada zona. No inventes datos, especies, nombres de lugares ni cifras.
2. Elige la obra de esta lista: {obras}.
3. Aplica las reglas de decisión que se te dan. Si ninguna aplica con claridad, decide, justifica y \
dilo en "caveats".
4. "why" explica en 2 o 3 frases qué atributos hacen prioritaria la zona, citando sus valores.
5. "caveats" incluye condiciones de campo por verificar (material disponible, cárcavas, acceso, \
tenencia de la tierra, ganado) y el límite del índice.
6. Recuerda: el índice es de potencial relativo y no mide volumen infiltrado.

Reglas de decisión (umbrales provisionales; slope_pct está en porcentaje):
- ndvi >= {ndvi_conservado}: conservar y monitorear.
- burned_years >= {incendios_con_material} y slope_pct >= {pendiente_media_pct}: barreras de material vegetal muerto.
- slope_pct >= {pendiente_muy_fuerte_pct}: reforestación con especies nativas (obras pesadas no son seguras).
- slope_pct >= {pendiente_fuerte_pct}: barreras de piedra acomodada.
- slope_pct >= {pendiente_media_pct}: barreras de material vegetal muerto.
- sand_pct >= {arena_alta_pct}: zanjas trinchera.
- ndvi < {ndvi_desnudo}: reforestación con especies nativas.
- en otro caso: zanjas trinchera.
Aplica las reglas en este orden y usa la primera que cumpla.

Responde SOLO con un objeto JSON {{"Z01": {{...}}, ...}} donde cada valor tiene los campos: \
zone_id, work, why, alternatives (lista de 1 a 2 obras), caveats. Sin texto adicional ni backticks."""


def prompt_sistema():
    return PROMPT_SISTEMA.format(obras=", ".join(OBRAS), **REGLAS)


class ErrorLLM(RuntimeError):
    pass


def llm_configurado():
    return bool(LLM_API_KEY and LLM_MODEL)


def _llamar_llm(mensajes, temperatura=0.2):
    if not llm_configurado():
        raise ErrorLLM("Faltan LLM_API_KEY o LLM_MODEL en el entorno (ver server/.env.example).")
    cuerpo = json.dumps({
        "model": LLM_MODEL,
        "messages": mensajes,
        "temperature": temperatura,
    }).encode("utf-8")
    req = urllib.request.Request(
        LLM_BASE_URL.rstrip("/") + "/chat/completions",
        data=cuerpo,
        headers={"Content-Type": "application/json",
                 "Authorization": "Bearer " + LLM_API_KEY},
    )
    try:
        with urllib.request.urlopen(req, timeout=LLM_TIMEOUT_S) as r:
            data = json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        detalle = e.read().decode("utf-8", "replace")[:300]
        raise ErrorLLM("El LLM respondió %s: %s" % (e.code, detalle))
    except urllib.error.URLError as e:
        raise ErrorLLM("No se pudo contactar al LLM: %s" % e.reason)
    try:
        return data["choices"][0]["message"]["content"]
    except (KeyError, IndexError):
        raise ErrorLLM("Respuesta del LLM sin 'choices[0].message.content'.")


def _json_del_texto(texto):
    """Rescata el objeto JSON aunque venga con backticks o texto alrededor."""
    t = texto.strip()
    if t.startswith("```"):
        t = t.split("```")[1]
        t = t[4:] if t.lower().startswith("json") else t
    ini, fin = t.find("{"), t.rfind("}")
    if ini == -1 or fin <= ini:
        raise ErrorLLM("La respuesta del LLM no trae un objeto JSON.")
    return json.loads(t[ini:fin + 1])


CAMPOS = ("zone_id", "work", "why", "alternatives", "caveats")


def validar_ficha(ficha, zone_id):
    """Normaliza y valida una recomendacion. Lanza ErrorLLM si no cumple."""
    if not isinstance(ficha, dict):
        raise ErrorLLM("La recomendación de %s no es un objeto." % zone_id)
    faltantes = [c for c in CAMPOS if c not in ficha]
    if faltantes:
        raise ErrorLLM("A %s le faltan campos: %s" % (zone_id, ", ".join(faltantes)))
    alt = ficha["alternatives"]
    if isinstance(alt, str):
        alt = [alt]
    if not isinstance(alt, list) or not all(isinstance(a, str) for a in alt):
        raise ErrorLLM("'alternatives' de %s debe ser una lista de textos." % zone_id)
    obra = str(ficha["work"]).strip()
    if obra not in OBRAS:
        raise ErrorLLM("Obra no permitida en %s: '%s'. Usa una de: %s"
                       % (zone_id, obra, ", ".join(OBRAS)))
    return {
        "zone_id": zone_id,
        "source": "grok",
        "work": obra,
        "why": str(ficha["why"]).strip(),
        "alternatives": [a.strip() for a in alt][:2],
        "caveats": str(ficha["caveats"]).strip(),
    }


def recomendar_lote(zonas, reintentos=1):
    """Pide recomendaciones para varias zonas. Devuelve (fichas, avisos)."""
    ids = [str(z.get("id")) for z in zonas]
    mensajes = [
        {"role": "system", "content": prompt_sistema()},
        {"role": "user", "content": "Zonas:\n" + json.dumps(zonas, ensure_ascii=False)},
    ]
    avisos = []
    for intento in range(reintentos + 1):
        try:
            crudo = _llamar_llm(mensajes)
            bruto = _json_del_texto(crudo)
            fichas = {zid: validar_ficha(bruto.get(zid), zid) for zid in ids}
            return fichas, avisos
        except (ErrorLLM, ValueError) as e:
            avisos.append("Intento %d: %s" % (intento + 1, e))
            if intento == reintentos:
                raise ErrorLLM(" | ".join(avisos))
            # El error se le devuelve al modelo para que corrija.
            mensajes.append({"role": "user", "content":
                             "Tu respuesta anterior falló: %s. Corrige y responde SOLO el JSON." % e})
    raise ErrorLLM(" | ".join(avisos))


def recomendar_zona(zona):
    """Una zona. Si el LLM no esta disponible o falla, cae a las reglas."""
    zid = str(zona.get("id", "?"))
    if not llm_configurado():
        return ficha_por_reglas(zona)
    try:
        return recomendar_lote([zona])[0][zid]
    except ErrorLLM:
        return ficha_por_reglas(zona)

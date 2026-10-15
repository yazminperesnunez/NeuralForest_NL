# API de recomendación

`POST /api/recommend` recibe las `properties` de una zona y devuelve el tipo de obra sugerido.
Solo biblioteca estándar de Python 3.8+: no hay que instalar nada.

## Correr

```bash
cp server/.env.example server/.env   # LLM_API_KEY y LLM_MODEL
python3 server/app.py                # sirve web/ y la API en http://localhost:8000
python3 server/app.py --port 9000
```

El servidor también sirve los archivos de `web/`, así que la página y la API quedan en el mismo
origen y `API_BASE` de `web/app.js` se queda vacío.

## Variables de entorno

| Variable | Para qué |
|---|---|
| `LLM_BASE_URL` | API compatible con OpenAI. Por defecto `https://api.x.ai/v1` (Grok). |
| `LLM_API_KEY` | Llave. Nunca llega al navegador ni al repo (`server/.env` está en `.gitignore`). |
| `LLM_MODEL` | Nombre exacto del modelo del proveedor. Sin esto, se usan las reglas. |
| `LLM_TIMEOUT_S` | Segundos de espera. Por defecto 60. |

## Contrato

Entrada: las `properties` de la zona, tal cual salen de `zones.geojson` (necesita al menos `id`).

Salida:

```json
{ "zone_id": "Z01", "work": "barreras de piedra acomodada", "why": "...",
  "alternatives": ["..."], "caveats": "...", "source": "grok" }
```

Códigos: `400` cuerpo inválido o sin `id`, `404` otra ruta, `413` cuerpo de más de 64 KB,
`502` el proveedor falló de forma irrecuperable.

## Qué pasa si el LLM falla

1. Se reintenta una vez, devolviéndole al modelo el error de validación.
2. Si vuelve a fallar —o si no hay llave configurada— responde la recomendación **por reglas**,
   con `"source": "reglas"`. El panel la etiqueta como tal. El demo nunca se queda en blanco.

Las reglas y sus umbrales están en el diccionario `REGLAS` de `recomendador.py`.
**Son provisionales: hay que validarlos con Pronatura.**

## Sin servidor

`python3 scripts/generar_recomendaciones.py` escribe `web/data/recommendations.json` con todas
las zonas. Con eso la página funciona abierta como archivos estáticos.

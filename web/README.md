# Prioridad de infiltración · web

Página estática (Leaflet 1.9.4 por CDN, sin build ni npm).

## Correr
```
cd web && python3 -m http.server 8000
# abrir http://localhost:8000
```

## P1: zonas reales
Reemplaza `data/zones.geojson` por el export de GEE (FeatureCollection). Acepta Polygon, MultiPolygon y Point. Si falta `id`, se genera `Z01`, `Z02`...

## P3: API
La página hace `POST /api/recommend` al mismo origen (sirve `web/` y la API desde el mismo servidor).
Si la API vive en otro host, cambia `API_BASE` al inicio de `app.js` (y habilita CORS).
`data/recommendations.json` es un caché opcional; esas zonas se muestran como "guardada".

## Contratos
Zona (`properties` de cada Feature; también es el body del POST):
```json
{ "id": "Z01", "priority": "alta", "score": 0.82, "slope_pct": 18.5, "ndvi": 0.21,
  "elev_m": 1850, "burned_years": 2, "sand_pct": 45, "basin": "Río Santa Catarina" }
```
`priority`: `"alta" | "media" | "baja"`. `score`: 0–1.

Recomendación (respuesta del POST; `recommendations.json` = objeto por id de zona):
```json
{ "zone_id": "Z01", "work": "barreras de piedra acomodada",
  "why": "...", "alternatives": ["..."], "caveats": "..." }
```

# Prioridad de infiltración · web

Página estática (Leaflet 1.9.4 por CDN, sin build ni npm).

## Correr
```
cd web && python3 -m http.server 8000
# abrir http://localhost:8000
```

## P1: zonas reales
Reemplaza `data/zones.geojson` por el export de GEE (FeatureCollection). Acepta Polygon, MultiPolygon y Point. Si falta `id`, se genera `Z01`, `Z02`...

Mientras sean las zonas de demostración, el archivo lleva `"mock": true` al nivel del FeatureCollection y la página muestra el aviso "Datos ilustrativos". El export de GEE no trae esa bandera, así que el aviso desaparece solo.

## P3: API
La página hace `POST /api/recommend` al mismo origen. `python3 server/app.py` sirve `web/` y la API juntos.
Si la API vive en otro host, cambia `API_BASE` al inicio de `app.js` (y habilita CORS).
`data/recommendations.json` es un caché opcional; esas zonas se muestran como "guardada".
Se pre-genera con `python3 scripts/generar_recomendaciones.py`.

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
  "why": "...", "alternatives": ["..."], "caveats": "...", "source": "grok" }
```
`source` es opcional (`"grok"` o `"reglas"`) y solo sirve para etiquetar el origen en el panel.
`work` sale de la lista cerrada de `server/recomendador.py`: barreras de piedra acomodada,
barreras de material vegetal muerto, zanjas trinchera, reforestación con especies nativas,
conservar y monitorear.

## Capas de contexto (opcionales)
`data/districts.geojson`: distritos de riego de Pronatura, en WGS84, con los atributos del
GeoPackage intactos. Se genera con `scripts/gpkg_a_geojson.py`. La página la carga solo cuando
se prende la casilla "Distritos de riego"; si el archivo no está, la casilla avisa y el mapa sigue.

`data/dams.json`: presas de abasto y nivel de SADM. `pct` y `hm3` en `null` se muestran como
"PENDIENTE"; `verify_coords: true` marca las coordenadas que faltan verificar. Si el archivo no
está, la página usa la lista `DAMS` de `app.js`.

## Cartera CSV
El botón "Descargar cartera (CSV)" arma el archivo en el navegador con todas las zonas (ordenadas
por índice) y su recomendación. Lleva BOM para que Excel abra bien los acentos.

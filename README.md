# NeuralForest NL

¿Dónde restaurar suelos en las partes altas para favorecer la infiltración?

Mapa de prioridad de restauración para las cuencas altas que alimentan las presas de Monterrey (Cerro Prieto, La Boca y El Cuchillo). Para cada zona prioritaria, Grok propone un tipo de obra (barreras de piedra, barreras de material vegetal muerto, zanjas, reforestación) y explica por qué.

Reto 1 · Infiltración — Grok Monterrey Build Day, 14 oct 2026. Reto propuesto por Pronatura Noreste.

## Cómo funciona

1. **`gee/`**: un script de Google Earth Engine calcula un índice ponderado con 5 capas: vegetación (NDVI), humedad (NDMI), pendiente, arena del suelo e incendios. Divide la zona en celdas de 3 km, las clasifica en alta, media o baja, y exporta `zones.geojson`.
2. **`web/`**: una página estática con un mapa Leaflet. Muestra las zonas, filtra por prioridad, lista las 25 zonas con mayor puntaje y muestra el detalle de cada zona.
3. **`server/`**: el endpoint `POST /api/recommend` manda los datos de una zona a Grok y regresa la obra recomendada. Solo biblioteca estándar de Python, sin dependencias. Si no hay llave de API configurada, responde con una recomendación por reglas en vez de fallar.
4. **`scripts/`**: pre-generan las recomendaciones de todas las zonas (para que el demo no dependa de la red) y convierten el GeoPackage de distritos de riego de Pronatura a GeoJSON sin necesidad de GDAL ni geopandas, y prueban qué tan sensibles son las zonas de prioridad alta a los pesos del índice.

## Estructura

```
gee/infiltration_priority.js        Índice de prioridad en GEE (pegar en el Code Editor)
web/index.html, app.js, styles.css
web/metodologia.html                Metodología, límites y fuentes (sin JS)
web/data/zones.geojson              Zonas (reemplazar con el export de GEE)
web/data/recommendations.json       Recomendaciones guardadas de Grok
web/data/districts.geojson          Distritos de riego de Pronatura (capa de contexto)
web/data/dams.json                  Presas de abasto y niveles de SADM
server/app.py                       Sirve web/ + POST /api/recommend
server/recomendador.py              Reglas de obra, prompt y cliente del LLM
scripts/generar_recomendaciones.py  Pre-genera recommendations.json
scripts/gpkg_a_geojson.py           GeoPackage -> GeoJSON (sin GDAL)
scripts/robustez_pesos.py           Sensibilidad de los pesos: robustez de cada zona
pitch/guion.md, pitch/diapositivas.md
```

## Correr

Con Grok en vivo (sirve la página y la API desde el mismo origen):

```bash
cp server/.env.example server/.env   # poner LLM_API_KEY y LLM_MODEL
python3 server/app.py                # http://localhost:8000
```

Solo la página, sin API:

```bash
cd web
python3 -m http.server 8000
# abrir http://localhost:8000
```

Pre-generar las recomendaciones de todas las zonas (recomendado antes del demo):

```bash
python3 scripts/generar_recomendaciones.py              # con Grok
python3 scripts/generar_recomendaciones.py --solo-reglas  # sin LLM
```

Probar qué tan sensibles son las zonas a los pesos (usar con el export real de GEE; con las zonas de muestra solo es ilustrativo):

```bash
python3 scripts/robustez_pesos.py            # 5,000 sorteos, escribe web/data/robustez.json
python3 scripts/robustez_pesos.py --n 20000  # más sorteos
```

Actualizar la capa de distritos de riego a partir del GeoPackage de Pronatura:

```bash
python3 scripts/gpkg_a_geojson.py "datos/Distritos de riego..gpkg" --solo-listar
python3 scripts/gpkg_a_geojson.py "datos/Distritos de riego..gpkg" \
  --salida web/data/districts.geojson --simplificar 100 \
  --omitir "fid,Shape_area,Shape_len,ID_Geo_N"
```

GEE: ver `gee/README.md`. Formatos de datos: ver `web/README.md`.
Metodología, pesos y límites: `web/metodologia.html`.

## Equipo

| Rol | Tarea |
|---|---|
| P1 | Índice en GEE y export de `zones.geojson` |
| P2 | Página web y mapa |
| P3 | Servidor e integración con Grok |
| P4 | Pesos, reglas de obras y pitch |

## Límites

- El índice compara el potencial relativo entre zonas. No mide el volumen de agua infiltrada.
- Los pesos de las capas son una primera propuesta y un experto debe validarlos.
- Sentinel-2 y MODIS tienen una resolución de 10 a 500 m. Cada celda de 3 km es un promedio.
- Los umbrales de tipo de obra (`REGLAS` en `server/recomendador.py`) son provisionales: faltan validar con Pronatura.
- `web/data/zones.geojson` trae `"mock": true` mientras sean las zonas de demostración; la página muestra un aviso y deja de mostrarlo cuando se reemplaza por el export real de GEE.

## Fuentes de datos

- SRTM 30 m (elevación y pendiente): `USGS/SRTMGL1_003`
- Sentinel-2 SR Harmonized (NDVI, NDMI): `COPERNICUS/S2_SR_HARMONIZED`
- OpenLandMap, fracción de arena: `OpenLandMap/SOL/SOL_SAND-WFRACTION_USDA-3A1A1A_M/v02`
- MODIS, área quemada: `MODIS/061/MCD64A1`
- Niveles de presas: SADM (página HTML, sin API: captura manual)
- Distritos de riego: Pronatura Noreste (GeoPackage entregado al equipo, EPSG:32614)

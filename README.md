# NeuralForest NL

¿Dónde restaurar suelos en las partes altas para favorecer la infiltración?

Mapa de prioridad de restauración para las cuencas altas que alimentan las presas de Monterrey (Cerro Prieto, La Boca y El Cuchillo). Para cada zona prioritaria, Grok propone un tipo de obra (barreras de piedra, barreras de material vegetal muerto, zanjas, reforestación) y explica por qué.

Reto 1 · Infiltración — Grok Monterrey Build Day, 14 oct 2026. Reto propuesto por Pronatura Noreste.

## Cómo funciona

1. **`gee/`**: un script de Google Earth Engine calcula un índice ponderado con 5 capas: vegetación (NDVI), humedad (NDMI), pendiente, arena del suelo e incendios. Divide la zona en celdas de 3 km, las clasifica en alta, media o baja, y exporta `zones.geojson`.
2. **`web/`**: una página estática con un mapa Leaflet. Muestra las zonas, filtra por prioridad, lista las 25 zonas con mayor puntaje y muestra el detalle de cada zona.
3. **`server/`** (pendiente): el endpoint `POST /api/recommend` manda los datos de una zona a Grok y regresa la obra recomendada.

## Estructura

```
gee/infiltration_priority.js   Índice de prioridad en GEE (pegar en el Code Editor)
web/index.html, app.js, styles.css
web/data/zones.geojson          Zonas (reemplazar con el export de GEE)
web/data/recommendations.json   Recomendaciones guardadas de Grok
```

## Correr

```bash
cd web
python3 -m http.server 8000
# abrir http://localhost:8000
```

GEE: ver `gee/README.md`. Formatos de datos: ver `web/README.md`.

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

## Fuentes de datos

- SRTM 30 m (elevación y pendiente): `USGS/SRTMGL1_003`
- Sentinel-2 SR Harmonized (NDVI, NDMI): `COPERNICUS/S2_SR_HARMONIZED`
- OpenLandMap, fracción de arena: `OpenLandMap/SOL/SOL_SAND-WFRACTION_USDA-3A1A1A_M/v02`
- MODIS, área quemada: `MODIS/061/MCD64A1`
- Niveles de presas: SADM

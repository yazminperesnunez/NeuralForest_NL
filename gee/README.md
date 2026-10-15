# Prioridad de infiltración (GEE)
1. Abre https://code.earthengine.google.com y crea un script nuevo.
2. Pega todo `infiltration_priority.js` y pulsa **Run**. Espera 2 a 6 min.
3. Mira la pestaña **Console**: mensajes 1/4 a 4/4, resumen y top 5.
4. Descargar: en Console haz clic en **Descarga zones.geojson →** (guarda como `zones.geojson`).
5. Respaldo: pestaña **Tasks** → **Run** en `zones` (sale en tu Google Drive).
6. Pesos: edita `WEIGHTS` arriba del script (deben sumar 1).
7. Zona propia: dibuja un polígono con el mapa (variable `geometry`); el script lo usa solo, con basin "Zona dibujada".
8. Zona fija: cambia las coordenadas en `buildBasins()`.
9. Si hay timeout: sube `CELL_SIZE_M` a 5000 o pon `DATE_START = '2024-01-01'`.

# Plan de implementación · 5 mejoras de UI/UX

Mejoras sobre el demo que ya está en `develop`. Cada una es **aditiva**: no cambia el
contrato de `zones.geojson`, ni el índice de GEE, ni la arquitectura de `web/app.js`.
Todas se tocan en tres archivos: `web/app.js`, `web/styles.css` y `web/index.html`.

Orden sugerido: **5 → 1 → 2 → 4 → 3**. La 5 es la más barata y deja el andamiaje de
selección que usan la 1 y la 2; la 3 es la más larga y la que menos riesgo corre si
se queda fuera por tiempo.

| # | Mejora | Esfuerzo | Para quién |
|---|---|---|---|
| 1 | Navegar entre zonas sin volver a la lista | ~30 líneas | quien presenta |
| 2 | Obra sugerida visible en la lista + filtro | ~40 líneas | el jurado y Pronatura |
| 3 | Atributos con barra y etiqueta cualitativa | ~50 líneas + CSS | el jurado |
| 4 | Tooltip con sustancia y rank en el mapa | ~35 líneas | proyector |
| 5 | Zona seleccionada en la URL | ~20 líneas | seguro de demo |

---

## Base técnica compartida (hacer primero, 10 min)

Hoy el orden del ranking se calcula en dos lugares: dentro de `renderList()`
(`web/app.js:194`) y dentro de `carteraCsv()`. Las mejoras 1, 2 y 5 necesitan ese
mismo orden, así que conviene extraerlo **una sola vez** antes de empezar:

```js
// Zonas visibles, ordenadas por índice. Única fuente del orden del ranking.
function zonasOrdenadas() {
  return state.zones.map(f => f.properties).filter(isVisible)
    .sort((a, b) => (b.score ?? -1) - (a.score ?? -1));
}
```

`renderList()` pasa a usarla y `carteraCsv()` también (el CSV exporta todas las zonas,
no solo las visibles: ahí se llama sin el `filter`, o con un parámetro `todas = true`).

Es el único cambio que toca código existente. Todo lo demás se agrega.

---

## 1 · Navegar entre zonas sin volver a la lista

**Problema.** `renderDetail()` (`web/app.js:229`) reemplaza la lista entera y la única
salida es el botón `← Volver a la lista`. Comparar dos zonas cuesta tres clics.

**Archivos.** `web/app.js`, `web/styles.css`.

### Pasos

1. Agregar una barra de navegación arriba de la ficha, dentro del `innerHTML` de
   `renderDetail()`:

   ```
   ← Lista          Z03 · 3 de 25          ‹ anterior   siguiente ›
   ```

2. Funciones nuevas:

   ```js
   function indiceDeZona(id) { return zonasOrdenadas().findIndex(p => p.id === id); }

   function zonaVecina(id, paso) {
     const lista = zonasOrdenadas();
     const i = lista.findIndex(p => p.id === id);
     return (i === -1) ? null : (lista[i + paso] || null);  // sin ciclo en los extremos
   }
   ```

3. Los botones `‹` / `›` llaman `selectZone(vecina.id, true)`. En el primero y el
   último se deshabilitan (`disabled`), no se ocultan: que no brinque el layout.

   El contador ("3 de 25") es la posición dentro de la lista **filtrada**; el `#rank` de
   la mejora 4 es la posición global y no cambia al filtrar. Son dos cosas distintas a
   propósito: una dice "dónde voy en lo que estoy viendo", la otra "qué tan prioritaria es".

4. Teclado, registrado **una sola vez** en el arranque (no en cada `renderDetail`,
   si no se acumulan listeners):

   ```js
   document.addEventListener('keydown', e => {
     if (!state.selected || e.target.matches('input, textarea')) return;
     if (e.key === 'ArrowRight' || e.key === 'ArrowLeft') {
       const v = zonaVecina(state.selected, e.key === 'ArrowRight' ? 1 : -1);
       if (v) { e.preventDefault(); selectZone(v.id, true); }
     }
     if (e.key === 'Escape') { state.selected = null; renderList(); }
   });
   ```

5. Cada salto ya hace `flyTo` porque `selectZone(id, true)` lo trae.

**Criterios de aceptación**
- Desde Z03 se llega a Z04 con un clic y con `→`, y el mapa vuela a la zona nueva.
- En la zona 1, `‹ anterior` está deshabilitado; en la última, `siguiente ›`.
- `Esc` regresa a la lista.
- Si se filtra a solo "alta", la navegación recorre **solo** las zonas altas.

---

## 2 · Obra sugerida visible en la lista + filtro por obra

**Problema.** La fila del ranking (`web/app.js:199`) muestra id, cuenca, índice y
prioridad. El tipo de obra —lo que aporta Grok— está a un clic de distancia, así que
nunca se ve el panorama completo.

**Archivos.** `web/app.js`, `web/styles.css`, `web/index.html`.

### Pasos

1. Tabla de presentación por obra, junto a `COLORS`:

   ```js
   const OBRAS_UI = {
     'barreras de piedra acomodada':        { corto: 'piedra',    icono: '🪨' },
     'barreras de material vegetal muerto': { corto: 'vegetal',   icono: '🌿' },
     'zanjas trinchera':                    { corto: 'zanjas',    icono: '⛏' },
     'reforestación con especies nativas':  { corto: 'reforestar',icono: '🌲' },
     'conservar y monitorear':              { corto: 'conservar', icono: '👁' },
   };
   ```

   Si llega una obra fuera de la lista, el chip la muestra tal cual en gris: el
   contrato del LLM ya la restringe, pero la UI no debe romperse por eso.

2. `chipObra(id)` devuelve el chip a partir de `recoFor(id)` (`web/app.js:241`), o un
   chip gris **"sin ficha"** cuando no hay recomendación. Hoy eso solo se descubre
   entrando a la zona.

3. Agregar el chip a la fila, dentro del `<span class="pill-row">` que ya existe al
   lado del `badge(p)`. No hace falta tocar el grid del `li`.

4. Filtro por obra en `index.html`, como un `<select>` en el grupo de controles del
   mapa (un grupo de 5 casillas satura la esquina):

   ```html
   <div class="ctl-group" id="work-filter">
     <label>Obra
       <select id="filter-work">
         <option value="todas">todas</option>
         <!-- las 5 obras, pobladas desde OBRAS_UI al arrancar -->
       </select>
     </label>
   </div>
   ```

5. Extender `isVisible(p)` para que considere también la obra seleccionada:

   ```js
   function isVisible(p) {
     const okClase = state.visible.has(p.priority) || !priorityOf(p);
     if (!okClase) return false;
     if (state.obra === 'todas') return true;
     const r = recoFor(p.id);
     return !!r && r.work === state.obra;
   }
   ```

   Con eso el filtro aplica **al mapa, a la lista, al contador y al CSV** sin tocar
   nada más: `refreshVisibility()` ya es el punto único.

**Criterios de aceptación**
- Cada fila muestra su obra sin abrir la zona.
- Elegir "barreras de piedra" deja en el mapa y en la lista solo esas zonas, y el
  contador ("Mostrando N de M") cuadra.
- Las zonas sin ficha se marcan y no desaparecen al filtrar por prioridad.

---

## 3 · Atributos con barra y etiqueta cualitativa

**Problema.** La ficha lista `NDVI 0.21`, `Pendiente 18.5 %`. Para el jurado, `0.21`
no indica ni siquiera si más es mejor o peor.

**Archivos.** `web/app.js`, `web/styles.css`.

### Pasos

1. Extender `ATTRS` (`web/app.js:10`) con el rango esperado y el sentido, **sin
   quitarle nada**: hoy es `[clave, etiqueta, unidad]` y pasa a tener dos campos
   opcionales más, `[min, max]` y una función de etiqueta cualitativa.

2. Normalizar contra el rango **real de las 25 zonas cargadas**, no contra un máximo
   teórico: así la barra responde *qué tan alto es alto aquí*. Calcularlo una vez al
   cargar (`rangosDeZonas()`), no por render.

3. Umbrales cualitativos tomados de `REGLAS` en `server/recomendador.py` para que la
   ficha y la recomendación nunca se contradigan:

   | Atributo | Corte | Etiqueta |
   |---|---|---|
   | NDVI | < 0.35 / < 0.50 / ≥ 0.50 | cobertura muy baja / parcial / conservada |
   | Pendiente | < 20 % / < 25 % / ≥ 25 % | suave / moderada / fuerte |
   | Arena | ≥ 50 % | suelo arenoso |
   | Incendios | ≥ 2 años | recurrente |

4. Render: la barra es un `<div>` con `width: %` en CSS puro, sin librería. Mantener
   el `<dl class="attrs">` que ya existe y agregar la barra dentro del `<dd>`.

5. Accesibilidad: la barra lleva `role="img"` con `aria-label` que repite el valor y
   la etiqueta, y cada atributo un `title` que lo explica
   (*"NDMI: humedad de la vegetación. Más bajo = más seco."*). La barra es decorativa;
   el número sigue siendo el dato.

**Criterios de aceptación**
- Todo atributo numérico muestra número, barra y etiqueta.
- Un atributo ausente (`null`) muestra `—` y **no** dibuja barra.
- La etiqueta nunca contradice la obra recomendada.
- Se entiende en blanco y negro, por si el proyector miente con el color.

---

## 4 · Tooltip con sustancia y número de rank en el mapa

**Problema.** El tooltip dice `Z01 · alta` (`web/app.js:94`) y los marcadores son
círculos sin etiqueta (`web/app.js:79`). En proyector no se distingue la zona #1 de la #19.

**Archivos.** `web/app.js`, `web/styles.css`.

### Pasos

1. Guardar el rank al cargar: justo después de `normalize()` (`web/app.js:56`), recorrer las
   zonas ordenadas por índice y escribir `p.rank = i + 1`. Es un campo derivado de la UI,
   no del contrato de datos. Ojo: el rank se fija sobre **todas** las zonas, no sobre las
   visibles, para que no cambie de número al filtrar.

2. Cambiar el `L.circleMarker` de `makeMarker()` por un `L.divIcon` ligero con el
   número del rank. Conservar `MARKER_MAX_ZONES` / `MARKER_MIN_ZOOM`
   (`web/app.js:20-21`): con el export real de GEE pueden ser cientos de celdas.

3. Tooltip como mini-ficha:

   ```
   #3 · Río Ramos
   índice 0.74 · prioridad alta
   🪨 barreras de piedra acomodada
   ```

4. Resaltado cruzado lista ↔ mapa: `mouseover` en la fila resalta el polígono y
   viceversa. `bindZoneEvents()` ya tiene el `mouseover`/`mouseout` con `styleFor(p, hover)`;
   solo falta exponerlo como `resaltar(id, on)` y llamarlo desde el panel.

5. Mantener el resaltado de la zona seleccionada aunque se quite el mouse: hoy
   `mouseout` siempre devuelve al estilo base.

**Criterios de aceptación**
- Se ve el número de rank sobre cada zona a zoom de trabajo.
- El tooltip dice cuenca, índice y obra sin abrir la ficha.
- Pasar el mouse por la lista resalta el polígono correspondiente.
- Con 300 celdas el mapa no se vuelve ilegible (los marcadores siguen la regla de zoom).

---

## 5 · Zona seleccionada en la URL

**Problema.** Recargar a media demo pierde todo, no se puede compartir un link a *esta*
zona y el botón "atrás" del navegador sale del sitio.

**Archivos.** `web/app.js`.

### Pasos

1. En `selectZone()` (`web/app.js:215`), escribir el hash **sin** agregar entradas de
   más al historial cuando la selección viene del propio hash:

   ```js
   if (location.hash.slice(1) !== id) location.hash = id;
   ```

2. Al volver a la lista, limpiar con `history.replaceState(null, '', location.pathname)`
   (evita dejar un `#` suelto en la barra).

3. Escuchar `hashchange` para que atrás/adelante naveguen entre zonas.

4. Al terminar de cargar las zonas, aplicar el hash inicial: si `#Z03` existe en los
   datos, abrir esa ficha; si no, ignorarlo en silencio y mostrar la lista.

5. De paso, un esqueleto de carga: el panel se queda en blanco mientras resuelve el
   `fetch`. Pintar tres filas grises con la misma altura que las reales evita el salto
   de layout.

**Criterios de aceptación**
- `index.html#Z03` abre directo la ficha de Z03.
- Recargar con una zona abierta la deja abierta.
- Atrás/adelante del navegador se mueven entre zonas y regresan a la lista.
- Un hash inválido no rompe nada.

---

## Fuera del top 5, baratas y agradecidas

- **Móvil:** al tocar un polígono, la ficha se renderiza debajo del mapa, fuera de
  pantalla, y parece que no pasó nada. `panel.scrollIntoView({ behavior: 'smooth' })`
  dentro de `selectZone()` cuando el ancho sea menor a 800 px. 2 líneas.
- **Ficha impresa:** un bloque `@media print` que oculte mapa, controles y botones y
  deje la ficha en una hoja, para llevarla a campo.

---

## Riesgos y cuidados

- **No tocar el contrato.** `rank` y el orden del ranking son derivados de la UI; el
  export de GEE no los trae y no debe traerlos.
- **Listeners duplicados.** `renderDetail()` se llama en cada selección: los listeners
  globales (teclado, `hashchange`) se registran una vez en el arranque.
- **Zonas sin ficha.** Con el export real de GEE habrá zonas sin recomendación hasta
  correr `scripts/generar_recomendaciones.py`. Las mejoras 2 y 4 tienen que mostrarlo,
  no fallar.
- **`esc()` siempre.** Todo texto que venga de los datos o del LLM pasa por `esc()`
  (`web/app.js:29`) antes de entrar al DOM, incluidos los chips de obra.
- **Volumen real.** Probar con un `zones.geojson` de cientos de celdas, no solo con las
  12 de demostración: la 2 y la 4 son las que más sufren ahí.

## Cómo probar

```bash
python3 server/app.py          # http://localhost:8000
```

Checklist por mejora: con los filtros en "alta", navegar con el teclado de la primera a
la última zona; filtrar por obra y verificar que el contador y el CSV coincidan; abrir
`#Z05` en una pestaña nueva; recargar con una ficha abierta; revisar la consola en
blanco; y repetir todo en una ventana angosta (menos de 800 px).

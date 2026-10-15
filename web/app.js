// Base de la API; '' = mismo origen (/api/recommend). Cambiar si el servidor vive en otro host.
const API_BASE = '';

const COLORS = { alta: '#d7301f', media: '#f28c28', baja: '#f2d600' };
const STROKES = { alta: '#8f1d12', media: '#a85a0a', baja: '#9a8500' };
const DAMS = [
  { name: 'Presa Cerro Prieto', lat: 24.9297, lng: -99.4041 },
  { name: 'Presa La Boca', lat: 25.4300, lng: -100.1280 },
  { name: 'Presa El Cuchillo', lat: 25.7300, lng: -99.3000 },
];
const ATTRS = [
  ['slope_pct', 'Pendiente', '%'], ['ndvi', 'NDVI', ''], ['elev_m', 'Elevación', 'm'],
  ['burned_years', 'Años con incendio', ''], ['sand_pct', 'Arena', '%'],
  ['basin', 'Cuenca', ''], ['score', 'Índice', ''],
];

const DISTRICTS_URL = 'data/districts.geojson';  // capa de contexto (Pronatura), carga perezosa
const DAMS_URL = 'data/dams.json';               // niveles de SADM (opcional)

const LIST_LIMIT = 25;
const MARKER_MAX_ZONES = 150; // con más zonas, los marcadores solo salen a zoom >= MARKER_MIN_ZOOM
const MARKER_MIN_ZOOM = 11;

const state = { zones: [], layers: {}, markers: {}, recos: {}, cache: {}, selected: null, visible: new Set(['alta', 'media', 'baja']),
  dams: null, districts: null };
const panel = document.getElementById('panel');
let map, zoneGroup, markerGroup;

// ---------- utilidades ----------
function esc(v) {
  return String(v).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
}
function fmt(v, unit) {
  if (v === undefined || v === null || v === '') return '—';
  return unit ? `${esc(v)} ${unit}` : esc(v);
}
function priorityOf(p) { return COLORS[p.priority] ? p.priority : null; }
function colorOf(p) { return COLORS[p.priority] || '#999'; }
function badge(p) {
  const k = priorityOf(p);
  return `<span class="badge ${k || 'na'}">${k || 'n/d'}</span>`;
}
function scoreText(p) { return typeof p.score === 'number' ? p.score.toFixed(2) : '—'; }

// ---------- datos ----------
async function loadJson(url, optional) {
  try {
    const r = await fetch(url);
    if (!r.ok) throw new Error(r.status);
    return await r.json();
  } catch (e) {
    if (optional) return null;
    throw e;
  }
}

function normalize(fc) {
  // Garantiza un id por zona aunque P1 no lo exporte.
  return fc.features.map((f, i) => {
    f.properties = f.properties || {};
    if (!f.properties.id) f.properties.id = 'Z' + String(i + 1).padStart(2, '0');
    return f;
  });
}

// ---------- mapa ----------
function styleFor(p, hover) {
  return { color: hover ? '#222' : (STROKES[p.priority] || '#555'), weight: hover ? 2.5 : 1, fillColor: colorOf(p), fillOpacity: hover ? 0.85 : 0.7 };
}

function makeLayer(feature) {
  const p = feature.properties;
  if (feature.geometry && feature.geometry.type === 'Point') {
    const [lng, lat] = feature.geometry.coordinates;
    return L.circleMarker([lat, lng], { radius: 9, ...styleFor(p) });
  }
  return L.geoJSON(feature, { style: () => styleFor(p) });
}

function makeMarker(feature, layer) {
  // Un Point ya se dibuja como círculo; no necesita marcador extra.
  if (feature.geometry && feature.geometry.type === 'Point') return null;
  const center = layer.getBounds().getCenter();
  return L.circleMarker(center, { radius: 7, color: '#fff', weight: 1.5, fillColor: colorOf(feature.properties), fillOpacity: 0.9 });
}

function bindZoneEvents(layer, p) {
  const apply = (hover) => {
    const s = styleFor(p, hover);
    if (layer.setStyle) layer.setStyle(s);
  };
  layer.on('mouseover', () => apply(true));
  layer.on('mouseout', () => apply(false));
  layer.on('click', () => selectZone(p.id, false));
  layer.bindTooltip(`${esc(p.id)} · ${esc(p.priority || 'n/d')}`, { sticky: true });
}

function buildMap() {
  map = L.map('map', { preferCanvas: true });
  const bases = {
    gris: L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Light_Gray_Base/MapServer/tile/{z}/{y}/{x}', {
      maxZoom: 18, maxNativeZoom: 16, attribution: 'Tiles &copy; Esri — Esri, HERE, Garmin, &copy; OpenStreetMap contributors' }),
    topo: L.tileLayer('https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png', {
      maxZoom: 17, attribution: 'Datos &copy; OpenStreetMap, SRTM | Estilo &copy; <a href="https://opentopomap.org">OpenTopoMap</a>' }),
    sat: L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', {
      maxZoom: 18, attribution: 'Tiles &copy; Esri — Maxar, Earthstar Geographics, GIS User Community' }),
  };
  // Etiquetas encima de los polígonos (canvas en overlayPane, zIndex 400) para que los nombres sigan legibles.
  map.createPane('labels');
  map.getPane('labels').style.zIndex = 450;
  map.getPane('labels').style.pointerEvents = 'none';
  const labels = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Light_Gray_Reference/MapServer/tile/{z}/{y}/{x}', {
    pane: 'labels', maxZoom: 18, maxNativeZoom: 16 });
  let current = bases.gris.addTo(map);
  labels.addTo(map);
  document.querySelectorAll('#basemaps input').forEach(inp => inp.addEventListener('change', () => {
    map.removeLayer(current);
    current = bases[inp.value].addTo(map);
    if (inp.value === 'gris') labels.addTo(map); else map.removeLayer(labels);
  }));
  zoneGroup = L.layerGroup().addTo(map);
  markerGroup = L.layerGroup().addTo(map);
  map.on('zoomend', refreshMarkers);
  map.setView([25.3, -100.0], 8);
}

function damLevel(d) {
  // SADM publica los niveles en HTML, sin API: si no hay captura, se dice.
  const pct = typeof d.pct === 'number' ? `${d.pct} %` : 'PENDIENTE';
  const hm3 = typeof d.hm3 === 'number' ? ` · ${d.hm3} hm³` : '';
  return `${pct}${hm3}`;
}

function damPopup(d) {
  const meta = state.dams || {};
  const corte = meta.as_of ? `<div>Corte: ${esc(meta.as_of)}</div>` : '';
  const total = typeof meta.total_pct === 'number'
    ? `<div>Presas principales: ${esc(meta.total_pct)} %${typeof meta.total_hm3 === 'number' ? ` (${esc(meta.total_hm3)} hm³)` : ''}</div>` : '';
  const aviso = d.verify_coords ? '<div><em>Coordenada aproximada, por verificar.</em></div>' : '';
  const fuente = meta.source ? `<div>Fuente: ${esc(meta.source)}</div>` : '';
  return `<b>${esc(d.name)}</b><div>Nivel: ${damLevel(d)}</div>${total}${corte}${fuente}${aviso}`;
}

function addDams() {
  const icon = L.divIcon({ className: '', html: '<div class="dam-icon"></div>', iconSize: [16, 16] });
  const dams = (state.dams && Array.isArray(state.dams.dams) && state.dams.dams.length) ? state.dams.dams : DAMS;
  dams.forEach(d => L.marker([d.lat, d.lng], { icon, title: d.name }).addTo(map).bindPopup(damPopup(d)));
}

function addZones() {
  state.zones.forEach(f => {
    const layer = makeLayer(f);
    bindZoneEvents(layer, f.properties);
    state.layers[f.properties.id] = layer;
    const marker = makeMarker(f, layer);
    if (marker) {
      bindZoneEvents(marker, f.properties);
      state.markers[f.properties.id] = marker;
    }
  });
  refreshVisibility();
  const bounds = L.featureGroup(Object.values(state.layers)).getBounds();
  if (bounds.isValid()) map.fitBounds(bounds.pad(0.15));
}

function isVisible(p) {
  return state.visible.has(p.priority) || !priorityOf(p);
}

function markersAllowed() {
  return state.zones.length <= MARKER_MAX_ZONES || map.getZoom() >= MARKER_MIN_ZOOM;
}

function toggle(group, layer, show) {
  if (show) group.addLayer(layer); else group.removeLayer(layer);
}

function refreshMarkers() {
  const showMarkers = markersAllowed();
  state.zones.forEach(f => {
    const id = f.properties.id;
    if (state.markers[id]) toggle(markerGroup, state.markers[id], isVisible(f.properties) && showMarkers);
  });
}

function refreshVisibility() {
  const showMarkers = markersAllowed();
  state.zones.forEach(f => {
    const id = f.properties.id;
    const vis = isVisible(f.properties);
    toggle(zoneGroup, state.layers[id], vis);
    if (state.markers[id]) toggle(markerGroup, state.markers[id], vis && showMarkers);
  });
  if (!state.selected) renderList();
}

function setupFilters() {
  document.querySelectorAll('#filters input').forEach(inp => inp.addEventListener('change', () => {
    if (inp.checked) state.visible.add(inp.value); else state.visible.delete(inp.value);
    refreshVisibility();
  }));
}

// ---------- panel: lista ----------
function renderList() {
  const all = state.zones.map(f => f.properties).filter(isVisible)
    .sort((a, b) => (b.score ?? -1) - (a.score ?? -1));
  const items = all.slice(0, LIST_LIMIT);
  const rows = items.map(p => `
    <li tabindex="0" data-id="${esc(p.id)}">
      <span class="id">${esc(p.id)}</span>
      <span class="basin" title="${esc(p.basin ?? '')}">${fmt(p.basin)}</span>
      <span class="score">${scoreText(p)}</span>
      <span class="pill-row">${badge(p)}</span>
    </li>`).join('');
  panel.innerHTML = `<h2>Zonas prioritarias</h2><p class="count">Mostrando ${items.length} de ${all.length} zonas</p>` +
    (items.length ? `<ul class="zone-list">${rows}</ul>` : '<p class="empty">Ninguna zona visible con los filtros actuales.</p>');
  panel.querySelectorAll('li').forEach(li => {
    const go = () => selectZone(li.dataset.id, true);
    li.addEventListener('click', go);
    li.addEventListener('keydown', e => { if (e.key === 'Enter') go(); });
  });
}

// ---------- panel: detalle ----------
function selectZone(id, fly) {
  const f = state.zones.find(z => z.properties.id === id);
  if (!f) return;
  state.selected = id;
  if (fly) flyTo(state.layers[id]);
  renderDetail(f.properties);
  panel.scrollTop = 0;
}

function flyTo(layer) {
  if (layer.getBounds) map.flyToBounds(layer.getBounds().pad(1.5), { maxZoom: 13 });
  else map.flyTo(layer.getLatLng(), 12);
}

function renderDetail(p) {
  const rows = ATTRS.map(([k, label, unit]) => `<dt>${label}</dt><dd>${k === 'score' ? scoreText(p) : fmt(p[k], unit)}</dd>`).join('');
  panel.innerHTML = `
    <button class="back" id="back">← Volver a la lista</button>
    <h2>Zona ${esc(p.id)} ${badge(p)}</h2>
    <dl class="attrs">${rows}</dl>
    <h2>Recomendación de obra</h2>
    <div id="reco"></div>`;
  document.getElementById('back').addEventListener('click', () => { state.selected = null; renderList(); });
  renderReco(p);
}

function recoFor(id) { return state.cache[id] || state.recos[id]; }

function renderReco(p) {
  const box = document.getElementById('reco');
  const r = recoFor(p.id);
  if (r) {
    const label = r.source === 'reglas' ? 'reglas' : (state.cache[p.id] ? 'Grok' : 'guardada');
    box.innerHTML = recoHtml(r, label);
    return;
  }
  box.innerHTML = '<button class="primary" id="ask">Pedir recomendación a Grok</button>';
  document.getElementById('ask').addEventListener('click', () => askGrok(p));
}

function recoHtml(r, label) {
  const alts = Array.isArray(r.alternatives) && r.alternatives.length
    ? `<h4>Alternativas</h4><ul>${r.alternatives.map(a => `<li>${esc(a)}</li>`).join('')}</ul>` : '';
  return `<div class="reco">
    <h3>Obra sugerida <span class="tag">${label}</span></h3>
    <div class="work">${fmt(r.work)}</div>
    <h4>Por qué</h4><p>${fmt(r.why)}</p>
    ${alts}
    <h4>Salvedades</h4><p>${fmt(r.caveats)}</p>
  </div>`;
}

async function askGrok(p) {
  const box = document.getElementById('reco');
  box.innerHTML = '<button class="primary" disabled>Consultando a Grok…</button>';
  try {
    const res = await fetch(`${API_BASE}/api/recommend`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(p),
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    state.cache[p.id] = await res.json();
  } catch (e) {
    showAskError(p, e);
    return;
  }
  // El usuario pudo cambiar de zona mientras esperaba.
  if (state.selected === p.id) renderReco(p);
}

function showAskError(p, e) {
  if (state.selected !== p.id) return;
  const box = document.getElementById('reco');
  box.innerHTML = `<button class="primary" id="ask">Reintentar</button>
    <div class="error">No se pudo obtener la recomendación (${esc(e.message)}). Revisa que el servidor /api/recommend esté activo e inténtalo de nuevo.</div>`;
  document.getElementById('ask').addEventListener('click', () => askGrok(p));
}

// ---------- capa de contexto: distritos de riego ----------
// GeoPackage de Pronatura convertido con scripts/gpkg_a_geojson.py.
// Es contexto, no entra en el índice: se carga solo si el usuario la pide.
const DISTRICT_FIELDS = [
  ['nom_dr', 'Distrito'], ['id_dr', 'Clave'], ['nom_edo', 'Estado'],
  ['nom_rh', 'Región hidrológica'], ['num_usu', 'Usuarios'],
  ['sup_tot', 'Superficie total (ha)'], ['sup_rtot', 'Superficie regada (ha)'],
  ['vol_atot', 'Volumen concesionado (m³)'], ['ano-agr', 'Año agrícola'],
];

function districtPopup(p) {
  const conocidos = DISTRICT_FIELDS.filter(([k]) => p[k] !== undefined && p[k] !== null);
  const extras = Object.keys(p).filter(k => !DISTRICT_FIELDS.some(([f]) => f === k)).map(k => [k, k]);
  const filas = conocidos.concat(extras)
    .map(([k, label]) => `<tr><td>${esc(label)}</td><td>${fmt(p[k])}</td></tr>`).join('');
  const titulo = p.nom_dr ? `DR ${esc(p.id_dr ?? '')} ${esc(p.nom_dr)}`.trim() : 'Distrito de riego';
  return `<div class="district-popup"><h4>${titulo}</h4><table>${filas}</table>
    <p>Capa de contexto · Pronatura Noreste. No entra en el índice.</p></div>`;
}

function districtNote(texto) {
  const caja = document.getElementById('context');
  if (!caja) return;
  let nota = caja.querySelector('.muted');
  if (!nota) {
    nota = document.createElement('span');
    nota.className = 'muted';
    caja.appendChild(nota);
  }
  nota.textContent = texto;
}

async function loadDistricts() {
  if (state.districts) return state.districts;
  districtNote('Cargando distritos…');
  const fc = await loadJson(DISTRICTS_URL);
  state.districts = L.geoJSON(fc, {
    style: { color: '#1b6ca8', weight: 2, fillColor: '#1b6ca8', fillOpacity: 0.12, dashArray: '4 3' },
    onEachFeature: (f, layer) => layer.bindPopup(districtPopup(f.properties || {})),
  });
  const n = (fc.features || []).length;
  districtNote(`${n} distrito${n === 1 ? '' : 's'} · contexto`);
  return state.districts;
}

function setupDistricts() {
  const inp = document.getElementById('toggle-districts');
  if (!inp) return;
  inp.addEventListener('change', async () => {
    if (!inp.checked) {
      if (state.districts) map.removeLayer(state.districts);
      return;
    }
    try {
      (await loadDistricts()).addTo(map);
    } catch (e) {
      inp.checked = false;
      districtNote('No se pudo cargar la capa.');
      console.warn('distritos de riego:', e);
    }
  });
}

// ---------- cartera en CSV ----------
const CSV_COLS = [
  ['id', 'id'], ['priority', 'prioridad'], ['score', 'indice'], ['basin', 'cuenca'],
  ['slope_pct', 'pendiente_pct'], ['ndvi', 'ndvi'], ['ndmi', 'ndmi'], ['elev_m', 'elevacion_m'],
  ['burned_years', 'anios_con_incendio'], ['sand_pct', 'arena_pct'],
];
const CSV_RECO_COLS = [
  ['work', 'obra_sugerida'], ['why', 'por_que'], ['alternatives', 'alternativas'],
  ['caveats', 'salvedades'], ['source', 'origen_recomendacion'],
];

function csvCell(v) {
  if (v === undefined || v === null) return '';
  const texto = Array.isArray(v) ? v.join(' | ') : String(v);
  return `"${texto.replace(/"/g, '""')}"`;
}

function carteraCsv() {
  const encabezado = CSV_COLS.concat(CSV_RECO_COLS).map(([, label]) => label);
  const filas = state.zones.map(f => f.properties)
    .slice()
    .sort((a, b) => (b.score ?? -1) - (a.score ?? -1))
    .map(p => {
      const r = recoFor(p.id) || {};
      return CSV_COLS.map(([k]) => csvCell(p[k]))
        .concat(CSV_RECO_COLS.map(([k]) => csvCell(r[k]))).join(',');
    });
  // BOM para que Excel abra bien los acentos.
  return '\ufeff' + [encabezado.join(','), ...filas].join('\r\n') + '\r\n';
}

function setupCsv() {
  const btn = document.getElementById('csv');
  if (!btn) return;
  btn.addEventListener('click', () => {
    if (!state.zones.length) return;
    const url = URL.createObjectURL(new Blob([carteraCsv()], { type: 'text/csv;charset=utf-8' }));
    const a = document.createElement('a');
    a.href = url;
    a.download = 'cartera-infiltracion.csv';
    a.click();
    URL.revokeObjectURL(url);
  });
}

// ---------- aviso de datos ilustrativos ----------
function showBanner(fc) {
  const caja = document.getElementById('banner');
  if (!caja) return;
  const avisos = [];
  if (fc && fc.mock) avisos.push('las zonas de <code>data/zones.geojson</code> son una muestra de demostración, no el export de GEE');
  const porReglas = Object.values(state.recos).filter(r => r && r.source === 'reglas').length;
  if (porReglas) avisos.push(`${porReglas} recomendación${porReglas === 1 ? '' : 'es'} se generaron por reglas, sin Grok`);
  if (!avisos.length) return;
  caja.hidden = false;
  caja.innerHTML = `<b>Datos ilustrativos:</b> ${avisos.join('; ')}.`;
}

// ---------- arranque ----------
async function init() {
  buildMap();
  state.dams = await loadJson(DAMS_URL, true);
  addDams();
  setupFilters();
  setupDistricts();
  setupCsv();
  try {
    const [fc, recos] = await Promise.all([loadJson('data/zones.geojson'), loadJson('data/recommendations.json', true)]);
    state.zones = normalize(fc);
    state.recos = recos || {};
    addZones();
    renderList();
    showBanner(fc);
  } catch (e) {
    panel.innerHTML = `<div class="error">No se pudieron cargar las zonas (data/zones.geojson). ${esc(e.message)}</div>`;
  }
}
init();

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
];
const DEM_URL = 'https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{z}/{x}/{y}.png';
const DEM_ATTR = 'Terrain: <a href="https://registry.opendata.aws/terrain-tiles/">AWS Terrain Tiles</a>';
const ESRI = 'Tiles &copy; Esri';

let map;
let recos = {};

function esc(v) {
  return String(v).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
}
function matchBy(table, fallback) {
  return ['match', ['get', 'priority'], ...Object.entries(table).flat(), fallback];
}

function baseStyle() {
  return {
    version: 8,
    sources: {
      sat: { type: 'raster', tileSize: 256, maxzoom: 19, attribution: `${ESRI}, Maxar, Earthstar Geographics`,
        tiles: ['https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}'] },
      gray: { type: 'raster', tileSize: 256, maxzoom: 16, attribution: `${ESRI}, HERE, Garmin, OpenStreetMap contributors`,
        tiles: ['https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Light_Gray_Base/MapServer/tile/{z}/{y}/{x}'] },
      dem: { type: 'raster-dem', encoding: 'terrarium', tileSize: 256, maxzoom: 15, tiles: [DEM_URL], attribution: DEM_ATTR },
      shade: { type: 'raster-dem', encoding: 'terrarium', tileSize: 256, maxzoom: 15, tiles: [DEM_URL] },
    },
    layers: [
      { id: 'sat', type: 'raster', source: 'sat' },
      { id: 'gray', type: 'raster', source: 'gray', layout: { visibility: 'none' } },
      { id: 'hillshade', type: 'hillshade', source: 'shade',
        paint: { 'hillshade-exaggeration': 0.5, 'hillshade-shadow-color': '#1a2230' } },
    ],
  };
}

function boundsOf(fc) {
  const b = new maplibregl.LngLatBounds();
  const add = c => (typeof c[0] === 'number' ? b.extend(c) : c.forEach(add));
  fc.features.forEach(f => add(f.geometry.coordinates));
  return b;
}

function addZones(fc) {
  map.addSource('zones', { type: 'geojson', data: fc });
  map.addLayer({ id: 'zones-fill', type: 'fill', source: 'zones',
    paint: { 'fill-color': matchBy(COLORS, '#999'), 'fill-opacity': 0.6 } });
  map.addLayer({ id: 'zones-line', type: 'line', source: 'zones',
    paint: { 'line-color': matchBy(STROKES, '#555'), 'line-width': 0.8 } });
}

function popupHtml(p) {
  const k = COLORS[p.priority] ? p.priority : null;
  const rows = ATTRS.map(([key, label, unit]) => {
    const v = p[key];
    const text = v === undefined || v === null || v === '' ? '—' : esc(v) + (unit ? ' ' + unit : '');
    return `<dt>${label}</dt><dd>${text}</dd>`;
  }).join('');
  const score = typeof p.score === 'number' ? p.score.toFixed(2) : '—';
  const r = recos[p.id];
  const reco = r ? `<div class="reco"><b>${esc(r.work || '')}</b><br>${esc(r.why || '')}</div>` : '';
  return `<div class="pop"><h3>${esc(p.id)}</h3><div class="basin">${esc(p.basin || '—')}</div>
    <span class="badge ${k || 'na'}">${k || 'n/d'}</span> Índice ${score}<dl>${rows}</dl>${reco}</div>`;
}

function wireInteraction() {
  map.on('click', 'zones-fill', e => {
    const f = e.features[0];
    new maplibregl.Popup({ maxWidth: '260px' }).setLngLat(e.lngLat).setHTML(popupHtml(f.properties)).addTo(map);
  });
  map.on('mouseenter', 'zones-fill', () => { map.getCanvas().style.cursor = 'pointer'; });
  map.on('mouseleave', 'zones-fill', () => { map.getCanvas().style.cursor = ''; });
}

function addDams() {
  DAMS.forEach(d => {
    const el = document.createElement('div');
    el.className = 'dam-marker';
    new maplibregl.Marker({ element: el }).setLngLat([d.lng, d.lat])
      .setPopup(new maplibregl.Popup({ offset: 12 }).setText(d.name)).addTo(map);
  });
}

function wireControls() {
  document.querySelectorAll('input[name=base]').forEach(r => r.addEventListener('change', () => {
    map.setLayoutProperty('sat', 'visibility', r.value === 'sat' && r.checked ? 'visible' : 'none');
    map.setLayoutProperty('gray', 'visibility', r.value === 'gray' && r.checked ? 'visible' : 'none');
  }));
  const boxes = document.querySelectorAll('input[data-p]');
  boxes.forEach(b => b.addEventListener('change', () => {
    const on = [...boxes].filter(x => x.checked).map(x => x.dataset.p);
    const filter = ['in', ['get', 'priority'], ['literal', on]];
    ['zones-fill', 'zones-line'].forEach(id => map.setFilter(id, filter));
  }));
}

function enableTerrain() {
  try {
    map.setTerrain({ source: 'dem', exaggeration: 1.6 });
  } catch (e) {
    console.warn('Terreno 3D no disponible; se muestra el mapa plano.', e);
  }
}

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

function startMap(fc) {
  map = new maplibregl.Map({ container: 'map', style: baseStyle(), center: [-100.3, 25.2], zoom: 8,
    maxPitch: 80, canvasContextAttributes: { antialias: true } });
  map.addControl(new maplibregl.NavigationControl({ visualizePitch: true }), 'bottom-right');
  map.addControl(new maplibregl.TerrainControl({ source: 'dem', exaggeration: 1.6 }), 'bottom-right');
  map.on('error', e => console.warn('Error de mapa:', e && e.error && e.error.message));
  // Se cargan los datos antes de crear el mapa para evitar carreras con el evento 'load'.
  map.on('load', () => {
    enableTerrain();
    addZones(fc);
    addDams();
    wireInteraction();
    wireControls();
    map.fitBounds(boundsOf(fc), { padding: 40, duration: 0 });
    map.easeTo({ pitch: 60, bearing: -25, duration: 2500 });
  });
}

async function init() {
  const [fc, r] = await Promise.all([loadJson('data/zones.geojson'), loadJson('data/recommendations.json', true)]);
  recos = r || {};
  try {
    startMap(fc);
  } catch (e) {
    console.warn('WebGL no disponible', e);
    document.getElementById('map').textContent = 'Tu navegador no pudo iniciar el mapa (WebGL).';
  }
}

init().catch(e => console.warn('Fallo al iniciar la vista 3D', e));

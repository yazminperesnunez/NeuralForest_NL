// ============================================================================
// Reto 1 · Infiltración (Pronatura Noreste)
// Índice de prioridad de restauración en partes altas de las cuencas que
// alimentan las presas de Monterrey, N.L.
// Pegar en code.earthengine.google.com y dar Run. No necesita editar nada.
// Tiempo esperado: 2 a 6 minutos (los mensajes salen en la pestaña Console).
// ============================================================================

// ---------- CONFIG ----------
var MIN_ELEV = 1000;          // m. Solo partes altas.
var CELL_SIZE_M = 3000;       // m. Más grande = más rápido (prueba 5000).
var SCALE_M = 100;            // m. Escala de reduceRegions.
var DATE_START = '2023-01-01';
var DATE_END = '2026-01-01';  // Acorta a 2024-01-01 si hay timeout.
var DRY_MONTHS = [2, 5];      // Temporada seca: feb a may.
var MAX_CLOUD_PCT = 20;
var SCL_KEEP = [4, 5, 6, 7, 11];
var FIRE_YEAR_START = 2015;
var FIRE_YEAR_END = 2025;
var FIRE_CAP = 3;             // 3 o más años quemados = máximo.
var SLOPE_PEAK_PCT = 20;      // Pendiente ideal (%).
var SLOPE_HALF_WIDTH = 40;    // Qué tan rápido cae la idoneidad.

// P4 (líder de dominio): cambia los pesos aquí. Deben sumar 1.
var WEIGHTS = { ndvi: 0.30, ndmi: 0.20, slope: 0.20, sand: 0.15, fire: 0.15 };

// Propiedades que lee la página web. No cambiar nombres.
var OUT_PROPS = ['id', 'priority', 'score', 'slope_pct', 'ndvi', 'elev_m',
                 'burned_years', 'sand_pct', 'basin', 'ndmi'];

// ---------- ZONA DE ESTUDIO ----------
function poly(coords) {
  // geodesic=false: los bordes compartidos coinciden exactamente.
  return ee.Geometry.Polygon([coords], null, false);
}

function buildBasins() {
  // Si dibujaste una geometría con las herramientas del mapa, se usa esa.
  if (typeof geometry !== 'undefined') {
    return ee.FeatureCollection([
      ee.Feature(ee.Geometry(geometry), { name: 'Zona dibujada' })
    ]);
  }
  return ee.FeatureCollection([
    ee.Feature(poly([[-100.80, 25.40], [-100.80, 25.72], [-100.25, 25.72],
                     [-100.25, 25.55], [-100.45, 25.40]]),
               { name: 'Río Santa Catarina → El Cuchillo' }),
    ee.Feature(poly([[-100.45, 25.40], [-100.25, 25.55], [-100.05, 25.45],
                     [-100.05, 25.20], [-100.40, 25.15]]),
               { name: 'Presa La Boca' }),
    ee.Feature(poly([[-100.30, 24.60], [-100.30, 25.00], [-99.85, 25.05],
                     [-99.70, 24.85], [-99.85, 24.60]]),
               { name: 'Presa Cerro Prieto' })
  ]);
}

var basins = buildBasins();
var zona = basins.geometry();

print('1/4 Zona definida. Calculando capas...');

// ---------- CAPAS ----------
function robustScale(img, bandName, scale) {
  var pts = img.sample({ region: zona, scale: scale, numPixels: 5000, seed: 1, geometries: false });
  var stats = pts.reduceColumns({ reducer: ee.Reducer.percentile([2, 98]), selectors: [bandName] });
  var min = ee.Number(stats.get('p2'));
  var max = ee.Number(stats.get('p98'));
  return img.unitScale(min, max).clamp(0, 1);
}

function maskClouds(img) {
  var scl = img.select('SCL');
  var ok = ee.Image(0);
  SCL_KEEP.forEach(function (c) { ok = ok.or(scl.eq(c)); });
  return img.updateMask(ok);
}

function terrain() {
  var elev = ee.Image('USGS/SRTMGL1_003').select('elevation');
  var slopeDeg = ee.Terrain.slope(elev);
  var slopePct = slopeDeg.multiply(Math.PI / 180).tan().multiply(100).rename('slope_pct');
  var slopeS = slopePct.subtract(SLOPE_PEAK_PCT).abs().divide(SLOPE_HALF_WIDTH)
    .multiply(-1).add(1).clamp(0, 1).rename('slope_s');
  return { elev: elev.rename('elev_m'), slopePct: slopePct, slopeS: slopeS };
}

function vegetation() {
  var s2 = ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')
    .filterBounds(zona)
    .filterDate(DATE_START, DATE_END)
    .filter(ee.Filter.calendarRange(DRY_MONTHS[0], DRY_MONTHS[1], 'month'))
    .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', MAX_CLOUD_PCT))
    .map(maskClouds)
    .select(['B4', 'B8', 'B11']);
  var comp = s2.median();
  return {
    ndvi: comp.normalizedDifference(['B8', 'B4']).rename('ndvi'),
    ndmi: comp.normalizedDifference(['B8', 'B11']).rename('ndmi')
  };
}

function sand() {
  return ee.Image('OpenLandMap/SOL/SOL_SAND-WFRACTION_USDA-3A1A1A_M/v02')
    .select('b0').rename('sand_pct');
}

function burnedYears() {
  var years = ee.List.sequence(FIRE_YEAR_START, FIRE_YEAR_END);
  var perYear = years.map(function (y) {
    var start = ee.Date.fromYMD(y, 1, 1);
    return ee.ImageCollection('MODIS/061/MCD64A1')
      .filterDate(start, start.advance(1, 'year'))
      .select('BurnDate').max().gt(0).unmask(0).rename('burned_years');
  });
  return ee.ImageCollection.fromImages(perYear).sum().rename('burned_years');
}

function buildStack() {
  var t = terrain();
  var veg = vegetation();
  var highMask = t.elev.gte(MIN_ELEV);

  var ndvi = veg.ndvi.updateMask(highMask);
  var ndmi = veg.ndmi.updateMask(highMask);
  var sandImg = sand();
  var fire = burnedYears();

  var ndviP = ee.Image(1).subtract(robustScale(ndvi, 'ndvi', SCALE_M));
  var ndmiP = ee.Image(1).subtract(robustScale(ndmi, 'ndmi', SCALE_M));
  var sandP = robustScale(sandImg, 'sand_pct', 250);
  var fireP = fire.min(FIRE_CAP).divide(FIRE_CAP);

  var score = ndviP.multiply(WEIGHTS.ndvi)
    .add(ndmiP.multiply(WEIGHTS.ndmi))
    .add(t.slopeS.multiply(WEIGHTS.slope))
    .add(sandP.multiply(WEIGHTS.sand))
    .add(fireP.multiply(WEIGHTS.fire))
    .updateMask(highMask).rename('score');

  var stack = ee.Image.cat([score, ndvi, ndmi, t.slopePct, t.elev, sandImg, fire])
    .updateMask(score.mask());
  return { score: score, stack: stack };
}

var layers = buildStack();

// ---------- CELDAS ----------
function labelBasin(cell) {
  var names = basins.filterBounds(cell.geometry().centroid(1)).aggregate_array('name');
  // add('') evita error si el centroide cae fuera de todas las cuencas.
  return cell.set('basin', ee.List(names).add('').get(0));
}

function round(x, decimals) {
  var k = Math.pow(10, decimals);
  return ee.Number(x).multiply(k).round().divide(k);
}

function buildCells() {
  var grid = zona.coveringGrid(ee.Projection('EPSG:32614'), CELL_SIZE_M)
    .map(labelBasin)
    .filter(ee.Filter.neq('basin', ''));

  var stats = layers.stack.reduceRegions({
    collection: grid,
    reducer: ee.Reducer.mean(),
    scale: SCALE_M,
    tileScale: 4
  }).filter(ee.Filter.notNull(['score']));

  var cuts = stats.reduceColumns({
    reducer: ee.Reducer.percentile([33.3, 66.7], ['lo', 'hi']),
    selectors: ['score']
  });
  var lo = ee.Number(cuts.get('lo'));
  var hi = ee.Number(cuts.get('hi'));

  var sorted = stats.sort('score', false);
  var list = sorted.toList(sorted.size());
  var ranks = ee.List.sequence(0, sorted.size().subtract(1));

  var cells = ee.FeatureCollection(ranks.map(function (i) {
    var f = ee.Feature(list.get(i));
    var s = ee.Number(f.get('score'));
    var priority = ee.Algorithms.If(s.gt(hi), 'alta', ee.Algorithms.If(s.gt(lo), 'media', 'baja'));
    return ee.Feature(f.geometry().transform('EPSG:4326', 1), {
      id: ee.String('Z').cat(ee.Number(i).add(1).int().format('%03d')),
      priority: priority,
      score: round(s, 2),
      ndvi: round(f.get('ndvi'), 2),
      ndmi: round(f.get('ndmi'), 2),
      slope_pct: round(f.get('slope_pct'), 1),
      sand_pct: round(f.get('sand_pct'), 1),
      elev_m: ee.Number(f.get('elev_m')).round().int(),
      burned_years: ee.Number(f.get('burned_years')).round().int(),
      basin: f.get('basin')
    });
  }));
  return { cells: cells, lo: lo, hi: hi };
}

var result = buildCells();
var cells = result.cells;

// ---------- MAPA ----------
var COLORS = { alta: '#d73027', media: '#fc8d59', baja: '#fee08b' };

function styled(cellsFc) {
  return cellsFc.map(function (f) {
    var c = ee.Dictionary(COLORS).get(f.get('priority'));
    return f.set('style', { color: '#444444', width: 1, fillColor: ee.String(c).cat('99') });
  }).style({ styleProperty: 'style' });
}

Map.setOptions('TERRAIN');
Map.centerObject(zona, 9);
Map.addLayer(layers.score, { min: 0, max: 1,
  palette: ['#ffffb2', '#fecc5c', '#fd8d3c', '#f03b20', '#bd0026'] },
  'Score de prioridad (0-1)', false);
Map.addLayer(styled(cells), {}, 'Celdas por prioridad');
Map.addLayer(basins.style({ color: '#0033cc', fillColor: '00000000', width: 2 }), {}, 'Cuencas');

// ---------- RESUMEN ----------
function summary() {
  var top5 = cells.limit(5, 'score', false).map(function (f) {
    return f.set('label', ee.String(f.get('id')).cat(' | ').cat(f.get('basin'))
      .cat(' | score ').cat(ee.Number(f.get('score')).format('%.2f')));
  }).aggregate_array('label');
  return ee.Dictionary({
    total: cells.size(),
    counts: cells.aggregate_histogram('priority'),
    p33: result.lo,
    p67: result.hi,
    top5: top5
  });
}

print('2/4 Calculando celdas y resumen (puede tardar unos minutos)...');
summary().evaluate(function (s, err) {
  if (err) {
    print('ERROR en el resumen: ' + err);
    print('Prueba CELL_SIZE_M = 5000 o DATE_START = 2024-01-01.');
    return;
  }
  print('3/4 Resumen listo.');
  print('Total de celdas: ' + s.total);
  print('Celdas por prioridad (alta/media/baja):', s.counts);
  print('Umbrales de terciles: p33.3 = ' + s.p33.toFixed(3) + ', p66.7 = ' + s.p67.toFixed(3));
  print('Top 5 celdas:');
  s.top5.forEach(function (line) { print('  ' + line); });
});

// ---------- DESCARGA ----------
// selectors must stay null: a selectors list drops the geometry in GeoJSON.
cells.getDownloadURL('geojson', null, 'zones', function (url, err) {
  if (err || !url) {
    print('ERROR al crear el link de descarga: ' + err);
    print('Usa la pestaña Tasks y pulsa Run en la tarea "zones".');
    return;
  }
  print('4/4 Link listo (haz clic):');
  print(ui.Label('Descarga zones.geojson →', {}, url));
});

// Respaldo: tarea de exportación a Google Drive (pestaña Tasks → Run).
Export.table.toDrive({
  collection: cells,
  description: 'zones',
  fileFormat: 'GeoJSON'
});

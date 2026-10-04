let ALL_PROPS = [];
let filtered = [];
let shown = 0;
const PAGE_SIZE = 24;
let currentOp = '';
let currentSeg = AM.segActual();   // 'vivienda' | 'comercial'  (también por URL: ?seg=comercial)
let META = null;

const grid = document.getElementById('grid');
const resultsCount = document.getElementById('resultsCount');
const statsStrip = document.getElementById('statsStrip');
const loadMoreBtn = document.getElementById('loadMore');

// Opciones del filtro "Tipo" según el segmento (cada opción es un grupo de tipos de AM.GRUPOS_TIPO)
const TIPOS_FILTRO = {
  vivienda: [['casa', 'Casa'], ['departamento', 'Departamento'], ['terreno', 'Terreno'], ['edificio', 'Edificio']],
  comercial: [['local', 'Local comercial'], ['oficina', 'Oficina'], ['bodega', 'Bodega o nave'], ['terreno', 'Terreno'], ['edificio', 'Edificio']],
};
// Rangos de precio máximo según segmento y operación (sin piso: cualquier precio)
const PRECIOS_FILTRO = {
  'vivienda|VENTA': [500000, 1000000, 1500000, 2000000, 3000000, 5000000, 8000000, 12000000, 20000000, 40000000],
  'vivienda|RENTA': [8000, 12000, 18000, 25000, 40000, 60000, 100000],
  'comercial|VENTA': [1000000, 2000000, 5000000, 10000000, 20000000, 50000000, 100000000],
  'comercial|RENTA': [15000, 30000, 50000, 100000, 200000, 500000],
};
const SOLO_VIVIENDA = ['fRecamaras', 'fBanos', 'fNiveles'];   // no aplican a inmuebles comerciales

function money0(n) { return '$' + n.toLocaleString('es-MX'); }

function armarOpcionesTipo() {
  const sel = document.getElementById('fTipo');
  sel.innerHTML = '<option value="">Cualquiera</option>' +
    TIPOS_FILTRO[currentSeg].map(([v, t]) => `<option value="${v}">${t}</option>`).join('');
}

function armarOpcionesPrecio() {
  const sel = document.getElementById('fPrecioMax');
  const previo = sel.value;
  const clave = currentSeg + '|' + (currentOp === 'RENTA' ? 'RENTA' : 'VENTA');
  const lista = PRECIOS_FILTRO[clave];
  sel.innerHTML = '<option value="">Sin límite</option>' +
    lista.map(n => `<option value="${n}">${money0(n)}${currentOp === 'RENTA' ? '/mes' : ''}</option>`).join('');
  if (lista.map(String).includes(previo)) sel.value = previo;
}

function armarColonias() {
  const municipio = document.getElementById('fMunicipio').value;
  const cuenta = {};
  ALL_PROPS.forEach(p => {
    if (AM.segDe(p) !== currentSeg || !p.colonia) return;
    if (municipio && p.municipio !== municipio) return;
    cuenta[p.colonia] = (cuenta[p.colonia] || 0) + 1;
  });
  const top = Object.entries(cuenta).sort((a, b) => b[1] - a[1]).slice(0, 120).map(e => e[0]).sort((a, b) => a.localeCompare(b, 'es'));
  document.getElementById('listaColonias').innerHTML = top.map(c => `<option value="${AM.esc(c)}"></option>`).join('');
}

function aplicarSegmentoEnPantalla() {
  document.querySelectorAll('#segToggle button').forEach(b => b.classList.toggle('active', b.dataset.seg === currentSeg));
  SOLO_VIVIENDA.forEach(id => {
    const campo = document.getElementById(id).closest('.field');
    if (campo) campo.style.display = currentSeg === 'comercial' ? 'none' : '';
  });
  armarOpcionesTipo();
  armarOpcionesPrecio();
  armarColonias();
}

function applyFilters() {
  const texto = AM.norm(document.getElementById('fTexto').value);
  const municipio = document.getElementById('fMunicipio').value;
  const tipo = document.getElementById('fTipo').value;
  const precioMax = document.getElementById('fPrecioMax').value;
  const recamaras = document.getElementById('fRecamaras').value;
  const banos = document.getElementById('fBanos').value;
  const m2Min = document.getElementById('fM2Min').value;
  const m2Max = document.getElementById('fM2Max').value;
  const niveles = document.getElementById('fNiveles').value;
  const orden = document.getElementById('fOrden').value;
  const fotoPrimero = document.getElementById('fFotoPrimero').checked;
  const gruposTipo = tipo ? (AM.GRUPOS_TIPO[tipo] || [tipo]) : null;

  filtered = ALL_PROPS.filter(p => {
    if (AM.segDe(p) !== currentSeg) return false;
    if (currentOp && p.operacion !== currentOp) return false;
    if (municipio && p.municipio !== municipio) return false;
    if (gruposTipo && !gruposTipo.includes(p.tipo)) return false;
    if (precioMax && (!AM.esMXN(p) || p.precio > parseInt(precioMax))) return false;
    if (recamaras) {
      const min = parseInt(recamaras);
      if (!p.recamaras) return false;
      if (min === 5 ? p.recamaras < 5 : p.recamaras !== min) return false;
    }
    if (banos && (!p.banos || p.banos < parseInt(banos))) return false;
    if (m2Min && (!p.m2 || p.m2 < parseFloat(m2Min))) return false;
    if (m2Max && (!p.m2 || p.m2 > parseFloat(m2Max))) return false;
    if (niveles) {
      const n = parseInt(niveles);
      if (!p.niveles) return false;
      if (n === 3 ? p.niveles < 3 : p.niveles !== n) return false;
    }
    // La búsqueda ignora acentos y mayúsculas, y revisa título y colonia.
    if (texto && !AM.norm((p.titulo || '') + ' ' + (p.colonia || '')).includes(texto)) return false;
    return true;
  });

  filtered = AM.ordenar(filtered, orden, fotoPrimero);

  shown = 0;
  grid.innerHTML = '';
  renderNextPage();
  resultsCount.textContent = `${filtered.length.toLocaleString('es-MX')} resultado${filtered.length !== 1 ? 's' : ''}`;
}

function renderNextPage() {
  const next = filtered.slice(shown, shown + PAGE_SIZE);
  if (shown === 0 && next.length === 0) {
    grid.innerHTML = `<div class="empty-state"><h3>No encontramos nada con esos filtros</h3><p>Prueba ampliando el rango de precio o la zona — o pregúntale a MAX, tenemos más opciones que no siempre están indexadas aquí.</p></div>`;
    loadMoreBtn.style.display = 'none';
    return;
  }
  grid.insertAdjacentHTML('beforeend', next.map(p => AM.cardHTML(p)).join(''));
  shown += next.length;
  loadMoreBtn.style.display = shown < filtered.length ? 'block' : 'none';
  AM.actualizarUI();
}

function renderStats() {
  const base = ALL_PROPS.filter(p => AM.segDe(p) === currentSeg);
  const ventas = base.filter(p => p.operacion === 'VENTA').length;
  const rentas = base.filter(p => p.operacion === 'RENTA').length;
  const etiqueta = currentSeg === 'comercial' ? 'inmuebles comerciales' : 'propiedades de vivienda';
  let actualizado = '';
  if (META && META.actualizado) {
    const f = new Date(META.actualizado);
    if (!isNaN(f)) actualizado = `<div><b>${f.toLocaleDateString('es-MX', { day: 'numeric', month: 'short' })}</b>inventario actualizado</div>`;
  }
  statsStrip.innerHTML = `
    <div><b>${base.length.toLocaleString('es-MX')}</b>${etiqueta}</div>
    <div><b>${ventas.toLocaleString('es-MX')}</b>en venta</div>
    <div><b>${rentas.toLocaleString('es-MX')}</b>en renta</div>
    <div><b>${new Set(base.map(p => p.municipio)).size}</b>municipios de la ZMG</div>
    ${actualizado}
  `;
}

function cambiarSegmento(seg) {
  currentSeg = seg;
  ['fTipo', 'fPrecioMax', 'fRecamaras', 'fBanos', 'fNiveles'].forEach(id => { document.getElementById(id).value = ''; });
  const u = new URL(location.href);
  if (seg === 'comercial') u.searchParams.set('seg', 'comercial'); else u.searchParams.delete('seg');
  history.replaceState(null, '', u);
  aplicarSegmentoEnPantalla();
  renderStats();
  applyFilters();
}

document.getElementById('segToggle').addEventListener('click', (e) => {
  const btn = e.target.closest('button');
  if (!btn || btn.dataset.seg === currentSeg) return;
  cambiarSegmento(btn.dataset.seg);
});

document.getElementById('opToggle').addEventListener('click', (e) => {
  const btn = e.target.closest('button');
  if (!btn) return;
  document.querySelectorAll('#opToggle button').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  currentOp = btn.dataset.op;
  armarOpcionesPrecio();
  applyFilters();
});

document.getElementById('btnBuscar').addEventListener('click', applyFilters);
loadMoreBtn.addEventListener('click', renderNextPage);
['fTipo', 'fPrecioMax', 'fRecamaras', 'fBanos', 'fM2Min', 'fM2Max', 'fNiveles', 'fOrden', 'fFotoPrimero'].forEach(id => {
  document.getElementById(id).addEventListener('change', applyFilters);
});
document.getElementById('fMunicipio').addEventListener('change', () => { armarColonias(); applyFilters(); });
let textoTimeout;
document.getElementById('fTexto').addEventListener('input', () => {
  clearTimeout(textoTimeout);
  textoTimeout = setTimeout(applyFilters, 350);
});

aplicarSegmentoEnPantalla();
fetch('inventario-meta.json').then(r => r.ok ? r.json() : null).catch(() => null)
  .then(meta => { META = meta; return fetch('data.json'); })
  .then(r => r.json())
  .then(data => {
    ALL_PROPS = data;
    renderStats();
    armarColonias();
    applyFilters();
  })
  .catch(() => {
    grid.innerHTML = `<div class="empty-state"><h3>No se pudo cargar el inventario</h3><p>Intenta recargar la página.</p></div>`;
  });

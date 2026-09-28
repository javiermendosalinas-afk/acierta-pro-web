let ALL_PROPS = [];
let filtered = [];
let shown = 0;
const PAGE_SIZE = 24;
let currentOp = '';

const grid = document.getElementById('grid');
const resultsCount = document.getElementById('resultsCount');
const statsStrip = document.getElementById('statsStrip');
const loadMoreBtn = document.getElementById('loadMore');

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

  filtered = ALL_PROPS.filter(p => {
    if (currentOp && p.operacion !== currentOp) return false;
    if (municipio && p.municipio !== municipio) return false;
    if (tipo && p.tipo !== tipo) return false;
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
  const total = ALL_PROPS.length;
  const ventas = ALL_PROPS.filter(p => p.operacion === 'VENTA').length;
  const rentas = ALL_PROPS.filter(p => p.operacion === 'RENTA').length;
  statsStrip.innerHTML = `
    <div><b>${total.toLocaleString('es-MX')}</b>propiedades activas</div>
    <div><b>${ventas.toLocaleString('es-MX')}</b>en venta</div>
    <div><b>${rentas.toLocaleString('es-MX')}</b>en renta</div>
    <div><b>5</b>municipios de la ZMG</div>
  `;
}

document.getElementById('opToggle').addEventListener('click', (e) => {
  const btn = e.target.closest('button');
  if (!btn) return;
  document.querySelectorAll('#opToggle button').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  currentOp = btn.dataset.op;
  applyFilters();
});

document.getElementById('btnBuscar').addEventListener('click', applyFilters);
loadMoreBtn.addEventListener('click', renderNextPage);
['fMunicipio', 'fTipo', 'fPrecioMax', 'fRecamaras', 'fBanos', 'fM2Min', 'fM2Max', 'fNiveles', 'fOrden', 'fFotoPrimero'].forEach(id => {
  document.getElementById(id).addEventListener('change', applyFilters);
});
let textoTimeout;
document.getElementById('fTexto').addEventListener('input', () => {
  clearTimeout(textoTimeout);
  textoTimeout = setTimeout(applyFilters, 350);
});

fetch('data.json')
  .then(r => r.json())
  .then(data => {
    ALL_PROPS = data;
    renderStats();
    applyFilters();
  })
  .catch(() => {
    grid.innerHTML = `<div class="empty-state"><h3>No se pudo cargar el inventario</h3><p>Intenta recargar la página.</p></div>`;
  });

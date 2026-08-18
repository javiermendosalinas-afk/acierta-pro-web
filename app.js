let ALL_PROPS = [];
let filtered = [];
let shown = 0;
const PAGE_SIZE = 24;
let currentOp = '';

const grid = document.getElementById('grid');
const resultsCount = document.getElementById('resultsCount');
const statsStrip = document.getElementById('statsStrip');
const loadMoreBtn = document.getElementById('loadMore');

function money(n) {
  return '$' + Math.round(n).toLocaleString('es-MX');
}

function iconHouse() {
  return `<svg viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="1.5"><path d="M3 11.5L12 4l9 7.5"/><path d="M5 10v9a1 1 0 0 0 1 1h4v-6h4v6h4a1 1 0 0 0 1-1v-9"/></svg>`;
}

function cardHTML(p) {
  const metaBits = [];
  if (p.recamaras) metaBits.push(`${p.recamaras} rec`);
  if (p.banos) metaBits.push(`${p.banos} baños`);
  if (p.m2) metaBits.push(`${Math.round(p.m2)} m²`);
  const unidad = p.operacion === 'RENTA' ? '/mes' : '';
  const waTexto = encodeURIComponent(`Hola, me interesa esta propiedad: ${p.titulo} (${p.eb || 'sin código'}) — ${p.liga}`);
  const mediaContent = p.foto
    ? `<img src="${p.foto}" alt="${p.titulo}" loading="lazy" onerror="this.parentElement.innerHTML='${iconHouse().replace(/'/g, "\\'")}'">`
    : iconHouse();
  return `
  <div class="card">
    <div class="card-media" ${p.foto ? 'style="background:#0f1f3d"' : ''}>
      <span class="card-op">${p.operacion}</span>
      ${mediaContent}
      <span class="card-tipo">${p.tipo}</span>
    </div>
    <div class="card-body">
      <div class="card-price">${money(p.precio)}<span> MXN${unidad}</span></div>
      <div class="card-title">${p.titulo}</div>
      <div class="card-loc">📍 ${p.municipio}</div>
      <div class="card-meta">${metaBits.map(b => `<span>${b}</span>`).join('')}</div>
      <div class="card-cta">
        <a class="btn-outline" href="${p.liga}" target="_blank" rel="noopener">Ver ficha</a>
        <a class="btn-solid" href="https://wa.me/523333777337?text=${waTexto}" target="_blank" rel="noopener">WhatsApp</a>
      </div>
    </div>
  </div>`;
}

function applyFilters() {
  const municipio = document.getElementById('fMunicipio').value;
  const tipo = document.getElementById('fTipo').value;
  const precioMax = document.getElementById('fPrecioMax').value;
  const recamaras = document.getElementById('fRecamaras').value;

  filtered = ALL_PROPS.filter(p => {
    if (currentOp && p.operacion !== currentOp) return false;
    if (municipio && p.municipio !== municipio) return false;
    if (tipo && p.tipo !== tipo) return false;
    if (precioMax && p.precio > parseInt(precioMax)) return false;
    if (recamaras && (!p.recamaras || p.recamaras < parseInt(recamaras))) return false;
    return true;
  });

  filtered.sort((a, b) => a.precio - b.precio);
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
  grid.insertAdjacentHTML('beforeend', next.map(cardHTML).join(''));
  shown += next.length;
  loadMoreBtn.style.display = shown < filtered.length ? 'block' : 'none';
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
['fMunicipio', 'fTipo', 'fPrecioMax', 'fRecamaras'].forEach(id => {
  document.getElementById(id).addEventListener('change', applyFilters);
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

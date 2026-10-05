/* Acierta Max — utilidades compartidas: tarjetas, comparador y análisis de precio */
(function () {
  const AM = (window.AM = {});

  // ── Básicos ────────────────────────────────────────────
  AM.ir = url => { location.href = url; };   // redirecciones (fácil de interceptar en pruebas)

  AM.esc = s => String(s == null ? '' : s).replace(/[&<>"']/g,
    c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  AM.money = n => '$' + Math.round(n).toLocaleString('es-MX');
  AM.norm = s => String(s || '').normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase().trim();
  AM.iconHouse = () => '<svg viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="1.5"><path d="M3 11.5L12 4l9 7.5"/><path d="M5 10v9a1 1 0 0 0 1 1h4v-6h4v6h4a1 1 0 0 0 1-1v-9"/></svg>';

  AM.GRUPOS_TIPO = {
    casa: ['casa', 'casa en condominio', 'casa con uso de suelo', 'quinta', 'rancho', 'villa'],
    departamento: ['departamento'],
    terreno: ['terreno', 'terreno industrial', 'terreno comercial'],
    local: ['local comercial', 'local en centro comercial'],
    oficina: ['oficina'],
    bodega: ['bodega comercial', 'bodega industrial', 'nave industrial'],
    edificio: ['edificio'],
  };
  AM.GRUPO_LABEL = {
    casa: 'casas', departamento: 'departamentos', terreno: 'terrenos', local: 'locales comerciales',
    oficina: 'oficinas', bodega: 'bodegas y naves', edificio: 'edificios', otro: 'propiedades',
  };
  AM.grupoDe = tipo => {
    for (const [k, arr] of Object.entries(AM.GRUPOS_TIPO)) if (arr.includes(tipo)) return k;
    return 'otro';
  };
  // Algunas publicaciones (pocas, sobre todo edificios y macro-lotes) están en dólares: no se mezclan con pesos.
  AM.esMXN = p => !p.moneda || p.moneda === 'MXN';
  // Segmento: cada ficha es de 'vivienda' o 'comercial' (lo decide el sincronizador al traer el inventario).
  // Si una ficha vieja no trae el campo, se deduce del tipo.
  AM.TIPOS_COMERCIALES = ['oficina', 'local comercial', 'local en centro comercial', 'bodega comercial', 'bodega industrial', 'nave industrial', 'terreno comercial', 'terreno industrial'];
  AM.segDe = p => p.segmento || (AM.TIPOS_COMERCIALES.includes(p.tipo) ? 'comercial' : 'vivienda');
  AM.soloVivienda = lista => lista.filter(p => AM.segDe(p) === 'vivienda');
  AM.segActual = () => new URLSearchParams(location.search).get('seg') === 'comercial' ? 'comercial' : 'vivienda';

  // Fotos: EasyBroker entrega la imagen al tamaño que se pida en la URL (width/height). Se pide grande y,
  // si no carga, se vuelve a la miniatura original; si tampoco, se quita la imagen y queda el ícono de casa.
  AM.fotoTam = (url, w, h) => {
    if (!url) return url;
    url = /[?&]width=\d+/.test(url) ? url.replace(/([?&])width=\d+/, '$1width=' + w) : url + (url.includes('?') ? '&' : '?') + 'width=' + w;
    return /[?&]height=\d+/.test(url) ? url.replace(/([?&])height=\d+/, '$1height=' + h) : url + '&height=' + h;
  };
  AM.fotoImg = (url, w, h, alt, extra) =>
    `<img src="${AM.esc(AM.fotoTam(url, w, h))}" data-f="${AM.esc(url)}" alt="${AM.esc(alt || '')}" ${extra || ''} onerror="if(this.dataset.f){var o=this.dataset.f;this.dataset.f='';this.src=o}else{this.remove()}">`;
  AM.precioTxt = p => (AM.esMXN(p) ? AM.money(p.precio) : 'US' + AM.money(p.precio));
  AM.precioM2 = p => (p.m2 > 0 && p.precio > 0 && AM.esMXN(p)) ? p.precio / p.m2 : null;
  // Un mismo código EB puede estar publicado en venta Y en renta (dos anuncios distintos):
  // el identificador único es código + operación (p. ej. EB-VM0258-R).
  AM.clave = p => p.eb + '-' + (p.operacion === 'RENTA' ? 'R' : 'V');
  AM.buscar = (todas, clave) => todas.find(p => AM.clave(p) === clave) || todas.find(p => p.eb === clave) || null;
  AM.fichaUrl = p => 'ficha.html?eb=' + encodeURIComponent(p.eb) + '&op=' + p.operacion;

  // Ordena una lista. `orden`: precio_asc | precio-desc | m2_desc | recamaras-desc ...
  AM.ordenar = function (lista, orden, fotoPrimero) {
    const [campo, dir] = String(orden || 'precio-asc').replace('_', '-').split('-');
    const s = dir === 'desc' ? -1 : 1;
    lista.sort((a, b) => ((a[campo] || 0) - (b[campo] || 0)) * s);
    if (campo === 'precio') { const mx = lista.filter(AM.esMXN), us = lista.filter(p => !AM.esMXN(p)); lista.length = 0; lista.push(...mx, ...us); }
    if (!fotoPrimero) return lista;
    const con = [], sin = [];
    lista.forEach(p => (p.foto ? con : sin).push(p));
    return con.concat(sin);
  };

  // ── Comparador (guardado en el navegador) ──────────────
  const KEY = 'aciertaComparar';
  const MAX = 10;
  AM.cmp = {
    max: MAX,
    get() {
      if (AM._memDirty) return AM._mem || [];
      try {
        const a = JSON.parse(localStorage.getItem(KEY) || '[]');
        return Array.isArray(a) ? a.slice(0, MAX) : [];
      } catch (e) { return AM._mem || []; }
    },
    set(arr) {
      AM._mem = arr;
      try { localStorage.setItem(KEY, JSON.stringify(arr)); AM._memDirty = false; }
      catch (e) { AM._memDirty = true; }
    },
    has(eb) { return this.get().includes(eb); },
    toggle(eb) {
      const a = this.get().slice(), i = a.indexOf(eb);
      if (i >= 0) { a.splice(i, 1); this.set(a); return { ok: true, on: false }; }
      if (a.length >= MAX) return { ok: false, motivo: 'max' };
      a.push(eb); this.set(a); return { ok: true, on: true };
    },
    clear() { this.set([]); },
  };

  AM.toast = function (msg) {
    let t = document.getElementById('amToast');
    if (!t) { t = document.createElement('div'); t.id = 'amToast'; document.body.appendChild(t); }
    t.textContent = msg;
    t.classList.add('show');
    clearTimeout(AM._tt);
    AM._tt = setTimeout(() => t.classList.remove('show'), 3200);
  };

  AM.actualizarUI = function () {
    const sel = AM.cmp.get();
    document.querySelectorAll('.btn-cmp').forEach(b => {
      const on = sel.includes(b.dataset.eb);
      b.classList.toggle('on', on);
      b.setAttribute('aria-pressed', on ? 'true' : 'false');
      b.textContent = on ? '✓ En comparación' : '＋ Comparar';
    });
    let bar = document.getElementById('cmpBar');
    if (!bar) {
      bar = document.createElement('div');
      bar.id = 'cmpBar';
      bar.innerHTML = '<span id="cmpTxt"></span><a id="cmpGo" class="cmp-go" href="comparar.html">Comparar ahora</a>' +
                      '<button id="cmpClear" type="button">Vaciar</button>';
      document.body.appendChild(bar);
      bar.querySelector('#cmpClear').addEventListener('click', () => { AM.cmp.clear(); AM.actualizarUI(); });
      bar.querySelector('#cmpGo').addEventListener('click', e => {
        if (AM.cmp.get().length < 2) { e.preventDefault(); AM.toast('Elige al menos 2 propiedades para compararlas.'); }
      });
    }
    const visible = sel.length > 0 && !AM.sinBarra;
    bar.style.display = visible ? 'flex' : 'none';
    document.body.classList.toggle('cmp-activo', visible);
    bar.querySelector('#cmpTxt').textContent = sel.length === 1
      ? '1 propiedad seleccionada — elige al menos una más'
      : sel.length + ' propiedades para comparar';
    bar.querySelector('#cmpGo').classList.toggle('deshabilitado', sel.length < 2);
  };

  document.addEventListener('click', e => {
    const b = e.target.closest && e.target.closest('.btn-cmp');
    if (!b) return;
    e.preventDefault();
    const r = AM.cmp.toggle(b.dataset.eb);
    if (!r.ok) AM.toast('Puedes comparar hasta ' + MAX + ' propiedades. Quita una para agregar otra.');
    AM.actualizarUI();
    document.dispatchEvent(new CustomEvent('am:cmp-change'));
  });
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', () => AM.actualizarUI());
  else AM.actualizarUI();

  // ── Tarjeta de propiedad ───────────────────────────────
  AM.cardHTML = function (p, opts) {
    opts = opts || {};
    const bits = [];
    if (p.recamaras) bits.push(p.recamaras + ' rec');
    if (p.banos) bits.push(p.banos + ' baños');
    if (p.m2) bits.push(Math.round(p.m2) + ' m²');
    const pm2 = AM.precioM2(p);
    if (pm2) bits.push(AM.money(pm2) + '/m²');
    const unidad = p.operacion === 'RENTA' ? '/mes' : '';
    const url = AM.fichaUrl(p);
    const wa = encodeURIComponent('Hola, me interesa esta propiedad: ' + p.titulo + ' (' + (p.eb || 'sin código') + ', ' + (p.operacion === 'RENTA' ? 'renta' : 'venta') + ') — ' +
      location.origin + '/' + url);
    const lugar = (p.colonia ? p.colonia + ', ' : '') + p.municipio;
    const loc = opts.compact
      ? (p.operacion === 'RENTA' ? 'Renta' : 'Venta') + ' · ' + p.tipo + ' · ' + lugar
      : '📍 ' + lugar;
    return `
  <div class="card" data-eb="${AM.esc(AM.clave(p))}">
    <a class="card-media" href="${url}" ${p.foto ? 'style="background:#0f1f3d"' : ''} aria-label="Ver ficha: ${AM.esc(p.titulo)}">
      ${AM.iconHouse()}${p.foto ? AM.fotoImg(p.foto, 720, 480, '', 'loading="lazy"') : ''}
      <span class="card-op">${AM.esc(p.operacion)}</span>
      <span class="card-tipo">${AM.esc(p.tipo)}</span>
    </a>
    <div class="card-body">
      <div class="card-price">${AM.precioTxt(p)}<span> ${AM.esMXN(p) ? 'MXN' : 'USD'}${unidad}</span></div>
      <a class="card-title" href="${url}">${AM.esc(p.titulo)}</a>
      <div class="card-loc">${AM.esc(loc)}</div>
      <div class="card-meta">${bits.map(b => `<span>${AM.esc(b)}</span>`).join('')}</div>
      <div class="card-cta">
        <a class="btn-outline" href="${url}">Ver ficha</a>
        <a class="btn-solid" href="https://wa.me/523333777337?text=${wa}" target="_blank" rel="noopener">WhatsApp</a>
      </div>
      <button class="btn-cmp" type="button" data-eb="${AM.esc(AM.clave(p))}" aria-pressed="false">＋ Comparar</button>
    </div>
  </div>`;
  };

  // ── Sellos de confianza (texto; el redactado exacto lo confirma Acierta Max) ──
  AM.confianzaHTML = function () {
    return '<div class="confianza"><div class="confianza-sellos">' +
      '<span>🏛️ Socio AMPI</span><span>📜 Cumple la NOM-247-SE-2021</span>' +
      '<span>🤝 Contratos conforme a PROFECO</span><span>🎓 Asesores certificados por la SEP</span></div>' +
      '<p>Herramientas a tu favor: comparativo de propiedades, análisis de precio por m², simulador de crédito y MAX, ' +
      'nuestro asistente con IA por WhatsApp — siempre con un asesor real a tu lado.</p></div>';
  };

  // ── Geometría compartida (mapa por zona, motor de inversión) ──
  AM.km = function (a, b) {
    const R_ = 6371, la1 = a.lat * Math.PI / 180, lo1 = a.lon * Math.PI / 180, la2 = b.lat * Math.PI / 180, lo2 = b.lon * Math.PI / 180;
    const h = Math.sin((la2 - la1) / 2) ** 2 + Math.cos(la1) * Math.cos(la2) * Math.sin((lo2 - lo1) / 2) ** 2;
    return 2 * R_ * Math.asin(Math.sqrt(h));
  };
  AM.puntoEnPoligono = function (lat, lon, poligono) {
    let dentro = false;
    for (let i = 0, j = poligono.length - 1; i < poligono.length; j = i++) {
      const xi = poligono[i].lat, yi = poligono[i].lng, xj = poligono[j].lat, yj = poligono[j].lng;
      const interseca = ((yi > lon) !== (yj > lon)) && (lat < (xj - xi) * (lon - yi) / (yj - yi) + xi);
      if (interseca) dentro = !dentro;
    }
    return dentro;
  };

  // ── Motor de inversión (mismos supuestos y método que herramientas/reporte_inversion.py) ──
  // Todo en JS para poder correr en el navegador del cliente, con SU zona dibujada y SUS filtros.
  AM.SUPUESTOS_INVERSION = { compra: 0.06, venta: 0.05, mantenimiento: 0.010, predial: 0.0015, vacancia: 1 / 12, inpc: 0.0376, cetes: 0.065, isr_marginal: 0.30, plusvalia_base: 0.0999, plusvalia_alta: 0.10 };
  // Fuente: SHF, Índice de Precios de la Vivienda, Zona Metropolitana de Guadalajara, 2T 2026 (9.99% anual, publicado por el IIEG de Jalisco).
  AM.SHF_FUENTE_URL = 'https://iieg.gob.mx/ns/?p=27454';
  AM.SHF_TRIMESTRE = '2T 2026';

  // ── Lugares de referencia para el bono de ubicación de la plusvalía ──
  // Lista CURADA (no exhaustiva) de centros comerciales, hospitales y
  // universidades conocidos de la ZMG, con coordenadas verificadas
  // (Google Places). No representa todos los lugares que existen -- es
  // una muestra razonable para orientar, no un análisis GIS completo.
  AM.LANDMARKS = {
    centros_comerciales: [
      { n: 'Andares', lat: 20.7101781, lon: -103.4127403 }, { n: 'Plaza del Sol', lat: 20.6505195, lon: -103.4013333 },
      { n: 'Galerías Guadalajara', lat: 20.6767971, lon: -103.4318360 }, { n: 'La Gran Plaza', lat: 20.6739898, lon: -103.4045833 },
      { n: 'Plaza Patria', lat: 20.7125399, lon: -103.3785850 }, { n: 'Forum Tlaquepaque', lat: 20.6482099, lon: -103.3214954 },
      { n: 'South Center (Periférico Sur)', lat: 20.6031288, lon: -103.4016469 }, { n: 'Plaza Tlaquepaque Río Nilo', lat: 20.6447851, lon: -103.3123162 },
    ],
    hospitales: [
      { n: 'Hospital San Javier', lat: 20.6879462, lon: -103.3896287 }, { n: 'Puerta de Hierro Medical Center', lat: 20.7086893, lon: -103.4144338 },
      { n: 'Hospital Country 2000', lat: 20.7036781, lon: -103.3646804 }, { n: 'Hospital Civil (Fray Antonio Alcalde)', lat: 20.6857262, lon: -103.3440966 },
      { n: 'Hospital Real San José', lat: 20.6728373, lon: -103.4095175 }, { n: 'Hospital Real San José Valle Real', lat: 20.7218921, lon: -103.4296447 },
    ],
    escuelas: [
      { n: 'ITESO', lat: 20.6083796, lon: -103.4146601 }, { n: 'CUCEI (UDG)', lat: 20.6548611, lon: -103.3254497 },
      { n: 'Universidad Panamericana', lat: 20.6826300, lon: -103.4419702 }, { n: 'Tec de Monterrey GDL', lat: 20.7343578, lon: -103.4543886 },
    ],
  };
  // Distancia (km) del punto al más cercano de una lista de lugares.
  AM.distMinKm = function (p, lista) { return Math.min(...lista.map(l => AM.km(p, { lat: l.lat, lon: l.lon }))); };
  // Bono de plusvalía por ubicación: +0.5 puntos si a <1.5 km de AL MENOS
  // uno de cada categoría (mall, hospital y escuela); +0.25 si a <4 km;
  // 0 si más lejos. Nunca resta -- no se castiga a zonas nuevas o alejadas
  // de estos puntos de referencia, solo se premia a las mejor ubicadas.
  AM.bonoUbicacion = function (p) {
    if (!p.lat || !p.lon) return 0;
    const bonoUno = d => d < 1.5 ? 0.005 : d < 4 ? 0.0025 : 0;
    return Object.values(AM.LANDMARKS).map(lista => bonoUno(AM.distMinKm(p, lista))).reduce((a, b) => a + b, 0);
  };
  // La plusvalía "base" de una propiedad concreta = la de la SHF para la
  // zona (S.plusvalia_base) + su bono de ubicación. No incluye antigüedad:
  // el inventario no trae año de construcción, así que ese ajuste no se aplica.
  AM.plusvaliaPropiedad = function (p, S) { S = S || AM.SUPUESTOS_INVERSION; return S.plusvalia_base + AM.bonoUbicacion(p); };
  AM.metodologiaPlusvaliaHTML = function () {
    return `<b>Cómo se calcula esta plusvalía:</b><br>
      Parte de la última estimación de la SHF para la Zona Metropolitana de Guadalajara (<b>${(AM.SUPUESTOS_INVERSION.plusvalia_base * 100).toFixed(2)}% anual, ${AM.esc(AM.SHF_TRIMESTRE)}</b>,
      <a href="${AM.SHF_FUENTE_URL}" target="_blank" rel="noopener">fuente</a>), y le suma un bono si la propiedad está cerca de centros comerciales,
      hospitales y escuelas conocidos de la ZMG (lista curada, no exhaustiva: hasta +0.5 puntos si está a menos de 1.5 km de cada uno, +0.25 si está a menos de 4 km).
      Las vías principales no se miden aparte: varios de estos centros y hospitales ya están sobre avenidas importantes (López Mateos, Vallarta, Periférico), así que la cercanía a ellos ya lo refleja en parte.<br><br>
      <b>No incluye antigüedad de la construcción</b> — el inventario no trae ese dato hoy; una propiedad muy nueva o muy antigua puede valer más o menos de lo que aquí se muestra.`;
  };
  AM.DESARROLLOS_PROPIOS = ['bella vittoria']; // los que Acierta Max comercializa directamente
  const _med = arr => { if (!arr.length) return null; const v = arr.slice().sort((a, b) => a - b), n = v.length; return n % 2 ? v[(n - 1) / 2] : (v[n / 2 - 1] + v[n / 2]) / 2; };
  function _tir(flujos) {
    let lo = -0.9, hi = 1.0;
    for (let i = 0; i < 200; i++) { const m = (lo + hi) / 2, v = flujos.reduce((s, f, t) => s + f / Math.pow(1 + m, t), 0); if (v > 0) lo = m; else hi = m; }
    return lo;
  }
  AM.pmt = function (monto, tasaAnual, anios) {
    const n = anios * 12, r = tasaAnual / 100 / 12;
    return r > 0 ? monto * r * Math.pow(1 + r, n) / (Math.pow(1 + r, n) - 1) : monto / n;
  };
  AM.saldoCredito = function (monto, tasaAnual, anios, mesesPagados) {
    const n = anios * 12, r = tasaAnual / 100 / 12, pago = AM.pmt(monto, tasaAnual, anios);
    return r > 0 ? monto * Math.pow(1 + r, mesesPagados) - pago * (Math.pow(1 + r, mesesPagados) - 1) / r : monto - pago * mesesPagados;
  };
  AM.interesAnioCredito = function (L, tasaAnual, plazoAnios, anio) {
    const pagoAnual = AM.pmt(L, tasaAnual, plazoAnios) * 12;
    const saldoIni = anio === 1 ? L : AM.saldoCredito(L, tasaAnual, plazoAnios, (anio - 1) * 12);
    const saldoFin = AM.saldoCredito(L, tasaAnual, plazoAnios, anio * 12);
    return pagoAnual - (saldoIni - saldoFin);
  };
  // El contribuyente elige, cada año, la deducción que más le convenga: la "ciega" (35% de lo
  // cobrado, sin comprobantes, más el predial) o la real (predial + mantenimiento + intereses
  // reales del crédito, si lo hay). Simplificación: no incluye depreciación ni otros gastos.
  AM.isrRentaAnual = function (cobrada, predial, mantenimiento, interesPagado, S) {
    const ciega = 0.35 * cobrada + predial;
    const real = predial + mantenimiento + (interesPagado || 0);
    const base = Math.max(cobrada - Math.max(ciega, real), 0);
    return { isr: S.isr_marginal * base, deduccionUsada: real > ciega ? 'real' : 'ciega' };
  };
  AM.flujosPropiedad = function (P, rentaAnual, g, n, S, credito) {
    const L = credito ? P * (credito.pct / 100) : 0;
    const aporte = P - L + P * S.compra, pagoMensual = L > 0 ? AM.pmt(L, credito.tasa, credito.plazo) : 0;
    const fl = [-aporte];
    for (let a = 1; a <= n; a++) {
      const val = P * Math.pow(1 + g, a - 1), cobrada = rentaAnual * Math.pow(1 + S.inpc, a - 1) * (1 - S.vacancia);
      const interesA = L > 0 ? AM.interesAnioCredito(L, credito.tasa, credito.plazo, a) : 0;
      const { isr } = AM.isrRentaAnual(cobrada, val * S.predial, val * S.mantenimiento, interesA, S);
      let r = cobrada - val * (S.mantenimiento + S.predial) - isr - pagoMensual * 12;
      if (a === n) r += P * Math.pow(1 + g, n) * (1 - S.venta) - (L > 0 ? AM.saldoCredito(L, credito.tasa, credito.plazo, n * 12) : 0);
      fl.push(r);
    }
    return fl;
  };
  AM.tirPropiedad = function (P, rentaAnual, g, n, S, credito) {
    S = S || AM.SUPUESTOS_INVERSION;
    return _tir(AM.flujosPropiedad(P, rentaAnual, g, n, S, credito));
  };
  AM.plusvaliaEquilibrio = function (P, rentaAnual, n, S, credito) {
    S = S || AM.SUPUESTOS_INVERSION; let lo = -0.05, hi = 0.30;
    for (let i = 0; i < 60; i++) { const m = (lo + hi) / 2; if (AM.tirPropiedad(P, rentaAnual, m, n, S, credito) < S.cetes) lo = m; else hi = m; }
    return lo;
  };
  AM.rendimientoNeto = function (P, rentaAnual, S) {
    S = S || AM.SUPUESTOS_INVERSION;
    const cobrada = rentaAnual * (1 - S.vacancia), pred = P * S.predial, mant = P * S.mantenimiento;
    const brutoAntes = cobrada / P - (S.mantenimiento + S.predial);
    const { isr } = AM.isrRentaAnual(cobrada, pred, mant, 0, S);
    const netoDespuesIsr = (cobrada - mant - pred - isr) / P;
    return { bruto: rentaAnual / P, neto: brutoAntes, netoDespuesIsr };
  };
  AM.cetesNeto = function (S) { S = S || AM.SUPUESTOS_INVERSION; return S.cetes - S.isr_marginal * Math.max(S.cetes - S.inpc, 0); };

  // Compara el PATRIMONIO TOTAL a n años entre tres caminos, partiendo del mismo capital
  // (lo que costaría comprar de contado): (1) dejarlo todo en CETES, (2) comprar de contado,
  // (3) comprar con crédito y dejar el resto del capital trabajando en CETES.
  // Los flujos de la propiedad que sobran (o faltan) cada año se reinvierten (o se financian)
  // al mismo CETES neto, para que la comparación sea consistente en toda la línea de tiempo.
  AM.compararEstrategias = function (P, rentaAnual, n, S, enganchePct, tasaHipoteca, plazo, plusvaliaUsada) {
    S = S || AM.SUPUESTOS_INVERSION;
    const g = plusvaliaUsada != null ? plusvaliaUsada : S.plusvalia_base;
    const cetesN = AM.cetesNeto(S), capitalTotal = P * (1 + S.compra);
    const acumular = flujos => { let acc = 0; for (let a = 1; a < flujos.length - 1; a++) acc = acc * (1 + cetesN) + flujos[a]; return acc * (1 + cetesN) + flujos[flujos.length - 1]; };
    const soloCetes = capitalTotal * Math.pow(1 + cetesN, n);
    const flContado = AM.flujosPropiedad(P, rentaAnual, g, n, S, null);
    const contado = acumular(flContado);
    const credito = { pct: 100 - enganchePct, tasa: tasaHipoteca, plazo: plazo || 20 };
    const flCredito = AM.flujosPropiedad(P, rentaAnual, g, n, S, credito);
    const aporteCredito = -flCredito[0], sobrante = capitalTotal - aporteCredito;
    const conCredito = acumular(flCredito) + sobrante * Math.pow(1 + cetesN, n);
    return { capitalTotal, soloCetes, contado, conCredito, sobrante, cetesNeto: cetesN, plusvaliaUsada: g,
      mensualCredito: AM.pmt(P * credito.pct / 100, tasaHipoteca, credito.plazo) };
  };

  // Genera el estudio: TODAS = inventario completo; opts = { poligono, tope, tipo, recMin, horizonte, banderas:{pagaSola,palancaAyuda}, tasaHipoteca, S }
  AM.motorInversion = function (TODAS, opts) {
    const S = Object.assign({}, AM.SUPUESTOS_INVERSION, opts.S || {});
    const tipos = AM.GRUPOS_TIPO[opts.tipo] || [opts.tipo];
    const ok = p => p.moneda === undefined || p.moneda === null || p.moneda === 'MXN';
    const enZona = p => p.lat && p.lon && AM.puntoEnPoligono(p.lat, p.lon, opts.poligono);
    const base = TODAS.filter(p => ok(p) && p.m2 >= 25 && p.m2 <= 600 && p.precio > 0 && enZona(p) && tipos.includes(p.tipo));
    const V = base.filter(p => p.operacion === 'VENTA'), R = base.filter(p => p.operacion === 'RENTA');
    let cand = V.filter(p => p.precio <= opts.tope);
    if (opts.recMin) cand = cand.filter(p => p.recamaras && p.recamaras >= opts.recMin);

    function rentEst(p) {
      for (const radio of [1.0, 1.5, 2.0]) {
        const c = R.filter(r => AM.km(p, r) <= radio && (!opts.recMin && !p.recamaras || (r.recamaras && Math.abs(r.recamaras - (p.recamaras || 0)) <= 1)) && r.m2 >= 0.65 * p.m2 && r.m2 <= 1.35 * p.m2);
        let v = c.map(r => r.precio / r.m2).sort((a, b) => a - b);
        if (v.length >= 5) { if (v.length >= 10) v = v.slice(Math.floor(v.length * .1), Math.floor(v.length * .9) + 1); return { renta: _med(v) * p.m2, n: c.length, radio }; }
      }
      return null;
    }
    function ventaMed(p) {
      for (const radio of [1.0, 1.5, 2.0]) {
        const c = V.filter(v => v !== p && AM.km(p, v) <= radio && (!p.recamaras || (v.recamaras && Math.abs(v.recamaras - p.recamaras) <= 1)));
        if (c.length >= 8) return { pm2: _med(c.map(v => v.precio / v.m2)), n: c.length };
      }
      return null;
    }
    const esPreventa = p => /preventa|pre-venta|preconstrucci/i.test(p.titulo || '');
    const esPropio = p => AM.DESARROLLOS_PROPIOS.some(d => AM.norm(p.titulo).includes(d) || AM.norm(p.liga).includes(d.replace(/ /g, '-')));

    const filas = [];
    for (const p of cand) {
      const re = rentEst(p), vm = ventaMed(p); if (!re || !vm) continue;
      const ra = re.renta * 12, bruto = ra / p.precio;
      if (bruto > 0.12 || bruto < 0.02) continue;
      const rend = AM.rendimientoNeto(p.precio, ra, S);
      filas.push({ p, ra, nr: re.n, radio: re.radio, nv: vm.n, desc: 1 - (p.precio / p.m2) / vm.pm2, bruto, neto: rend.neto, netoDespuesIsr: rend.netoDespuesIsr, preventa: esPreventa(p), propio: esPropio(p) });
    }
    function rank(vals) { const o = vals.map((v, i) => i).sort((a, b) => vals[a] - vals[b]), r = new Array(vals.length); o.forEach((idx, k) => r[idx] = vals.length > 1 ? k / (vals.length - 1) : 0); return r; }
    const evaluables = filas.filter(x => !x.preventa);
    const rn = rank(evaluables.map(x => x.neto)), rd = rank(evaluables.map(x => x.desc));
    evaluables.forEach((x, i) => { const conf = Math.min(x.nr / 8, 1) * (x.radio === 1.0 ? 1.0 : x.radio === 1.5 ? 0.8 : 0.6); x.score = 0.5 * rn[i] + 0.3 * rd[i] + 0.2 * conf; x.confianza = conf >= 0.75 ? 'alta' : conf >= 0.4 ? 'media' : 'baja'; });
    evaluables.sort((a, b) => b.score - a.score || a.p.eb.localeCompare(b.p.eb));
    const preventas = filas.filter(x => x.preventa).sort((a, b) => a.p.precio - b.p.precio);

    const enganchePct = (opts.enganchePct != null) ? opts.enganchePct : 30;
    const credito = (opts.banderas.pagaSola || opts.banderas.palancaAyuda) ? { pct: 100 - enganchePct, tasa: opts.tasaHipoteca || 11, plazo: 20, enganchePct } : null;
    function empacar(x, rank) {
      const p = x.p, n = opts.horizonte || 4;
      const plusvaliaProp = AM.plusvaliaPropiedad(p, S);
      const out = { rank, eb: p.eb, titulo: p.titulo, colonia: p.colonia, municipio: p.municipio, m2: p.m2, rec: p.recamaras, precio: p.precio,
        pm2: Math.round(p.precio / p.m2), lat: p.lat, lon: p.lon, foto: p.foto, liga: p.liga, renta: Math.round(x.ra / 12), renta_anual: Math.round(x.ra),
        bruto: x.bruto, neto: x.neto, netoDespuesIsr: x.netoDespuesIsr, desc: x.desc, n_venta: x.nv, n_renta: x.nr, confianza: x.confianza || 'media', propio: x.propio, preventa: x.preventa,
        plusvaliaUsada: plusvaliaProp, bonoUbicacion: plusvaliaProp - S.plusvalia_base,
        geq: AM.plusvaliaEquilibrio(p.precio, x.ra, n, S, null), tir: {} };
      [['inflacion', S.inpc], ['base', plusvaliaProp], ['alta', S.plusvalia_alta]].forEach(([k, g]) => out.tir[k] = AM.tirPropiedad(p.precio, x.ra, g, n, S, null));
      if (credito) {
        const mensual = AM.pmt(p.precio * credito.pct / 100, credito.tasa, credito.plazo), noiMensual = (x.ra * (1 - S.vacancia) - p.precio * (S.mantenimiento + S.predial)) / 12;
        const cmp = AM.compararEstrategias(p.precio, x.ra, n, S, enganchePct, credito.tasa, credito.plazo, plusvaliaProp);
        out.credito = { mensual, noiMensual, sePagaSola: noiMensual >= mensual, enganchePct, patrimonio: cmp, palancaAyuda: cmp.conCredito > cmp.contado, geqConCredito: AM.plusvaliaEquilibrio(p.precio, x.ra, n, S, credito) };
      }
      return out;
    }
    let top = evaluables;
    return {
      inventario: { total: TODAS.length, en_zona_venta: V.length, candidatos: cand.length, evaluados: evaluables.length, sin_comparables: cand.length - filas.length, rentas_comparables: R.length, preventas: preventas.length },
      mercado: { cetes: S.cetes, cetes_neto: AM.cetesNeto(S), inflacion: S.inpc, isr_marginal: S.isr_marginal },
      supuestos: S, credito,
      opciones: top.slice(0, 10).map((x, i) => empacar(x, i + 1)),
      preventas: preventas.slice(0, 6).map((x, i) => empacar(x, i + 1)),
    };
  };

  // ── Compartir una ficha (WhatsApp a un tercero / correo) ──────
  AM.compartirHTML = function (titulo, url) {
    const id = 'sh' + Math.random().toString(36).slice(2, 8);
    const texto = `Mira esta propiedad que encontré en Acierta Max: ${titulo} — ${url}`;
    return `<div class="compartir" id="${id}">
      <button type="button" class="btn-compartir" data-compartir="${id}">📤 Compartir esta ficha</button>
      <div class="compartir-ops" id="${id}-ops" style="display:none">
        <a target="_blank" rel="noopener" href="https://wa.me/?text=${encodeURIComponent(texto)}">Por WhatsApp</a>
        <a href="mailto:?subject=${encodeURIComponent('Propiedad: ' + titulo)}&body=${encodeURIComponent(texto)}">Por correo</a>
        <button type="button" data-copiar-liga="${AM.esc(url)}">Copiar enlace</button>
      </div></div>`;
  };
  document.addEventListener('click', e => {
    const b = e.target.closest('[data-compartir]');
    if (b) {
      const ops = document.getElementById(b.dataset.compartir + '-ops'); if (!ops) return;
      if (navigator.share) { navigator.share({ title: 'Acierta Max', text: b.closest('.compartir').dataset.texto || '', url: location.href }).catch(() => {}); }
      else ops.style.display = ops.style.display === 'none' ? 'flex' : 'none';
      return;
    }
    const c = e.target.closest('[data-copiar-liga]');
    if (c) {
      const url = c.dataset.copiarLiga, listo = () => AM.toast('Enlace copiado.');
      if (navigator.clipboard && navigator.clipboard.writeText) navigator.clipboard.writeText(url).then(listo, () => prompt('Copia este enlace:', url));
      else prompt('Copia este enlace:', url);
    }
  });

  // ── Captura de contacto reutilizable (agendar visita, pedir info) ──
  // Un solo lead por navegador para TODO el sitio (compra, renta, inversión…):
  // una vez registrado, no se le vuelve a pedir nombre y WhatsApp cada vez.
  const CLAVE_LEAD = 'aciertaLead';
  AM.leadGuardado = function () { try { return JSON.parse(localStorage.getItem(CLAVE_LEAD) || 'null'); } catch (e) { return null; } };
  function guardarLead(l) { try { localStorage.setItem(CLAVE_LEAD, JSON.stringify(l)); } catch (e) {} }
  let _caminoCfg = null;
  function caminoCfg() { return _caminoCfg || (_caminoCfg = fetch('camino-datos.json').then(r => r.json())); }

  function modalContactoHTML(motivo, coaches) {
    return `<div class="am-modal-fondo" id="amModalFondo"><div class="am-modal">
      <button type="button" class="am-modal-cerrar" id="amModalCerrar" aria-label="Cerrar">✕</button>
      <h3>Un momento antes de continuar</h3>
      <p class="muted">${AM.esc(motivo || 'Para que un asesor de Acierta Max te dé seguimiento, compártenos tus datos.')}</p>
      <label>Tu nombre</label><input type="text" id="amNombre" maxlength="80">
      <label>Tu WhatsApp (10 dígitos)</label><input type="tel" id="amWa" inputmode="numeric" maxlength="20">
      <div id="amVerifWA"></div>
      <label for="amCoach">¿Ya conoces a un coach de Acierta Max? <span class="muted">(opcional)</span></label>
      <select id="amCoach"><option value="">No, que me asignen uno</option>${(coaches || []).map(n => `<option>${AM.esc(n)}</option>`).join('')}</select>
      <label class="am-consent"><input type="checkbox" id="amConsent"> <span>Acepto que Acierta Max guarde mis datos y me contacte por WhatsApp, conforme al <a href="aviso-privacidad.html" target="_blank" rel="noopener">Aviso de privacidad</a>.</span></label>
      <div class="am-modal-error" id="amModalError" style="display:none"></div>
      <button type="button" class="btn-solid" id="amModalEnviar" style="width:100%;padding:12px;border:0;border-radius:999px;font-weight:800;cursor:pointer">Continuar</button>
      <button type="button" class="am-modal-saltar" id="amModalSaltar">Continuar sin registrar mis datos</button>
    </div></div>`;
  }
  const telOk = t => { let d = String(t || '').replace(/\D/g, ''); if (d.startsWith('521') && d.length === 13) d = d.slice(3); else if (d.startsWith('52') && d.length === 12) d = d.slice(2); return d.length === 10; };

  // opts: { motivo, operacion, tipo, municipio, presupuesto, notas } -> Promise<lead|null>
  AM.asegurarLead = function (opts) {
    opts = opts || {};
    const existente = AM.leadGuardado();
    if (existente && existente.folio) return Promise.resolve(existente);
    return caminoCfg().then(cfg => new Promise(resolve => {
      const host = document.createElement('div'); host.innerHTML = modalContactoHTML(opts.motivo, cfg.coaches); document.body.appendChild(host);
      let verificado = false, verifTelDe = '', estado = '', codigo = '', liga = '', timer = null, desde = 0, revisando = false;
      const $ = id => document.getElementById(id);
      const parar = () => { if (timer) { clearInterval(timer); timer = null; } };
      const cerrar = lead => { parar(); document.removeEventListener('visibilitychange', alVolver); window.removeEventListener('focus', alVolver); host.remove(); resolve(lead); };

      // Verificación invertida (4-oct-2026): el cliente nos manda "Mi código
      // Acierta es 1234" desde su WhatsApp y la ventana avanza sola.
      function verifHTML() {
        const wa = $('amWa').value.trim();
        if (!telOk(wa)) return '';
        if (verificado && verifTelDe === wa) return '<div class="cam-verif-ok">✅ WhatsApp verificado</div>';
        if (estado === 'preparando') return '<div class="cam-verif-txt">Preparando…</div>';
        if (estado === 'esperando') {
          return `<div class="cam-verif"><p class="cam-verif-txt">Toca <strong>Abrir WhatsApp</strong> y envía el mensaje que ya viene escrito (código <strong>${AM.esc(codigo)}</strong>), sin cambiarlo. Esta ventana avanza sola cuando lo recibamos.</p>
            <a class="btn-sec cam-verif-wa" id="amLnkAbrirWA" href="${AM.esc(liga)}" target="_blank" rel="noopener">Abrir WhatsApp</a>
            <p class="cam-verif-txt muted">Esperando tu mensaje…</p>
            ${errorVerif ? `<p class="cam-verif-error">${AM.esc(errorVerif)}</p>` : ''}
            <button type="button" class="cam-verif-reenviar" id="amBtnReenviarWA">Generar el mensaje otra vez</button></div>`;
        }
        return `<button type="button" class="btn-sec" id="amBtnEnviarWA">Verificar por WhatsApp</button>${errorVerif ? `<p class="cam-verif-error">${AM.esc(errorVerif)}</p>` : ''}`;
      }
      let errorVerif = '';
      const pintarVerif = () => { const el = $('amVerifWA'); if (el) el.innerHTML = verifHTML(); };
      async function llamar(ruta, cuerpo) {
        try {
          const cfg = await caminoCfg();
          const r = await fetch(cfg.endpoint + ruta, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(cuerpo) });
          const j = await r.json().catch(() => ({}));
          return { ok: r.ok && j.ok, j };
        } catch (e) { return { ok: false, j: { error: 'No pudimos conectar. Revisa tu internet.' } }; }
      }
      async function revisar() {
        if (estado !== 'esperando' || revisando) return;
        if (Date.now() - desde > 15 * 60 * 1000) { parar(); estado = ''; errorVerif = 'El código venció. Vuelve a verificar.'; pintarVerif(); return; }
        revisando = true;
        const wa = $('amWa').value.trim();
        const r = await llamar('/verificar/estado', { whatsapp: wa });
        revisando = false;
        if (r.ok && r.j.verificado && estado === 'esperando' && wa === $('amWa').value.trim()) {
          parar(); verificado = true; verifTelDe = wa; estado = ''; errorVerif = ''; pintarVerif();
        }
      }
      function alVolver() { if (!document.hidden) revisar(); }
      document.addEventListener('visibilitychange', alVolver);
      window.addEventListener('focus', alVolver);
      async function enviarCodigo() {
        parar(); estado = 'preparando'; errorVerif = ''; pintarVerif();
        const wa = $('amWa').value.trim();
        const r = await llamar('/verificar/iniciar', { whatsapp: wa });
        if (r.ok && r.j.verificado) { verificado = true; verifTelDe = wa; estado = ''; }
        else if (r.ok && r.j.liga) { estado = 'esperando'; codigo = r.j.codigo || ''; liga = r.j.liga; desde = Date.now(); timer = setInterval(revisar, 3000); }
        else { estado = ''; errorVerif = (r.j && r.j.error) || 'No pudimos preparar la verificación. Intenta de nuevo.'; }
        pintarVerif();
      }
      $('amWa').addEventListener('input', () => { if ($('amWa').value.trim() !== verifTelDe) { verificado = false; parar(); estado = ''; errorVerif = ''; } pintarVerif(); });
      host.addEventListener('click', e => {
        const b = e.target.closest('button'); if (!b) return;
        if (b.id === 'amBtnEnviarWA' || b.id === 'amBtnReenviarWA') enviarCodigo();
      });

      document.getElementById('amModalCerrar').addEventListener('click', () => cerrar(null));
      document.getElementById('amModalSaltar').addEventListener('click', () => cerrar(null));
      document.getElementById('amModalFondo').addEventListener('click', e => { if (e.target.id === 'amModalFondo') cerrar(null); });
      document.getElementById('amModalEnviar').addEventListener('click', async () => {
        const nombre = document.getElementById('amNombre').value.trim(), wa = document.getElementById('amWa').value.trim();
        const err = document.getElementById('amModalError'), btn = document.getElementById('amModalEnviar');
        const consent = document.getElementById('amConsent').checked;
        if (nombre.length < 2) { err.textContent = 'Escribe tu nombre.'; err.style.display = 'block'; return; }
        if (!telOk(wa)) { err.textContent = 'Escribe tu WhatsApp a 10 dígitos.'; err.style.display = 'block'; return; }
        if (!verificado || verifTelDe !== wa) { err.textContent = 'Primero verifica tu WhatsApp con el botón «Verificar por WhatsApp».'; err.style.display = 'block'; return; }
        if (!consent) { err.textContent = 'Necesitamos tu consentimiento para guardar tus datos y contactarte.'; err.style.display = 'block'; return; }
        err.style.display = 'none'; btn.disabled = true; btn.textContent = 'Guardando…';
        try {
          const cfg = await caminoCfg();
          const r = await fetch(cfg.endpoint, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({
            nombre, whatsapp: wa, email: '', consentimiento: true, aviso_version: cfg.avisoVersion,
            operacion: opts.operacion || 'compra', tipo: opts.tipo || 'nose', uso: opts.uso || '', cuando: opts.cuando || '',
            municipio: opts.municipio || 'cualquiera', colonia: opts.notas || '', coach_conocido: document.getElementById('amCoach').value }) });
          const j = await r.json().catch(() => ({}));
          if (r.ok && j.ok) { const lead = { folio: j.folio, vendedor: j.vendedor, token: j.token, nombre, whatsapp: wa }; guardarLead(lead); cerrar(lead); return; }
          err.textContent = (j && j.error) || 'No pudimos guardar tus datos.'; err.style.display = 'block'; btn.disabled = false; btn.textContent = 'Continuar';
        } catch (e) { err.textContent = 'No pudimos conectar. Revisa tu internet.'; err.style.display = 'block'; btn.disabled = false; btn.textContent = 'Continuar'; }
      });
    }));
  };

  // ── Análisis de precio por m² ──────────────────────────
  const MIN_MUESTRA = 8;
  function percentil(orden, q) {
    const pos = (orden.length - 1) * q, lo = Math.floor(pos), hi = Math.ceil(pos);
    return orden[lo] + (orden[hi] - orden[lo]) * (pos - lo);
  }

  // Compara el precio por m² de `p` contra propiedades comparables del inventario:
  // misma operación (venta/renta), mismo grupo de tipo y, en casas/deptos, ±1 recámara.
  // Usa la colonia si hay al menos MIN_MUESTRA comparables; si no, el municipio.
  AM.analisis = function (p, all) {
    if (!AM.esMXN(p)) return { disponible: false, motivo: 'El precio de esta propiedad está en dólares; el análisis por m² compara solo propiedades en pesos.' };
    const pm2 = AM.precioM2(p);
    if (!pm2) return { disponible: false, motivo: 'Esta propiedad no tiene m² o precio registrados, por eso no se puede calcular su precio por m².' };
    const g = AM.grupoDe(p.tipo);
    const usaRec = (g === 'casa' || g === 'departamento') && p.recamaras > 0;
    const base = all.filter(q => q !== p && q.operacion === p.operacion &&
      AM.grupoDe(q.tipo) === g && AM.precioM2(q) &&
      (!usaRec || (q.recamaras > 0 && Math.abs(q.recamaras - p.recamaras) <= 1)));
    const niveles = [];
    if (p.colonia) niveles.push({ alcance: 'colonia', nombre: p.colonia, f: q => AM.norm(q.colonia) === AM.norm(p.colonia) });
    niveles.push({ alcance: 'municipio', nombre: p.municipio, f: q => q.municipio === p.municipio });

    for (const nv of niveles) {
      const comps = base.filter(nv.f);
      if (comps.length < MIN_MUESTRA) continue;
      const vals = comps.map(AM.precioM2).sort((a, b) => a - b);
      const mediana = percentil(vals, 0.5);
      const diff = pm2 / mediana - 1;
      const bajoElPropio = vals.filter(v => v < pm2).length;
      const desc = AM.GRUPO_LABEL[g] +
        (usaRec ? ' de ' + Math.max(1, p.recamaras - 1) + ' a ' + (p.recamaras + 1) + ' recámaras' : '') +
        ' en ' + (p.operacion === 'RENTA' ? 'renta' : 'venta') + ' en ' +
        (nv.alcance === 'colonia' ? 'la colonia ' + nv.nombre : nv.nombre);
      return {
        disponible: true, pm2, n: comps.length, alcance: nv.alcance, nombre: nv.nombre, descripcion: desc,
        mediana, p10: percentil(vals, 0.10), p25: percentil(vals, 0.25), p75: percentil(vals, 0.75), p90: percentil(vals, 0.90),
        min: vals[0], max: vals[vals.length - 1],
        diffPct: diff, percentil: bajoElPropio / vals.length,
        veredicto: diff <= -0.15 ? 'bajo' : diff >= 0.15 ? 'alto' : 'linea',
        atipico: pm2 > mediana * 3 || pm2 < mediana / 3,
      };
    }
    return { disponible: false, motivo: 'Todavía no hay suficientes propiedades comparables (mínimo ' + MIN_MUESTRA + ') para dar una referencia confiable.' };
  };

  AM.veredictoTexto = function (an) {
    const pct = Math.round(Math.abs(an.diffPct) * 100);
    if (an.veredicto === 'bajo') return 'por debajo de la mediana (' + pct + '%)';
    if (an.veredicto === 'alto') return 'por encima de la mediana (' + pct + '%)';
    return 'en línea con la mediana (' + (an.diffPct >= 0 ? '+' : '−') + pct + '%)';
  };

  AM.AVISO_ANALISIS = 'Es una referencia orientativa: se basa en precios de lista (no de cierre) del inventario que manejamos. ' +
    'Un precio por m² más bajo puede deberse a antigüedad, estado o acabados, y uno más alto a lo contrario; ' +
    'lo mejor es verificarlo en persona.';

  AM.similares = function (p, all, n) {
    n = n || 4;
    if (!AM.esMXN(p)) return [];
    const g = AM.grupoDe(p.tipo);
    let c = all.filter(q => q !== p && q.operacion === p.operacion && AM.grupoDe(q.tipo) === g && q.municipio === p.municipio && AM.esMXN(q));
    const cerca = c.filter(q => Math.abs(q.precio - p.precio) <= p.precio * 0.3);
    if (cerca.length >= n) c = cerca;
    const misma = q => (AM.norm(q.colonia) === AM.norm(p.colonia) ? 0 : 1);
    c.sort((a, b) => (misma(a) - misma(b)) || ((a.foto ? 0 : 1) - (b.foto ? 0 : 1)) ||
      (Math.abs(a.precio - p.precio) - Math.abs(b.precio - p.precio)));
    return c.slice(0, n);
  };
})();

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
  const MAX = 4;
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
      ${AM.iconHouse()}${p.foto ? `<img src="${AM.esc(p.foto)}" alt="" loading="lazy" onerror="this.remove()">` : ''}
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
  AM.SUPUESTOS_INVERSION = { compra: 0.06, venta: 0.05, mantenimiento: 0.010, predial: 0.0015, vacancia: 1 / 12, inpc: 0.0376, cetes: 0.065, isr_marginal: 0.30 };
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
  AM.tirPropiedad = function (P, rentaAnual, g, n, S, credito) {
    S = S || AM.SUPUESTOS_INVERSION;
    const L = credito ? P * (credito.pct / 100) : 0, aporte = P - L + P * S.compra, pagoMensual = L > 0 ? AM.pmt(L, credito.tasa, credito.plazo) : 0;
    const fl = [-aporte];
    for (let a = 1; a <= n; a++) {
      const val = P * Math.pow(1 + g, a - 1);
      let r = rentaAnual * Math.pow(1 + S.inpc, a - 1) * (1 - S.vacancia) - val * (S.mantenimiento + S.predial) - pagoMensual * 12;
      if (a === n) r += P * Math.pow(1 + g, n) * (1 - S.venta) - (L > 0 ? AM.saldoCredito(L, credito.tasa, credito.plazo, n * 12) : 0);
      fl.push(r);
    }
    return _tir(fl);
  };
  AM.plusvaliaEquilibrio = function (P, rentaAnual, n, S) {
    S = S || AM.SUPUESTOS_INVERSION; let lo = -0.05, hi = 0.30;
    for (let i = 0; i < 60; i++) { const m = (lo + hi) / 2; if (AM.tirPropiedad(P, rentaAnual, m, n, S) < S.cetes) lo = m; else hi = m; }
    return lo;
  };
  AM.rendimientoNeto = function (P, rentaAnual, S) {
    S = S || AM.SUPUESTOS_INVERSION;
    const cobrada = rentaAnual * (1 - S.vacancia), pred = P * S.predial;
    const brutoAntes = (cobrada) / P - (S.mantenimiento + S.predial);
    const isrRenta = S.isr_marginal * Math.max(0.65 * cobrada - pred, 0);
    const netoDespuesIsr = (cobrada - P * S.mantenimiento - pred - isrRenta) / P;
    return { bruto: (rentaAnual / P), neto: brutoAntes, netoDespuesIsr };
  };
  AM.cetesNeto = function (S) { S = S || AM.SUPUESTOS_INVERSION; return S.cetes - S.isr_marginal * Math.max(S.cetes - S.inpc, 0); };

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

    const credito = (opts.banderas.pagaSola || opts.banderas.palancaAyuda) ? { pct: 50, tasa: opts.tasaHipoteca || 11, plazo: 20 } : null;
    function empacar(x, rank) {
      const p = x.p, n = opts.horizonte || 4;
      const out = { rank, eb: p.eb, titulo: p.titulo, colonia: p.colonia, municipio: p.municipio, m2: p.m2, rec: p.recamaras, precio: p.precio,
        pm2: Math.round(p.precio / p.m2), lat: p.lat, lon: p.lon, foto: p.foto, liga: p.liga, renta: Math.round(x.ra / 12), renta_anual: Math.round(x.ra),
        bruto: x.bruto, neto: x.neto, netoDespuesIsr: x.netoDespuesIsr, desc: x.desc, n_venta: x.nv, n_renta: x.nr, confianza: x.confianza || 'media', propio: x.propio, preventa: x.preventa,
        geq: AM.plusvaliaEquilibrio(p.precio, x.ra, n, S), tir: {} };
      [['inflacion', S.inpc], ['base', 0.06], ['alta', 0.10]].forEach(([k, g]) => out.tir[k] = AM.tirPropiedad(p.precio, x.ra, g, n, S));
      if (credito) {
        const mensual = AM.pmt(p.precio * credito.pct / 100, credito.tasa, credito.plazo), noiMensual = (x.ra * (1 - S.vacancia) - p.precio * (S.mantenimiento + S.predial)) / 12;
        const tirCon = AM.tirPropiedad(p.precio, x.ra, 0.06, n, S, credito);
        out.credito = { mensual, noiMensual, sePagaSola: noiMensual >= mensual, tirConCredito: tirCon, palancaAyuda: tirCon > out.tir.base };
      }
      return out;
    }
    let top = evaluables;
    if (opts.banderas.pagaSola || opts.banderas.palancaAyuda) {
      top = evaluables.filter(x => {
        const p = x.p, n = opts.horizonte || 4, mensual = AM.pmt(p.precio * credito.pct / 100, credito.tasa, credito.plazo), noiMensual = (x.ra * (1 - S.vacancia) - p.precio * (S.mantenimiento + S.predial)) / 12;
        const sePagaSola = noiMensual >= mensual, tirCon = AM.tirPropiedad(p.precio, x.ra, 0.06, n, S, credito), tirSin = AM.tirPropiedad(p.precio, x.ra, 0.06, n, S, null);
        const palancaAyuda = tirCon > tirSin;
        return (opts.banderas.pagaSola && sePagaSola) || (opts.banderas.palancaAyuda && palancaAyuda);
      });
    }
    return {
      inventario: { total: TODAS.length, en_zona_venta: V.length, candidatos: cand.length, evaluados: evaluables.length, sin_comparables: cand.length - filas.length, rentas_comparables: R.length, preventas: preventas.length },
      mercado: { cetes: S.cetes, cetes_neto: AM.cetesNeto(S), inflacion: S.inpc, isr_marginal: S.isr_marginal },
      supuestos: S, credito,
      opciones: top.slice(0, 10).map((x, i) => empacar(x, i + 1)),
      preventas: preventas.slice(0, 6).map((x, i) => empacar(x, i + 1)),
    };
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

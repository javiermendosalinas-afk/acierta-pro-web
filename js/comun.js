/* Acierta Max — utilidades compartidas: tarjetas, comparador y análisis de precio */
(function () {
  const AM = (window.AM = {});

  // ── Básicos ────────────────────────────────────────────
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
  AM.precioM2 = p => (p.m2 > 0 && p.precio > 0) ? p.precio / p.m2 : null;
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
      <div class="card-price">${AM.money(p.precio)}<span> MXN${unidad}</span></div>
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
    const g = AM.grupoDe(p.tipo);
    let c = all.filter(q => q !== p && q.operacion === p.operacion && AM.grupoDe(q.tipo) === g && q.municipio === p.municipio);
    const cerca = c.filter(q => Math.abs(q.precio - p.precio) <= p.precio * 0.3);
    if (cerca.length >= n) c = cerca;
    const misma = q => (AM.norm(q.colonia) === AM.norm(p.colonia) ? 0 : 1);
    c.sort((a, b) => (misma(a) - misma(b)) || ((a.foto ? 0 : 1) - (b.foto ? 0 : 1)) ||
      (Math.abs(a.precio - p.precio) - Math.abs(b.precio - p.precio)));
    return c.slice(0, n);
  };
})();

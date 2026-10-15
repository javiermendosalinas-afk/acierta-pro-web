/* Acierta Max · Selección de propiedades para propuesta (solo asesores).
   Se activa cuando el asesor entra al Portal del coach (localStorage modo_asesor = 1) o con ?asesor=1.
   Agrega un botón «＋ Propuesta» a cada tarjeta con liga a ficha.html?eb=…, y una barra flotante que abre la selección en asesor.html. */
(function () {
  try { if (/[?&]asesor=1\b/.test(location.search)) localStorage.setItem('modo_asesor', '1'); if (/[?&]asesor=0\b/.test(location.search)) localStorage.removeItem('modo_asesor'); } catch (e) {}
  if (localStorage.getItem('modo_asesor') !== '1') return;
  const K = 'propuesta_sel';
  const leer = () => { try { return JSON.parse(localStorage.getItem(K) || '[]'); } catch (e) { return []; } };
  const guardar = s => { localStorage.setItem(K, JSON.stringify(s)); pintarBarra(); marcar(); };
  const tiene = eb => leer().some(x => x.eb === eb);
  function alternar(eb, op) { let s = leer(); s = tiene(eb) ? s.filter(x => x.eb !== eb) : s.concat([{ eb, op: op || '' }]).slice(0, 8); guardar(s); }
  const css = document.createElement('style');
  css.textContent = '.prp-btn{display:inline-flex;align-items:center;gap:4px;margin:6px 0 0;padding:6px 10px;border-radius:999px;border:1.5px solid #1D3A8A;background:#fff;color:#1D3A8A;font:600 12px system-ui,sans-serif;cursor:pointer}' +
    '.prp-btn.on{background:#1D3A8A;color:#fff}.prp-barra{position:fixed;right:14px;bottom:calc(84px + env(safe-area-inset-bottom));z-index:9999;background:#1D3A8A;color:#fff;border-radius:16px;padding:10px 12px;box-shadow:0 8px 24px rgba(0,0,0,.25);font:500 13px system-ui,sans-serif;display:flex;gap:10px;align-items:center;flex-wrap:wrap;max-width:92vw}' +
    '.prp-barra a,.prp-barra button{color:#fff;font:700 13px system-ui,sans-serif;background:rgba(255,255,255,.15);border:0;border-radius:10px;padding:7px 10px;text-decoration:none;cursor:pointer}';
  document.head.appendChild(css);
  const ebDe = href => { const m = /[?&]eb=([A-Za-z0-9-]+)/.exec(href || ''); return m ? m[1] : ''; };
  const opDe = href => { const m = /[?&]op=([A-Za-z]+)/.exec(href || ''); const o = m ? m[1].toUpperCase() : ''; return ({ V: 'VENTA', R: 'RENTA' })[o] || o; };
  function boton(eb, op) {
    const b = document.createElement('button'); b.type = 'button'; b.className = 'prp-btn'; b.dataset.eb = eb;
    b.onclick = e => { e.preventDefault(); e.stopPropagation(); alternar(eb, op); };
    return b;
  }
  function marcar() { document.querySelectorAll('.prp-btn').forEach(b => { const on = tiene(b.dataset.eb); b.classList.toggle('on', on); b.textContent = on ? '✓ En propuesta' : '＋ Propuesta'; }); }
  function escanear() {
    document.querySelectorAll('a[href*="ficha.html?eb="]').forEach(a => {
      const eb = ebDe(a.getAttribute('href')); if (!eb) return;
      const caja = a.closest('.card,.prop,.result,.item,li,article') || a.parentElement;
      if (!caja || caja.dataset.prp === eb) return;
      caja.dataset.prp = eb; caja.appendChild(boton(eb, opDe(a.getAttribute('href'))));
    });
    marcar();
  }
  let barra;
  function pintarBarra() {
    const s = leer();
    const enFicha = /ficha\.html$/.test(location.pathname) ? ebDe(location.search) : '';
    if (!barra) { barra = document.createElement('div'); barra.className = 'prp-barra'; document.body.appendChild(barra); }
    let h = `📋 Propuesta: <b>${s.length}</b>`;
    if (enFicha) h += ` <button type="button" id="prpEsta">${tiene(enFicha) ? '✓ Quitar esta' : '＋ Agregar esta'}</button>`;
    if (s.length) h += ` <a href="asesor.html">Armar en el portal</a> <button type="button" id="prpVaciar">Vaciar</button>`;
    barra.innerHTML = h; barra.hidden = !s.length && !enFicha;
    const be = document.getElementById('prpEsta'); if (be) be.onclick = () => alternar(enFicha, opDe(location.search));
    const bv = document.getElementById('prpVaciar'); if (bv) bv.onclick = () => { if (confirm('¿Vaciar la propuesta?')) guardar([]); };
  }
  function iniciar() { escanear(); pintarBarra(); new MutationObserver(() => { clearTimeout(iniciar.t); iniciar.t = setTimeout(escanear, 250); }).observe(document.body, { childList: true, subtree: true }); }
  document.readyState === 'loading' ? document.addEventListener('DOMContentLoaded', iniciar) : iniciar();
  window.addEventListener('storage', e => { if (e.key === K) { pintarBarra(); marcar(); } });
})();

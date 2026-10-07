// Página de suscripción al Pulso Inmobiliario (pulso.html) e invitaciones en el sitio.
const T = require('./sitio.js'); const { ok } = T;
const fs = require('fs');
(async () => {
  const llamadas = [];
  const interceptar = (u, op) => {
    if (!u.includes('/api/pulso/')) return null;
    const b = JSON.parse(op.body || '{}'); llamadas.push(b);
    return { ok: true, status: 200, json: async () => ({ ok: true, codigo: '4821', liga: 'https://wa.me/523333777337?text=PULSO%204821' }) };
  };
  const errores = [];
  const w = await T.abrir('pulso.html', '', errores, interceptar);
  const d = w.document, $ = id => d.getElementById(id);
  ok(/PULSO Acierta Max/.test(d.title) && d.querySelector('link[rel=canonical]'), 'título y canonical para buscadores');
  ok(d.querySelectorAll('.pu-cifra').length === 4 && d.querySelectorAll('.pu-barra').length === 3, 'adelanto con 4 cifras y gráfica de barras');
  ok(/Fuente:/.test(d.querySelector('.pu-fuente').textContent), 'la gráfica muestra su fuente');
  $('puEnviar').click(); await T.espera(50);
  ok(/nombre/.test($('puError').textContent) && !llamadas.length, 'sin nombre no envía y lo explica');
  $('puNombre').value = 'Ana Ruiz'; $('puWa').value = '33 2497 0007';
  $('puEnviar').click(); await T.espera(50);
  ok(/autorizaci/.test($('puError').textContent) && !llamadas.length, 'sin aceptar el aviso de privacidad no envía');
  d.querySelector('.pu-chips input[value="comprar"]').checked = true;
  d.querySelector('.pu-chips input[value="verifica"]').checked = true;
  $('puAcepto').checked = true; $('puEnviar').click(); await T.espera(300);
  const b = llamadas[0] || {};
  ok(b.nombre === 'Ana Ruiz' && b.whatsapp === '3324970007' && b.acepta === true && b.intereses.join() === 'comprar,verifica', 'envía nombre, WhatsApp limpio, intereses y consentimiento');
  ok(b.sitio_web === '' && typeof b.aviso_version === 'string', 'incluye la versión del aviso y el campo trampa vacío');
  const lnk = $('puAbrirWA');
  ok(lnk && /wa\.me\/523333777337\?text=PULSO%204821/.test(lnk.href), 'muestra el botón para recibirlo en WhatsApp con su código');
  ok(/PULSO 4821/.test(d.querySelector('.pu-listo').textContent) && $('puDescarga'), 'da la alternativa de escribir el código y la descarga inmediata');
  ok(fs.existsSync(T.RAIZ + '/assets/pulso/pulso-01-octubre-2026.pdf'), 'el PDF de la edición 01 está publicado');
  const ed = JSON.parse(fs.readFileSync(T.RAIZ + '/pulso/ediciones.json', 'utf8')).ediciones.filter(e => e.vigente);
  ok(ed.length === 1 && /pulso-01-octubre-2026\.pdf(\?v=\d+)?$/.test(ed[0].pdf_raw), 'hay exactamente una edición vigente y apunta al PDF publicado');
  const home = fs.readFileSync(T.RAIZ + '/index.html', 'utf8'), blog = fs.readFileSync(T.RAIZ + '/blog/colores-del-ano-2026-comex.html', 'utf8');
  ok(/href="pulso\.html"/.test(home) && /pulso-cta/.test(home) && /pulso-cta/.test(blog), 'invitación al Pulso en la portada (menú y sección) y en los artículos');
  ok(/pulso\.html/.test(fs.readFileSync(T.RAIZ + '/sitemap.xml', 'utf8')), 'la página está en el sitemap');
  ok(errores.length === 0, 'sin errores de JavaScript' + (errores.length ? ' -> ' + errores.slice(0, 2).join(' | ') : ''));
  process.exit(T.fallas ? 1 : 0);
})();

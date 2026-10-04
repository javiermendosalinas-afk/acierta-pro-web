// Lo construido antes que no debe romperse: comparador de 10, simulador de contado, enlace del paso de crédito, SEO y blog.
const T = require('./sitio.js'); const { ok } = T;
const fs = require('fs');
(async () => {
  const errores = [];
  const data = JSON.parse(fs.readFileSync(T.RAIZ + '/data.json', 'utf8'));
  const ids = [...new Set(data.map(p => p.eb))].slice(0, 12);

  let w = await T.abrir('index.html', '', errores);
  ids.forEach(eb => w.AM.cmp.toggle(eb));
  ok(w.AM.cmp.get().length === 10, `el comparador acepta hasta 10 (guardó ${w.AM.cmp.get().length} de 12 intentos)`);

  w = await T.abrir('simulador.html', '', errores); let d = w.document;
  const eng = d.getElementById('enganche');
  ok(eng.max === '100', 'simulador: enganche hasta 100%');
  eng.value = '100'; eng.dispatchEvent(new w.Event('input', { bubbles: true }));
  ok(/contado/i.test(d.getElementById('rMensual').textContent), 'simulador: al 100% avisa pago de contado');

  w = await T.abrir('proceso.html', '', errores); d = w.document;
  const a = d.querySelector('.paso[data-id="c2"] a.paso-enlace');
  ok(a && a.getAttribute('href') === 'simulador.html', 'proceso: el paso de precalificar enlaza al simulador');

  const robots = fs.readFileSync(T.RAIZ + '/robots.txt', 'utf8'), sitemap = fs.readFileSync(T.RAIZ + '/sitemap.xml', 'utf8');
  ok(/GPTBot/.test(robots) && /ClaudeBot/.test(robots) && /Sitemap:/i.test(robots), 'robots.txt permite a los bots de IA e indica el sitemap');
  ok(fs.existsSync(T.RAIZ + '/llms.txt'), 'llms.txt existe');
  const articulos = fs.readdirSync(T.RAIZ + '/blog').filter(f => f.endsWith('.html') && f !== 'index.html');
  ok(articulos.length >= 24, `el blog tiene ${articulos.length} artículos`);
  const faltan = articulos.filter(f => !sitemap.includes('/blog/' + f));
  ok(faltan.length === 0, 'todos los artículos están en el sitemap' + (faltan.length ? ': faltan ' + faltan.join(', ') : ''));
  const blogIdx = fs.readFileSync(T.RAIZ + '/blog/index.html', 'utf8');
  const sinTarjeta = articulos.filter(f => !blogIdx.includes('/blog/' + f));
  ok(sinTarjeta.length <= 6, `artículos sin tarjeta en el índice del blog: ${sinTarjeta.length}` + (sinTarjeta.length ? ' (' + sinTarjeta.join(', ') + ')' : ''));

  // el FAQ que lee Google debe coincidir con el visible
  const home = fs.readFileSync(T.RAIZ + '/index.html', 'utf8');
  const bloques = [...home.matchAll(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/g)].map(m => JSON.parse(m[1]));
  const faq = bloques.find(b => b['@type'] === 'FAQPage');
  const visibles = home.replace(/<script[\s\S]*?<\/script>/g, '');
  const desfasadas = faq.mainEntity.filter(q => !visibles.includes(q.acceptedAnswer.text.replace(/&/g, '&amp;')) && !visibles.includes(q.acceptedAnswer.text));
  ok(desfasadas.length === 0, 'FAQ visible = FAQ de Google (' + faq.mainEntity.length + ' preguntas)' + (desfasadas.length ? ' DESFASADAS: ' + desfasadas.map(q => q.name).join(' | ') : ''));
  ok(/Tlajomulco/.test(home) && /Más de 7,000/.test(home) && !/Más de 5,000/.test(home), 'la portada menciona los 5 municipios (incluye Tlajomulco) y "Más de 7,000"');
  ok(data.length > 7000, `el inventario publicado supera las 7,000 fichas (${data.length})`);
  ok(errores.length === 0, 'sin errores de JavaScript' + (errores.length ? ': ' + errores.slice(0, 2).join(' | ') : ''));
  process.exit(T.fallas ? 1 : 0);
})();

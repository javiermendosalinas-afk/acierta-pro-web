// acierta.pro replica la bolsa NeoJaus (origen inmobiliaria.pro) SIN depender de ella.
const T = require('./sitio.js'); const { ok } = T;
const fs = require('fs');
const resp = (j, status = 200) => ({ ok: status < 400, status, json: async () => j, headers: { get: () => null } });
const EB = JSON.parse(fs.readFileSync(T.RAIZ + '/data.json', 'utf8'));
const base = EB.find(p => p.segmento === 'vivienda' && p.foto && p.foto.startsWith('https://'));
const nj = i => Object.assign({}, base, { eb: 'NJ-' + (10000 + i).toString(16).toUpperCase(), fuente: 'neojaus', liga: 'https://inmobiliaria.pro/x', foto: 'https://cdn.neojaus.com/properties/u/a.webp' });
const BOLSA = Array.from({ length: 80 }, (_, i) => nj(i));
BOLSA[0] = Object.assign({}, BOLSA[0], { precio: 0 });                       // inválida: sin precio
BOLSA[1] = Object.assign({}, BOLSA[1], { municipio: 'Monterrey' });           // inválida: fuera de la ZMG
BOLSA[2] = Object.assign({}, BOLSA[2], { tambien_en: [{ clave: 'EB-AAA111', url: 'x' }] });  // gemela de EB: no se repite
const URL_BOLSA = 'raw.githubusercontent.com/javiermendosalinas-afk/aciertamax-bolsa';
async function caso(nombre, { cfg, bolsa, estado = 200, pagina = 'index.html', query = '' }) {
  const errores = [];
  const w = await T.abrir(pagina, query, errores, u => {
    if (u.includes('bolsa-config.json')) return cfg === undefined ? null : resp(cfg);
    if (u.includes(URL_BOLSA)) return resp(bolsa, estado);
    return null;
  });
  await T.espera(900);
  const todo = await w.AM.inventario();
  return { w, errores, todo, nj: todo.filter(p => /^NJ-/.test(p.eb)) };
}
(async () => {
  const cfgOn = JSON.parse(fs.readFileSync(T.RAIZ + '/bolsa-config.json', 'utf8'));
  let r = await caso('normal', { bolsa: BOLSA });
  ok(r.todo.length - r.nj.length === EB.length, 'EasyBroker completo siempre (' + EB.length + ' fichas)');
  ok(r.nj.length === 77, 'se replican las fichas válidas de la bolsa (77 de 80: sin precio, fuera de la ZMG y gemela de EB quedan fuera)');
  ok(r.nj.every(p => p.liga.startsWith('https://acierta.pro/ficha.html?eb=NJ-') && /op=(VENTA|RENTA)$/.test(p.liga)), 'en acierta.pro la liga es su propia ficha');
  ok(r.errores.length === 0, 'portada sin errores con la bolsa');
  r = await caso('apagada', { cfg: Object.assign({}, cfgOn, { activa: false }), bolsa: BOLSA });
  ok(r.nj.length === 0 && r.todo.length === EB.length, 'interruptor "activa": false → solo EasyBroker');
  r = await caso('falla', { bolsa: { error: 'x' }, estado: 500 });
  ok(r.nj.length === 0 && r.todo.length === EB.length && r.errores.length === 0, 'si inmobiliaria.pro falla, acierta.pro sigue con EasyBroker sin errores');
  r = await caso('casi vacía', { bolsa: BOLSA.slice(3, 20) });
  ok(r.nj.length === 0, 'paquete casi vacío (menos de 50) → se ignora');
  const rara = BOLSA.map((p, i) => i % 2 ? Object.assign({}, p, { foto: '' }) : p);
  r = await caso('rara', { bolsa: rara });
  ok(r.nj.length === 0, 'paquete con muchas fichas defectuosas → se ignora completo');
  const p = BOLSA[5];
  r = await caso('ficha', { bolsa: BOLSA, pagina: 'ficha.html', query: '?eb=' + p.eb + '&op=' + p.operacion });
  for (let i = 0; i < 30 && !r.w.document.body.textContent.includes(p.eb); i++) await T.espera(200);
  const visible = r.w.document.body.cloneNode(true);
  visible.querySelectorAll('script, template').forEach(s => s.remove());
  const txt = visible.textContent;
  ok(txt.includes(p.eb) && !/ya no está en nuestro inventario/.test(txt), 'la ficha NJ se abre en acierta.pro');
  ok(!visible.innerHTML.includes('Abrir en aciertamax.com') && !visible.innerHTML.includes('inmobiliaria.pro/x'), 'y no muestra enlace a aciertamax.com ni al originador');
  process.exit(T.fallas ? 1 : 0);
})();

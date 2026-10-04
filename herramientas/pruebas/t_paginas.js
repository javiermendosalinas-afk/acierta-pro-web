// Prueba de humo: cada página abre sin errores de JavaScript, y las herramientas de vivienda solo ven vivienda.
const T = require('./sitio.js'); const { ok } = T;
const fs = require('fs');
(async () => {
  const data = JSON.parse(fs.readFileSync(T.RAIZ + '/data.json', 'utf8'));
  const viv = data.filter(p => p.segmento ? p.segmento === 'vivienda' : !['oficina','local comercial','local en centro comercial','bodega comercial','bodega industrial','nave industrial','terreno comercial','terreno industrial'].includes(p.tipo));
  const conCoord = viv.filter(p => p.lat && p.lon && p.m2 && p.operacion === 'VENTA' && p.tipo === 'casa').slice(0, 3);
  const ids = conCoord.map(p => p.eb).join(',');
  const ficha = '?eb=' + viv[0].eb + '&op=' + (viv[0].operacion === 'RENTA' ? 'R' : 'V');

  const paginas = [
    ['index.html', ''], ['ficha.html', ficha], ['comparar.html', '?ids=' + ids], ['inversion.html', ''],
    ['mapa.html', ''], ['proceso.html', ''], ['simulador.html', ''], ['camino.html', ''], ['blog/index.html', ''], ['aviso-privacidad.html', ''],
  ];
  for (const [pag, q] of paginas) {
    const errores = [];
    let w;
    try { w = await T.abrir(pag, q, errores); } catch (e) { errores.push('abrir: ' + e.message); }
    ok(errores.length === 0, `${pag} abre sin errores de JavaScript` + (errores.length ? ' -> ' + errores.slice(0, 2).join(' | ') : ''));
    if (pag === 'inversion.html') ok(/TODAS = AM\.soloVivienda\(/.test(fs.readFileSync(T.RAIZ + '/' + pag, 'utf8')), 'inversion.html filtra a solo vivienda al cargar el inventario');
    if (pag === 'proceso.html' || pag === 'camino.html') ok(/TODAS = AM\.soloVivienda\(/.test(fs.readFileSync(T.RAIZ + '/' + pag, 'utf8')), `${pag} filtra a solo vivienda al cargar el inventario`);
    if (pag === 'mapa.html') ok(w.eval('ALL_PROPS.every(p => AM.segDe(p) === "vivienda")') && w.eval('ALL_PROPS.length') === viv.length, `mapa muestra solo vivienda (${w.eval('ALL_PROPS.length')} fichas)`);
  }
  const e2 = []; const wm = await T.abrir('mapa.html', '?seg=comercial', e2);
  ok(wm.eval('ALL_PROPS.length') > 0 && wm.eval('ALL_PROPS.every(p => AM.segDe(p) === "comercial")'), 'mapa.html?seg=comercial muestra solo comercial');
  process.exit(T.fallas ? 1 : 0);
})();

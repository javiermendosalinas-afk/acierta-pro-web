const T = require('./sitio.js'); const { ok } = T;
const fs = require('fs');
(async () => {
  const errores = [];
  const data = JSON.parse(fs.readFileSync(T.RAIZ + '/data.json', 'utf8'));
  const segDe = p => p.segmento || (['oficina','local comercial','local en centro comercial','bodega comercial','bodega industrial','nave industrial','terreno comercial','terreno industrial'].includes(p.tipo) ? 'comercial' : 'vivienda');
  const nViv = data.filter(p => segDe(p) === 'vivienda').length, nCom = data.length - nViv;

  let w = await T.abrir('index.html', '', errores), d = w.document;
  ok(!!d.getElementById('segToggle'), 'la portada tiene el selector Vivienda | Comercial');
  ok(d.querySelector('#segToggle button.active').dataset.seg === 'vivienda', 'por defecto abre en Vivienda');
  ok(w.eval('filtered.length') === nViv, `Vivienda por defecto: ${nViv} fichas, ninguna comercial (resultado: ${w.eval('filtered.length')})`);
  ok(w.eval('filtered.every(p => AM.segDe(p) === "vivienda")'), 'ninguna ficha comercial aparece en la vista de vivienda');
  const munis = [...d.querySelectorAll('#fMunicipio option')].map(o => o.value).filter(Boolean);
  ok(munis.length === 6 && munis.includes('Tlajomulco de Zúñiga') && munis.includes('Tlaquepaque') && munis.includes('Tonalá') && munis.includes('El Salto'), `el filtro de municipio tiene los 5 de la ZMG más El Salto (comercial): ${munis.join(', ')}`);
  const tiposViv = [...d.querySelectorAll('#fTipo option')].map(o => o.value);
  ok(tiposViv.includes('casa') && tiposViv.includes('departamento') && !tiposViv.includes('bodega'), `tipos de vivienda: ${tiposViv.join(',')}`);
  ok(/propiedades de vivienda/.test(d.getElementById('statsStrip').textContent) && /5\s*municipios/.test(d.getElementById('statsStrip').textContent), 'la franja de cifras habla de vivienda y de 5 municipios');

  // el filtro "Casa" ahora incluye casas en condominio
  const cond = data.filter(p => p.tipo === 'casa en condominio' && segDe(p) === 'vivienda').length;
  d.getElementById('fTipo').value = 'casa'; d.getElementById('fTipo').dispatchEvent(new w.Event('change'));
  ok(w.eval('filtered.some(p => p.tipo === "casa en condominio")') || cond === 0, 'el filtro Casa incluye las casas en condominio');

  // cambiar a Comercial
  d.querySelector('#segToggle button[data-seg="comercial"]').click();
  await T.espera(200);
  ok(w.eval('filtered.length') === nCom, `Comercial: ${nCom} fichas (resultado: ${w.eval('filtered.length')})`);
  ok(w.eval('filtered.every(p => AM.segDe(p) === "comercial")'), 'solo fichas comerciales en la vista comercial');
  const tiposCom = [...d.querySelectorAll('#fTipo option')].map(o => o.value);
  ok(tiposCom.includes('bodega') && tiposCom.includes('local') && tiposCom.includes('oficina'), `tipos comerciales: ${tiposCom.join(',')}`);
  ok(d.getElementById('fRecamaras').closest('.field').style.display === 'none', 'recámaras/baños/niveles se ocultan en comercial');
  ok(/comerciales/.test(d.getElementById('statsStrip').textContent), 'la franja de cifras habla de inmuebles comerciales');
  ok(w.location.search.includes('seg=comercial'), 'la URL recuerda el segmento (se puede compartir)');

  // precios por operación
  d.querySelector('#opToggle button[data-op="RENTA"]').click(); await T.espera(100);
  const opsRenta = [...d.querySelectorAll('#fPrecioMax option')].map(o => o.value).filter(Boolean).map(Number);
  ok(opsRenta.length && Math.max(...opsRenta) <= 500000, `rangos de renta comercial razonables (${opsRenta.join(',')})`);

  // volver a Vivienda
  d.querySelector('#segToggle button[data-seg="vivienda"]').click(); await T.espera(100);
  ok(w.eval('filtered.every(p => AM.segDe(p) === "vivienda")') && d.getElementById('fRecamaras').closest('.field').style.display !== 'none', 'volver a Vivienda restaura todo');

  // abrir directo en comercial por URL
  let w2 = await T.abrir('index.html', '?seg=comercial', errores);
  ok(w2.eval('filtered.every(p => AM.segDe(p) === "comercial")') && w2.eval('filtered.length') > 0, '?seg=comercial abre directo en Comercial');

  console.log('Errores de JS:', errores.length ? errores : 'ninguno');
  ok(errores.length === 0, 'sin errores de JavaScript');
  process.exit(T.fallas ? 1 : 0);
})();

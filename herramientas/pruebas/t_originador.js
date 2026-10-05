// Portal del coach: buscar al originador por clave (EB o NJ), incluidas claves relacionadas.
const T = require('./sitio.js'); const { ok } = T;
const fs = require('fs');
const resp = j => ({ ok: true, status: 200, json: async () => j, headers: { get: () => null } });
(async () => {
  const data = JSON.parse(fs.readFileSync(T.RAIZ + '/data.json', 'utf8'));
  const eb = data.find(p => (p.eb || '').startsWith('EB-'));
  const nj = { eb: 'NJ-10D65', operacion: 'VENTA', precio: 3500000, municipio: 'Zapopan', colonia: 'Palmira', tipo: 'casa', titulo: 'Casa NJ', fuente: 'neojaus',
               url_fuente: 'https://neojaus.com/propiedades/casa-x', liga: 'https://acierta.pro/ficha.html?eb=NJ-10D65&op=V', foto: 'x' };
  const ebConGemela = Object.assign({}, eb, { tambien_en: [{ clave: 'NJ-ABC12', url: 'https://neojaus.com/propiedades/gemela' }] });
  const interceptar = (u) => {
    if (u.includes('neojaus.json')) return resp([nj]);
    if (u.includes('data.json')) return resp(data.map(p => p.eb === eb.eb ? ebConGemela : p));
    if (u.includes('/api/asesor/usuarios')) return resp({ ok: true, usuarios: [{ usuario: 'javier', nombre: 'Javier Mendoza', activo: true }] });
    if (u.includes('/api/asesor/login')) return resp({ ok: true, token: 'TOK', nombre: 'Javier Mendoza' });
    return null;
  };
  const errores = [];
  const w = await T.abrir('asesor.html', '', errores, interceptar);
  const d = w.document, $ = id => d.getElementById(id);
  $('asUsuario').value = 'javier'; $('asClave').value = 'x'; $('asEntrar').click(); await T.espera(1500);
  $('asOrigClave').value = 'nj-10d65'; $('asOrigBuscar').click(); await T.espera(200);
  ok(/neojaus\.com\/propiedades\/casa-x/.test($('asOrigRes').innerHTML) && /no se publica en acierta\.pro/.test($('asOrigRes').textContent), 'clave NJ: la busca en la bolsa (fuera de acierta.pro) y da la liga al originador');
  $('asOrigClave').value = eb.eb; $('asOrigBuscar').click(); await T.espera(50);
  ok($('asOrigRes').innerHTML.includes(eb.liga.replace(/&/g, '&amp;')) && /gemela/.test($('asOrigRes').innerHTML), 'clave EB: liga a aciertamax.com y también a su publicación gemela en NeoJaus');
  $('asOrigClave').value = 'NJ-ABC12'; $('asOrigBuscar').click(); await T.espera(50);
  ok($('asOrigRes').textContent.includes(eb.eb), 'la clave NJ de una gemela encuentra la ficha de EasyBroker');
  $('asOrigClave').value = 'EB-NOEXIS'; $('asOrigBuscar').click(); await T.espera(50);
  ok(/no está en el inventario/.test($('asOrigRes').textContent), 'clave inexistente: lo explica');
  ok(errores.length === 0, 'sin errores de JavaScript' + (errores.length ? ' -> ' + errores.slice(0, 2).join(' | ') : ''));
  process.exit(T.fallas ? 1 : 0);
})();

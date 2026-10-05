// Portal del coach: propuesta preparada por enlace (#p=) y claves fuera del inventario (EasyBroker).
const T = require('./sitio.js'); const { ok } = T;
const resp = (j, status = 200) => ({ ok: status < 400, status, json: async () => j, headers: { get: () => null } });
(async () => {
  const llamadas = [];
  const fuera = { eb: 'EB-XB4792', operacion: 'RENTA', titulo: 'Casa en RENTA en Virreyes Residencial', tipo: 'casa', precio: 55000, municipio: 'Zapopan', colonia: 'Virreyes Residencial', recamaras: 4, banos: 4, m2: 355, foto: '', lat: 20.7, lon: -103.4, fuera_de_inventario: true };
  const interceptar = (u, op) => {
    if (!u.includes('/api/asesor/')) return null;
    const ruta = u.split('/api/asesor')[1]; const b = JSON.parse(op.body || '{}'); llamadas.push([ruta, b]);
    if (ruta === '/usuarios') return resp({ ok: true, usuarios: [{ usuario: 'javier', nombre: 'Javier Mendoza', activo: true }] });
    if (ruta === '/login') return resp({ ok: true, token: 'TOK', nombre: 'Javier Mendoza' });
    if (ruta === '/propiedad') return b.eb === 'EB-XB4792' ? resp({ ok: true, propiedad: fuera }) : resp({ ok: false, error: 'No encontré' }, 404);
    if (ruta === '/propuesta') return resp({ ok: true, cliente_ok: true, via: 'archivo', coach_ok: true, liga: 'x' });
    return resp({ ok: false }, 404);
  };
  const datos = { cliente: { nombre: 'Martha Cuevas', whatsapp: '3312285704' }, trato: 'usted', genero: 'f', criterios: 'casa en renta', nota: 'su contrato vence en diciembre',
    propiedades: [{ eb: 'EB-XB4792', operacion: 'RENTA', resumen: 'Resumen A', ventajas: ['V1', 'V2'] }, { eb: 'EB-NOEXISTE', operacion: 'RENTA' }] };
  const hash = '#p=' + Buffer.from(JSON.stringify(datos), 'utf8').toString('base64').replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
  const errores = [];
  const w = await T.abrir('asesor.html', hash, errores, interceptar);
  w.confirm = () => true; w.alert = () => {};
  const d = w.document, $ = id => d.getElementById(id);
  $('asUsuario').value = 'javier'; $('asClave').value = 'x'; $('asEntrar').click(); await T.espera(1500);
  ok($('asNombre').value === 'Martha Cuevas' && $('asWa').value === '3312285704', 'el enlace llena nombre y WhatsApp del cliente');
  ok($('asTrato').value === 'usted' && $('asGenero').value === 'f', 'y el trato de usted con saludo "Estimada"');
  const cards = d.querySelectorAll('.as-prop');
  ok(cards.length === 1 && cards[0].textContent.includes('EB-XB4792'), 'trae de EasyBroker la clave que no está en el inventario');
  ok(cards[0].querySelector('textarea[data-campo="resumen"]').value === 'Resumen A' && cards[0].querySelector('textarea[data-campo="ventajas"]').value === 'V1\nV2', 'respeta el resumen y las ventajas preparados');
  ok(/No encontré: EB-NOEXISTE/.test($('asMsg').textContent), 'avisa qué claves no encontró');
  ok(!/#p=/.test(w.location.href), 'borra los datos del enlace de la barra de direcciones');
  $('asVista').click(); await T.espera(200);
  const v = llamadas.find(l => l[0] === '/propuesta');
  ok(v && v[1].trato === 'usted' && v[1].genero === 'f' && v[1].vio_en_sitio === false, 'la vista previa manda trato, saludo y que no vio propiedades en el sitio');
  $('asBuscarEB').value = 'eb-wv3319'; $('asBuscarEB').dispatchEvent(new w.Event('input')); await T.espera(50);
  ok(!!d.querySelector('#asSugerencias button[data-eb="EB-WV3319"]'), 'al teclear una clave que no está, ofrece buscarla en EasyBroker');
  ok(errores.length === 0, 'sin errores de JavaScript' + (errores.length ? ' -> ' + errores.slice(0, 2).join(' | ') : ''));
  process.exit(T.fallas ? 1 : 0);
})();

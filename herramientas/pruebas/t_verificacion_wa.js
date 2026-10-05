// Verificación invertida de WhatsApp (4-oct-2026): el cliente nos escribe
// "Mi código Acierta es 1234" y la ventana avanza sola al confirmarse.
const T = require('./sitio.js'); const { ok } = T;
const fs = require('fs');
(async () => {
  const cfg = JSON.parse(fs.readFileSync(T.RAIZ + '/camino-datos.json', 'utf8'));
  const errores = [];
  const w = await T.abrir('index.html', '', errores);
  const llamadas = []; let verificadoEnServidor = false;
  const fetchOrig = w.fetch;
  w.fetch = (u, op) => {
    if (String(u).startsWith(cfg.endpoint)) {
      const ruta = String(u).slice(cfg.endpoint.length); const cuerpo = JSON.parse((op && op.body) || '{}');
      llamadas.push(ruta);
      let j = { ok: true };
      if (ruta === '/verificar/iniciar') j = { ok: true, verificado: false, codigo: '1234', liga: 'https://wa.me/523333777337?text=Hola%2C%20quiero%20confirmar%20mi%20WhatsApp.%20Mi%20c%C3%B3digo%20Acierta%20es%201234' };
      if (ruta === '/verificar/estado') j = { ok: true, verificado: verificadoEnServidor && cuerpo.whatsapp === '3324970007' };
      return Promise.resolve({ ok: true, status: 200, json: async () => j });
    }
    return fetchOrig(u, op);
  };
  const d = w.document;
  w.AM.asegurarLead({ motivo: 'prueba' });
  await T.espera(300);
  const wa = d.getElementById('amWa');
  ok(!!wa, 'se abre la ventana de contacto');
  wa.value = '3324970007'; wa.dispatchEvent(new w.Event('input', { bubbles: true }));
  const btn = d.getElementById('amBtnEnviarWA');
  ok(btn && /Verificar por WhatsApp/.test(btn.textContent), 'con un número válido aparece "Verificar por WhatsApp"');
  btn.click(); await T.espera(200);
  const lnk = d.getElementById('amLnkAbrirWA');
  ok(lnk && /^https:\/\/wa\.me\/523333777337\?text=/.test(lnk.getAttribute('href')) && /Acierta%20es%201234/.test(lnk.getAttribute('href')),
     'aparece "Abrir WhatsApp" con el mensaje y el código ya escritos');
  ok(/1234/.test(d.getElementById('amVerifWA').textContent) && /avanza sola/.test(d.getElementById('amVerifWA').textContent), 'explica qué hacer y muestra el código');
  await T.espera(3300);
  ok(llamadas.includes('/verificar/estado') && !/verificado/.test(d.getElementById('amVerifWA').textContent.replace('Verificar','')), 'consulta el estado sola y sigue esperando mientras no llega el mensaje');
  verificadoEnServidor = true;
  w.dispatchEvent(new w.Event('focus')); await T.espera(300);
  ok(/WhatsApp verificado/.test(d.getElementById('amVerifWA').textContent), 'al llegar el mensaje (y regresar a la página) queda "✅ WhatsApp verificado" sin escribir nada');
  wa.value = '3311112222'; wa.dispatchEvent(new w.Event('input', { bubbles: true }));
  ok(!!d.getElementById('amBtnEnviarWA'), 'si cambia el número, pide verificar de nuevo');
  ok(!llamadas.includes('/verificar/enviar') && !llamadas.includes('/verificar/confirmar'), 'ya no usa el envío de código por plantilla');
  const cam = fs.readFileSync(T.RAIZ + '/camino.html', 'utf8');
  ok(/\/verificar\/iniciar/.test(cam) && /\/verificar\/estado/.test(cam) && !/\/verificar\/enviar/.test(cam), 'camino.html usa el mismo flujo nuevo');
  ok(errores.length === 0, 'sin errores de JavaScript' + (errores.length ? ' -> ' + errores.slice(0, 2).join(' | ') : ''));
  process.exit(T.fallas ? 1 : 0);
})();

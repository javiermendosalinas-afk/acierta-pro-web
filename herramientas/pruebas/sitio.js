// Arnés de pruebas del sitio: abre una página en jsdom leyendo los archivos locales (sin red).
const { JSDOM, VirtualConsole, ResourceLoader } = require('jsdom');
const fs = require('fs'); const path = require('path');
const RAIZ = path.resolve(__dirname, '..', '..');
const ORIGEN = 'https://acierta.pro/';

const T = { fallas: 0, RAIZ };
T.ok = (c, m) => { if (!c) T.fallas++; console.log((c ? 'OK   ' : 'FALLA ') + m); };
T.espera = ms => new Promise(r => setTimeout(r, ms));

class Cargador extends ResourceLoader {
  fetch(url) {
    if (url.startsWith(ORIGEN)) {
      const ruta = path.join(RAIZ, decodeURIComponent(new URL(url).pathname));
      // Leaflet no corre en jsdom (no hay layout): se sustituye por un doble que acepta cualquier llamada encadenada
      if (/leaflet\.js$/.test(ruta)) return Promise.resolve(Buffer.from(
        'window.L = (function(){ var s = new Proxy(function(){}, { get: function(t,k){ return k === "then" ? undefined : s; }, apply: function(){ return s; }, construct: function(){ return s; } }); return s; })();'));
      if (fs.existsSync(ruta) && fs.statSync(ruta).isFile()) return Promise.resolve(fs.readFileSync(ruta));
    }
    return Promise.resolve(Buffer.from(''));      // fuentes, analítica, etc.: vacío, sin red
  }
}

T.abrir = async function (pagina, query = '', errores = []) {
  const html = fs.readFileSync(path.join(RAIZ, pagina), 'utf8');
  const vc = new VirtualConsole();
  vc.on('jsdomError', e => errores.push(String(e.message || e)));
  vc.on('error', e => errores.push(String(e)));
  const dom = new JSDOM(html, {
    url: ORIGEN + pagina + query, runScripts: 'dangerously', resources: new Cargador(),
    pretendToBeVisual: true, virtualConsole: vc,
    beforeParse(w) {
      w.fetch = (u) => {
        const p = new URL(u, w.location.href);
        if (p.origin === 'https://acierta.pro') {
          const ruta = path.join(RAIZ, decodeURIComponent(p.pathname));
          if (fs.existsSync(ruta)) {
            const txt = fs.readFileSync(ruta, 'utf8');
            return Promise.resolve({ ok: true, status: 200, json: async () => JSON.parse(txt), text: async () => txt });
          }
          return Promise.resolve({ ok: false, status: 404, json: async () => { throw new Error('404'); }, text: async () => '' });
        }
        return Promise.reject(new Error('red bloqueada en pruebas: ' + u));
      };
      w.scrollTo = () => {};
      w.HTMLElement.prototype.scrollIntoView = () => {};
    },
  });
  await new Promise(r => dom.window.addEventListener('load', r));
  await T.espera(700);
  return dom.window;
};
module.exports = T;

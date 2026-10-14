/* Buscador comercial (locales, oficinas, bodegas y naves) para acierta.pro, inmobiliaria.pro y losprofesionalesinmobiliarios.com.
   Uso: <div id="comercial" data-sitio="acierta|inmobiliaria|lpi" data-estilo="tarjeta|circulo"></div><script src="https://acierta.pro/comercial.js"></script> */
(function(){
var box=document.getElementById("comercial");if(!box)return;
var sitio=box.dataset.sitio||"acierta",circ=box.dataset.estilo=="circulo",D=[],sel=[],vista=24,o="R";
var NOM={local:"Local comercial",cc:"Local en plaza comercial",oficina:"Oficina",bodega:"Bodega",nave:"Nave industrial"};
var fmt=function(v){return "$"+v.toLocaleString("es-MX")};
var css=document.createElement("style");css.textContent=
".cm-f{display:flex;flex-wrap:wrap;gap:10px;align-items:flex-end;margin:18px 0;padding:16px;border:1px solid rgba(0,0,0,.12);border-radius:16px;background:#fff}"+
".cm-f label{display:flex;flex-direction:column;gap:4px;font-size:.85rem;opacity:.8}.cm-f select,.cm-f input{font:inherit;font-size:1rem;padding:9px 12px;border:1.5px solid rgba(0,0,0,.18);border-radius:10px;min-width:150px;background:#fff}"+
".cm-seg{display:flex;border:2px solid currentColor;border-radius:999px;overflow:hidden}.cm-seg button{font:inherit;font-weight:700;border:0;background:transparent;padding:9px 16px;cursor:pointer;color:inherit}.cm-seg button.on{background:#1b1e22;color:#fff}"+
".cm-n{margin:8px 0 18px;opacity:.75}.cm-g{display:grid;grid-template-columns:repeat(auto-fill,minmax(250px,1fr));gap:22px}"+
".cm-c{display:block;text-decoration:none;color:inherit;background:#fff;border:1px solid rgba(0,0,0,.1);border-radius:16px;overflow:hidden}"+
".cm-c .im{aspect-ratio:4/3;background:#e9e6e0 center/cover}.cm-c .tx{padding:12px 14px}.cm-c b{display:block;font-size:1.2rem}.cm-c span{display:block;font-size:.92rem;opacity:.75}"+
".cm-c .q{opacity:1;color:#1FA855;font-weight:700;margin-top:6px}"+
".cm-o .cm-c{background:none;border:0;text-align:center}.cm-o .cm-c .im{aspect-ratio:1;border-radius:50%;border:6px solid #fff;box-shadow:0 0 0 2px #1b1e22}"+
".cm-o .cm-c:nth-child(3n+1) .im{box-shadow:0 0 0 2px #1D3A8A}.cm-o .cm-c:nth-child(3n+2) .im{box-shadow:0 0 0 2px #D8452F}.cm-o .cm-c:nth-child(3n) .im{box-shadow:0 0 0 2px #E0A43A}"+
".cm-m{display:block;margin:26px auto 0;font:inherit;font-weight:700;padding:12px 26px;border-radius:999px;border:2px solid currentColor;background:none;cursor:pointer;color:inherit}"+
"@media(max-width:700px){.cm-f select,.cm-f input{min-width:0;width:100%}.cm-f label{flex:1 1 45%}}";document.head.appendChild(css);
box.innerHTML='<form class="cm-f" onsubmit="return false"><div class="cm-seg"><button type="button" data-o="R" class="on">Rentar</button><button type="button" data-o="V">Comprar</button></div>'+
'<label>Tipo<select data-k="t"><option value="">Todos</option><option value="local">Local comercial</option><option value="cc">Local en plaza</option><option value="oficina">Oficina</option><option value="bodega">Bodega</option><option value="nave">Nave industrial</option></select></label>'+
'<label>Municipio<select data-k="u"><option value="">Toda la ZMG</option><option>Guadalajara</option><option>Zapopan</option><option>Tlaquepaque</option><option value="Tlajomulco de Zúñiga">Tlajomulco</option><option>Tonalá</option></select></label>'+
'<label>Superficie mínima<select data-k="m"><option value="">Cualquiera</option><option value="50">50 m²</option><option value="100">100 m²</option><option value="200">200 m²</option><option value="500">500 m²</option><option value="1000">1,000 m²</option><option value="3000">3,000 m²</option></select></label>'+
'<label>Precio hasta<select data-k="p"></select></label><label>Zona o palabra<input data-k="q" type="search" placeholder="Ej. Av. Vallarta, esquina, plaza"></label></form>'+
'<p class="cm-n">Cargando…</p><div class="cm-g'+(circ?' cm-o':'')+'"></div><button type="button" class="cm-m" hidden>Ver más</button>';
if(circ)box.querySelector(".cm-g").parentNode.classList.add("cm-o");
var $=function(s){return box.querySelector(s)},v=function(k){return $('[data-k="'+k+'"]').value};
function topes(){var s=$('[data-k="p"]'),T=o=="R"?[10000,20000,40000,80000,150000,300000]:[2000000,4000000,8000000,15000000,30000000];s.innerHTML='<option value="">Sin límite</option>'+T.map(function(x){return '<option value="'+x+'">'+fmt(x)+'</option>'}).join("");}
function filtrar(){var t=v("t"),u=v("u"),m=+v("m")||0,p=+v("p")||0,q=v("q").trim().toLowerCase();
 sel=D.filter(function(x){return x.o==o&&(!t||x.t==t)&&(!u||x.u==u)&&(!m||(x.m||0)>=m)&&(!p||x.p<=p)&&(!q||(x.c+" "+x.ti+" "+x.u).toLowerCase().indexOf(q)>=0)}).sort(function(a,b){return a.p-b.p});vista=24;pintar();}
function pintar(){var origen={acierta:"acierta.pro",inmobiliaria:"inmobiliaria.pro",lpi:"losprofesionalesinmobiliarios.com"}[sitio];
 $(".cm-g").innerHTML=sel.slice(0,vista).map(function(x){return '<a class="cm-c" href="'+x.l+'" target="_blank" rel="noopener"><div class="im" role="img" aria-label="'+(x.ti||NOM[x.t]).replace(/"/g,"")+'" style="background-image:url(\''+x.f+'\')"></div><div class="tx"><b>'+fmt(x.p)+(x.o=="R"?" /mes":"")+'</b><span>'+NOM[x.t]+(x.m?" · "+x.m.toLocaleString("es-MX")+" m²":"")+'</span><span>'+(x.c?x.c+", ":"")+x.u+'</span><span class="q">'+x.e+'</span></div></a>'}).join("");
 $(".cm-n").innerHTML=sel.length?sel.length.toLocaleString("es-MX")+" propiedades comerciales, de menor a mayor precio. ¿Buscas algo específico? <a href='https://wa.me/523333777337?text="+encodeURIComponent("Hola, vengo de "+origen+". Busco un local, oficina o bodega")+"' target='_blank' rel='noopener'>Escríbenos</a> y lo buscamos por ti.":"No encontramos propiedades con estos filtros. Prueba quitando alguno.";
 $(".cm-m").hidden=vista>=sel.length;}
box.querySelectorAll(".cm-seg button").forEach(function(b){b.onclick=function(){o=b.dataset.o;box.querySelectorAll(".cm-seg button").forEach(function(x){x.classList.toggle("on",x==b)});topes();filtrar()}});
box.querySelectorAll("select").forEach(function(s){s.onchange=filtrar});$('[data-k="q"]').oninput=function(){clearTimeout(this._t);this._t=setTimeout(filtrar,250)};
$(".cm-m").onclick=function(){vista+=24;pintar()};topes();
fetch("https://acierta.pro/comercial.json").then(function(r){return r.json()}).then(function(d){D=d;filtrar()}).catch(function(){$(".cm-n").textContent="No pudimos cargar el inventario comercial. Escríbenos por WhatsApp al 33 3377 7337."});
})();

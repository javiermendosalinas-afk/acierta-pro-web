"""Páginas fijas para buscadores (Google, Bing y asistentes de IA).

Genera, a partir del inventario publicado (data.json de EasyBroker + neojaus.json de la bolsa):
  /propiedades/<municipio>/<clave>-<venta|renta>.html   una página por propiedad
  /zonas/<municipio>/<colonia>/<tipo>-en-<venta|renta>.html   una por colonia y tipo (con 3 o más)
  /zonas/<municipio>/<tipo>-en-<venta|renta>.html        una por municipio y tipo
  /zonas/index.html                                     índice de zonas
  /sitemap-propiedades-N.xml, /sitemap-zonas.xml        mapas del sitio (y los agrega a robots.txt)

El HTML es completo sin JavaScript: lo que ve el buscador es lo mismo que ve el cliente.
Uso: python herramientas/generar_seo.py
"""
import html, json, os, re, shutil, statistics, unicodedata
from datetime import datetime, timezone

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITIO = "https://acierta.pro"
WA = "523333777337"
HOY = datetime.now(timezone.utc).strftime("%Y-%m-%d")
GRUPOS = {"casa": ["casa", "casa en condominio", "casa con uso de suelo", "quinta", "rancho", "villa"], "departamento": ["departamento"],
          "terreno": ["terreno", "terreno industrial", "terreno comercial"], "local": ["local comercial", "local en centro comercial"],
          "oficina": ["oficina"], "bodega": ["bodega comercial", "bodega industrial", "nave industrial"], "edificio": ["edificio"]}
PLURAL = {"casa": "Casas", "departamento": "Departamentos", "terreno": "Terrenos", "local": "Locales comerciales", "oficina": "Oficinas",
          "bodega": "Bodegas y naves", "edificio": "Edificios"}
SLUG_GRUPO = {"casa": "casas", "departamento": "departamentos", "terreno": "terrenos", "local": "locales-comerciales", "oficina": "oficinas",
              "bodega": "bodegas", "edificio": "edificios"}
E = lambda s: html.escape(str(s if s is not None else ""), quote=True)


def slug(s):
    s = unicodedata.normalize("NFKD", str(s or "")).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-") or "sin-colonia"


def grupo_de(tipo):
    for k, v in GRUPOS.items():
        if tipo in v:
            return k
    return None


def num(x):
    return int(x) if isinstance(x, float) and x.is_integer() else x


def dinero(x):
    return "${:,.0f}".format(x) if x else "—"


def es_mxn(p):
    return not p.get("moneda") or p.get("moneda") == "MXN"


def pm2(p):
    return p["precio"] / p["m2"] if p.get("m2") and p.get("precio") and es_mxn(p) else None


def url_prop(p):
    return f"/propiedades/{slug(p['municipio'])}/{p['eb'].lower()}-{'renta' if p['operacion'] == 'RENTA' else 'venta'}.html"


def url_zona(muni, col, g, op):
    base = f"/zonas/{slug(muni)}/" + (f"{slug(col)}/" if col else "")
    return base + f"{SLUG_GRUPO[g]}-en-{'renta' if op == 'RENTA' else 'venta'}.html"


def foto_tam(url, w, h):
    if not url or "easybroker" not in url:
        return url
    url = re.sub(r"([?&])width=\d+", rf"\g<1>width={w}", url) if re.search(r"[?&]width=\d+", url) else url + ("&" if "?" in url else "?") + f"width={w}"
    return re.sub(r"([?&])height=\d+", rf"\g<1>height={h}", url) if re.search(r"[?&]height=\d+", url) else url + f"&height={h}"


def cargar():
    with open(os.path.join(RAIZ, "data.json"), encoding="utf-8") as fh:
        eb = json.load(fh)
    nj = []
    ruta = os.path.join(RAIZ, "herramientas", "neojaus", "neojaus.json")
    if os.path.exists(ruta):
        with open(ruta, encoding="utf-8") as fh:
            nj = [r for r in json.load(fh) if not any(str(x.get("clave", "")).startswith("EB-") for x in (r.get("tambien_en") or []))]
    detalle = {}
    for sub in (("neojaus", "fichas"), ("eb", "fichas")):
        dirf = os.path.join(RAIZ, "herramientas", *sub)
        if os.path.isdir(dirf):
            for f in os.listdir(dirf):
                if f.endswith(".json"):
                    with open(os.path.join(dirf, f), encoding="utf-8") as fh:
                        detalle.update(json.load(fh))
    props, vistos = [], set()
    for p in eb + nj:
        g = grupo_de(p.get("tipo"))
        if not g or not p.get("precio") or not p.get("eb") or not p.get("municipio"):
            continue
        k = (p["eb"], p["operacion"])
        if k in vistos:
            continue
        vistos.add(k)
        p = dict(p, grupo=g, colonia=(p.get("colonia") or "").strip())
        if p["eb"] in detalle:
            p["detalle"] = detalle[p["eb"]]
        props.append(p)
    return props


def estadisticas(lista):
    pr = sorted(p["precio"] for p in lista if es_mxn(p))
    m2 = sorted(v for v in (pm2(p) for p in lista) if v)
    return {"n": len(lista), "mediana": statistics.median(pr) if pr else None, "min": pr[0] if pr else None, "max": pr[-1] if pr else None,
            "pm2": statistics.median(m2) if len(m2) >= 3 else None, "n_pm2": len(m2)}


CSS_EXTRA = '<link rel="stylesheet" href="/seo.css">'
CSS_SEO = """
.seo-wrap{max-width:1100px;margin:0 auto;padding:24px 20px 40px}.migas{font-size:14px;color:#5b6575;margin-bottom:14px}.migas a{color:#5b6575}
.seo-top{display:grid;grid-template-columns:1.1fr 1fr;gap:28px;align-items:start}@media(max-width:820px){.seo-top{grid-template-columns:1fr}}
.seo-foto{border-radius:14px;overflow:hidden;background:#0f1f3d;aspect-ratio:3/2}.seo-foto img{width:100%;height:100%;object-fit:cover;display:block}
.seo-mini{display:flex;gap:8px;margin-top:8px;overflow-x:auto}.seo-mini img{width:92px;height:68px;object-fit:cover;border-radius:8px;flex:none}
.seo-eyebrow{color:#d62828;font-weight:700;letter-spacing:.06em;text-transform:uppercase;font-size:13px}.seo-precio{font-family:Fraunces,serif;font-size:2.1rem;font-weight:700;color:#0a1f3f;margin:6px 0}
.seo-chips{display:flex;flex-wrap:wrap;gap:8px;margin:10px 0 16px}.seo-chips span{border:1px solid #d5dbe4;border-radius:999px;padding:6px 12px;font-size:14px;background:#fff}
.seo-cta{display:flex;flex-wrap:wrap;gap:10px}.seo-card{background:#fff;border-radius:14px;padding:20px 22px;margin-top:22px;box-shadow:0 1px 3px rgba(10,31,63,.08)}
.seo-card h2{font-family:Fraunces,serif;margin:0 0 10px;font-size:1.35rem}.seo-desc{white-space:pre-line;line-height:1.65}
.seo-stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:12px;margin:14px 0}.seo-stats div{background:#f4f6f9;border-radius:10px;padding:12px 14px}
.seo-stats b{display:block;font-family:Fraunces,serif;font-size:1.3rem;color:#0a1f3f}.seo-stats span{font-size:13px;color:#5b6575}
.seo-tabla{width:100%;border-collapse:collapse;font-size:15px}.seo-tabla th,.seo-tabla td{text-align:left;padding:8px 10px;border-bottom:1px solid #e5e9f0}.seo-tabla th{background:#0a1f3f;color:#fff}
.seo-links{columns:3 220px;font-size:15px;line-height:1.9}.seo-faq dt{font-weight:700;margin-top:12px}.seo-faq dd{margin:4px 0 0}
"""


def cabeza(titulo, desc, canon, imagen=None, extra=""):
    img = f'<meta property="og:image" content="{E(imagen)}">' if imagen else ""
    return f"""<!DOCTYPE html>
<html lang="es-MX">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{E(titulo)}</title>
<meta name="description" content="{E(desc)}">
<link rel="canonical" href="{SITIO}{canon}">
<meta property="og:type" content="website"><meta property="og:title" content="{E(titulo)}"><meta property="og:description" content="{E(desc)}">
<meta property="og:url" content="{SITIO}{canon}"><meta property="og:site_name" content="Acierta Max"><meta property="og:locale" content="es_MX">{img}
<meta name="twitter:card" content="summary_large_image">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Fraunces:wght@500;600;700&family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
<link rel="stylesheet" href="/styles.css">{CSS_EXTRA}{extra}
</head>
<body>
<header class="site-header"><div class="header-inner">
<a href="/"><div class="logo"><span class="pin"></span>Acierta<b>Max</b></div></a>
<nav class="header-nav"><a href="/mapa.html">Buscar por zona</a><a href="/zonas/">Zonas</a><a href="/blog/">Blog</a></nav>
<a class="header-cta" href="https://wa.me/{WA}?text=Hola%2C%20quiero%20m%C3%A1s%20informaci%C3%B3n" target="_blank" rel="noopener">Habla con MAX →</a>
</div></header>
<main class="seo-wrap">"""


PIE = """</main>
<footer class="site-footer"><strong>Acierta Max</strong> · Profesionales Inmobiliarios · Zona Metropolitana de Guadalajara<br>
Socio AMPI · Información y disponibilidad sujetas a confirmación · <a href="/zonas/">Todas las zonas</a></footer>
</body></html>"""


def tarjeta(p):
    u = url_prop(p)
    bits = [x for x in (f"{p['recamaras']} rec" if p.get("recamaras") else "", f"{num(p['banos'])} baños" if p.get("banos") else "",
                        f"{round(p['m2'])} m²" if p.get("m2") else "") if x]
    foto = f'<img src="{E(foto_tam(p["foto"], 720, 480))}" alt="{E(p["titulo"])}" loading="lazy">' if p.get("foto") else ""
    lugar = (p["colonia"] + ", " if p["colonia"] else "") + p["municipio"]
    return f"""<div class="card"><a class="card-media" href="{u}" style="background:#0f1f3d">{foto}<span class="card-op">{E(p['operacion'])}</span><span class="card-tipo">{E(p['tipo'])}</span></a>
<div class="card-body"><div class="card-price">{'' if es_mxn(p) else 'US'}{dinero(p['precio'])}<span> {'MXN' if es_mxn(p) else 'USD'}{'/mes' if p['operacion'] == 'RENTA' else ''}</span></div>
<a class="card-title" href="{u}">{E(p['titulo'])}</a><div class="card-loc">📍 {E(lugar)}</div><div class="card-meta">{''.join(f'<span>{E(b)}</span>' for b in bits)}</div>
<div class="card-cta"><a class="btn-outline" href="{u}">Ver ficha</a></div></div></div>"""


def pagina_prop(p, comps_muni, comps_col, similares):
    op = "renta" if p["operacion"] == "RENTA" else "venta"
    lugar = (p["colonia"] + ", " if p["colonia"] else "") + p["municipio"]
    d = p.get("detalle") or {}
    fotos = [f"https://cdn.neojaus.com/properties/{d['uid']}/{n}" for n in d.get("fotos", [])] if d.get("uid") else list(d.get("fotos") or [])
    if not fotos and p.get("foto"):
        fotos = [p["foto"]]
    precio_txt = ("" if es_mxn(p) else "US") + dinero(p["precio"]) + (" al mes" if op == "renta" else "")
    datos = [x for x in (f"{p['recamaras']} recámaras" if p.get("recamaras") else "", f"{num(p['banos'])} baños" if p.get("banos") else "",
                         f"{round(p['m2'])} m²" if p.get("m2") else "", f"Terreno {round(p['terreno'])} m²" if p.get("terreno") else "",
                         f"{d['estacionamientos']} estacionamientos" if d.get("estacionamientos") else "", f"Código {p['eb']}") if x]
    titulo = f"{p['titulo']} | {precio_txt} | Acierta Max"
    desc = f"{p['tipo'].capitalize()} en {op} en {lugar}: " + ", ".join(datos[:4]) + f". {precio_txt} MXN. Agenda tu visita con Acierta Max."
    # análisis de precio
    analisis = ""
    v = pm2(p)
    for nombre, comps in ((f"{PLURAL[p['grupo']].lower()} en {op} en {p['colonia']}", comps_col), (f"{PLURAL[p['grupo']].lower()} en {op} en {p['municipio']}", comps_muni)):
        st = estadisticas(comps)
        if v and st["pm2"] and st["n_pm2"] >= 5:
            dif = (v / st["pm2"] - 1) * 100
            pos = "por encima" if dif > 3 else "por debajo" if dif < -3 else "en línea con"
            frase = f"está {abs(dif):.0f}% {pos} de" if pos != "en línea con" else "está en línea con"
            analisis = f"""<section class="seo-card"><h2>¿Está bien de precio?</h2><p>Su precio por m² ({dinero(v)}) {frase} la mediana de {E(nombre)} ({dinero(st['pm2'])} por m², {st['n_pm2']} propiedades comparables).</p>
<div class="seo-stats"><div><b>{dinero(v)}</b><span>por m² esta propiedad</span></div><div><b>{dinero(st['pm2'])}</b><span>por m² mediana de la zona</span></div><div><b>{dinero(st['mediana'])}</b><span>precio mediano de la zona</span></div></div></section>"""
            break
    texto = d.get("descripcion") or (f"{p['tipo'].capitalize()} en {op} en {lugar}. " + (f"Cuenta con {', '.join(datos[:-1])}. " if len(datos) > 1 else "") +
                                     f"Precio: {precio_txt} MXN. Código de la propiedad: {p['eb']}. Un asesor de Acierta Max te acompaña en la visita, la revisión de documentos y la negociación.")
    wa = f"https://wa.me/{WA}?text=" + re.sub(r"\s", "%20", html.escape(f"Hola, me interesa esta propiedad: {p['titulo']} ({p['eb']}, {op}) — {SITIO}{url_prop(p)}"))
    zona_url = url_zona(p["municipio"], p["colonia"], p["grupo"], p["operacion"]) if p["colonia"] and len(comps_col) >= 3 else url_zona(p["municipio"], None, p["grupo"], p["operacion"])
    ld = {"@context": "https://schema.org", "@type": "RealEstateListing", "name": p["titulo"], "url": SITIO + url_prop(p), 
          "image": fotos[:6], "description": texto[:500],
          "offers": {"@type": "Offer", "price": round(p["precio"]), "priceCurrency": "MXN" if es_mxn(p) else "USD", "availability": "https://schema.org/InStock",
                     "businessFunction": "http://purl.org/goodrelations/v1#LeaseOut" if op == "renta" else "http://purl.org/goodrelations/v1#Sell"},
          "itemOffered": {"@type": "Accommodation" if p["grupo"] in ("casa", "departamento") else "Place", "name": p["titulo"],
                          "address": {"@type": "PostalAddress", "addressLocality": p["municipio"], "addressRegion": "Jalisco", "addressCountry": "MX",
                                      **({"streetAddress": p["colonia"]} if p["colonia"] else {})},
                          **({"geo": {"@type": "GeoCoordinates", "latitude": p["lat"], "longitude": p["lon"]}} if p.get("lat") and p.get("lon") else {}),
                          **({"numberOfRooms": p["recamaras"]} if p.get("recamaras") else {}),
                          **({"floorSize": {"@type": "QuantitativeValue", "value": round(p["m2"]), "unitCode": "MTK"}} if p.get("m2") else {})}}
    migas = [("Inicio", "/"), (p["municipio"], url_zona(p["municipio"], None, p["grupo"], p["operacion"]))]
    if p["colonia"] and len(comps_col) >= 3:
        migas.append((p["colonia"], zona_url))
    ld_migas = {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": i + 1, "name": n, "item": SITIO + u} for i, (n, u) in enumerate(migas)]}
    h = cabeza(titulo, desc, url_prop(p), fotos[0] if fotos else None,
               f'<script type="application/ld+json">{json.dumps(ld, ensure_ascii=False)}</script><script type="application/ld+json">{json.dumps(ld_migas, ensure_ascii=False)}</script>')
    h += f"""<nav class="migas">{' › '.join(f'<a href="{u}">{E(n)}</a>' for n, u in migas)} › {E(p['eb'])}</nav>
<div class="seo-top"><div><div class="seo-foto">{f'<img src="{E(foto_tam(fotos[0], 1200, 800))}" alt="{E(p["titulo"])}">' if fotos else ''}</div>
{('<div class="seo-mini">' + ''.join(f'<img src="{E(foto_tam(f, 240, 160))}" alt="Foto {i + 2} de {E(p["titulo"])}" loading="lazy">' for i, f in enumerate(fotos[1:9])) + '</div>') if len(fotos) > 1 else ''}</div>
<div><div class="seo-eyebrow">{op.capitalize()} · {E(p['tipo'])} · {E(lugar)}</div><h1>{E(p['titulo'])}</h1>
<div class="seo-precio">{E(precio_txt)} <small style="font-size:1rem;color:#5b6575">{'MXN' if es_mxn(p) else 'USD'}</small></div>
<div class="seo-chips">{''.join(f'<span>{E(x)}</span>' for x in datos)}</div>
<div class="seo-cta"><a class="btn-solid btn-lg" href="{wa}" target="_blank" rel="noopener">Hablar con un asesor por WhatsApp</a>
<a class="btn-outline btn-lg" href="/ficha.html?eb={E(p['eb'])}&amp;op={E(p['operacion'])}">Ver todas las fotos, mapa y simulador</a></div></div></div>
<section class="seo-card"><h2>Descripción</h2><div class="seo-desc">{E(texto)}</div>
{('<h3>Amenidades</h3><div class="seo-chips">' + ''.join(f'<span>{E(str(a).replace("_", " ").capitalize())}</span>' for a in d.get("amenidades", [])) + '</div>') if d.get("amenidades") else ''}</section>
{analisis}
<section class="seo-card"><h2>Antes de comprar o rentar</h2><p>Con <a href="/#verifica">Acierta Verifica</a> revisamos físicamente el inmueble (humedad, instalaciones, gas y estructura) y sus documentos antes de que firmes. Y si quieres conocer más opciones, mira todas las <a href="{zona_url}">{E(PLURAL[p['grupo']].lower())} en {op} en {E(p['colonia'] if p['colonia'] and len(comps_col) >= 3 else p['municipio'])}</a>.</p></section>
{('<section class="seo-card"><h2>Propiedades similares</h2><div class="similares">' + ''.join(tarjeta(s) for s in similares) + '</div></section>') if similares else ''}
"""
    return h + PIE


def pagina_zona(muni, col, g, op, lista, hijos=None):
    opn = "renta" if op == "RENTA" else "venta"
    lugar = f"{col}, {muni}" if col else muni
    st = estadisticas(lista)
    h1 = f"{PLURAL[g]} en {opn} en {lugar}"
    precio_med = dinero(st["mediana"]) + (" al mes" if opn == "renta" else "")
    desc = f"{st['n']} {PLURAL[g].lower()} en {opn} en {lugar}. Precio mediano {precio_med}" + (f", {dinero(st['pm2'])} por m²" if st["pm2"] else "") + ". Fotos, precios y asesoría de Acierta Max."
    canon = url_zona(muni, col, g, op)
    orden = sorted(lista, key=lambda p: (not p.get("foto"), p["precio"]))
    faq = [(f"¿Cuánto cuesta {'rentar' if opn == 'renta' else 'comprar'} {'una' if g in ('casa', 'oficina', 'bodega') else 'un'} {PLURAL[g].lower().rstrip('s').replace('locales comerciale', 'local comercial')} en {lugar}?",
            f"El precio mediano de {PLURAL[g].lower()} en {opn} en {lugar} es de {precio_med}, con un rango de {dinero(st['min'])} a {dinero(st['max'])} entre {st['n']} propiedades publicadas (actualizado {HOY})."),
           (f"¿Cuántas {PLURAL[g].lower()} hay en {opn} en {lugar}?", f"Hoy tenemos {st['n']} {PLURAL[g].lower()} en {opn} en {lugar} en nuestro inventario, que se actualiza cada quincena.")]
    if st["pm2"]:
        faq.append((f"¿Cuál es el precio por m² en {lugar}?", f"La mediana es de {dinero(st['pm2'])} por m² de construcción, con base en {st['n_pm2']} propiedades con superficie publicada."))
    ld = {"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [{"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in faq]}
    h = cabeza(f"{h1} | {st['n']} opciones | Acierta Max", desc, canon, (orden[0].get("foto") if orden else None),
               f'<script type="application/ld+json">{json.dumps(ld, ensure_ascii=False)}</script>')
    migas = [("Inicio", "/"), ("Zonas", "/zonas/")] + ([(muni, url_zona(muni, None, g, op))] if col else [])
    h += f"""<nav class="migas">{' › '.join(f'<a href="{u}">{E(n)}</a>' for n, u in migas)} › {E(col or muni)}</nav>
<h1>{E(h1)}</h1><p class="muted">Inventario actualizado al {HOY} · Acierta Max, profesionales inmobiliarios en Guadalajara</p>
<div class="seo-stats"><div><b>{st['n']}</b><span>{E(PLURAL[g].lower())} en {opn}</span></div><div><b>{E(precio_med)}</b><span>precio mediano</span></div>
{f'<div><b>{dinero(st["pm2"])}</b><span>por m² (mediana)</span></div>' if st['pm2'] else ''}<div><b>{dinero(st['min'])} – {dinero(st['max'])}</b><span>rango de precios</span></div></div>"""
    if hijos:
        h += '<section class="seo-card"><h2>Por colonia</h2><table class="seo-tabla"><tr><th>Colonia</th><th>Propiedades</th><th>Precio mediano</th><th>$ por m²</th></tr>' + "".join(
            f'<tr><td><a href="{url_zona(muni, c, g, op)}">{E(c)}</a></td><td>{s["n"]}</td><td>{dinero(s["mediana"])}</td><td>{dinero(s["pm2"]) if s["pm2"] else "—"}</td></tr>' for c, s in hijos) + "</table></section>"
    h += f'<section class="seo-card"><h2>Propiedades disponibles</h2><div class="similares">{"".join(tarjeta(p) for p in orden[:48])}</div>'
    if len(orden) > 48:
        h += f'<p>Mostramos 48 de {len(orden)}. <a href="/mapa.html">Ver todas en el buscador por zona</a>.</p>'
    h += '</section><section class="seo-card"><h2>Preguntas frecuentes</h2><dl class="seo-faq">' + "".join(f"<dt>{E(q)}</dt><dd>{E(a)}</dd>" for q, a in faq) + "</dl></section>"
    return h + PIE


def escribir(ruta_url, contenido):
    ruta = os.path.join(RAIZ, ruta_url.lstrip("/"))
    if ruta.endswith("/"):
        ruta += "index.html"
    os.makedirs(os.path.dirname(ruta), exist_ok=True)
    with open(ruta, "w", encoding="utf-8") as fh:
        fh.write(contenido)


def main():
    props = cargar()
    with open(os.path.join(RAIZ, "seo.css"), "w", encoding="utf-8") as fh:
        fh.write(CSS_SEO.strip() + "\n")
    for d in ("propiedades", "zonas"):
        shutil.rmtree(os.path.join(RAIZ, d), ignore_errors=True)
    por_muni, por_col = {}, {}
    for p in props:
        por_muni.setdefault((p["municipio"], p["grupo"], p["operacion"]), []).append(p)
        if p["colonia"]:
            por_col.setdefault((p["municipio"], slug(p["colonia"]), p["grupo"], p["operacion"]), []).append(p)
    urls_prop = []
    for p in props:
        cm = por_muni[(p["municipio"], p["grupo"], p["operacion"])]
        cc = por_col.get((p["municipio"], slug(p["colonia"]), p["grupo"], p["operacion"]), []) if p["colonia"] else []
        base = [s for s in (cc if len(cc) >= 4 else cm) if s is not p]
        sim = sorted(base, key=lambda s: abs((s["precio"] or 0) - p["precio"]))[:4]
        escribir(url_prop(p), pagina_prop(p, cm, cc, sim))
        urls_prop.append((url_prop(p), p.get("foto")))
    urls_zona = []
    nombres_col = {}
    for (m, sc, g, op), lista in por_col.items():
        nombres_col[(m, sc)] = max((p["colonia"] for p in lista), key=lambda c: sum(1 for p in lista if p["colonia"] == c))
    for (m, sc, g, op), lista in por_col.items():
        if len(lista) >= 3:
            escribir(url_zona(m, nombres_col[(m, sc)], g, op), pagina_zona(m, nombres_col[(m, sc)], g, op, lista))
            urls_zona.append(url_zona(m, nombres_col[(m, sc)], g, op))
    for (m, g, op), lista in por_muni.items():
        hijos = sorted(((nombres_col[(m, sc)], estadisticas(l)) for (mm, sc, gg, oo), l in por_col.items() if mm == m and gg == g and oo == op and len(l) >= 3),
                       key=lambda x: -x[1]["n"])
        escribir(url_zona(m, None, g, op), pagina_zona(m, None, g, op, lista, hijos))
        urls_zona.append(url_zona(m, None, g, op))
    # índice de zonas
    idx = cabeza("Casas, departamentos, terrenos y locales por zona en Guadalajara | Acierta Max",
                 f"Inventario de {len(props):,} propiedades en venta y renta en la Zona Metropolitana de Guadalajara, por municipio, colonia y tipo.", "/zonas/")
    idx += f"<h1>Propiedades por zona en la Zona Metropolitana de Guadalajara</h1><p class='muted'>{len(props):,} propiedades en venta y renta · actualizado {HOY}</p>"
    for m in sorted({k[0] for k in por_muni}):
        idx += f"<section class='seo-card'><h2>{E(m)}</h2><ul class='seo-links'>" + "".join(
            f"<li><a href='{url_zona(m, None, g, op)}'>{E(PLURAL[g])} en {'renta' if op == 'RENTA' else 'venta'}</a> ({len(por_muni[(m, g, op)])})</li>"
            for (mm, g, op) in sorted(k for k in por_muni if k[0] == m)) + "</ul>"
        cols = sorted({nombres_col[(mm, sc)] for (mm, sc, g, op), l in por_col.items() if mm == m and len(l) >= 3})
        if cols:
            idx += "<h3>Colonias</h3><ul class='seo-links'>" + "".join(
                f"<li><a href='{url_zona(m, c, g, op)}'>{E(c)}: {E(PLURAL[g].lower())} en {'renta' if op == 'RENTA' else 'venta'}</a></li>"
                for (mm, sc, g, op), l in sorted(por_col.items()) if mm == m and len(l) >= 3 for c in [nombres_col[(mm, sc)]]) + "</ul>"
        idx += "</section>"
    escribir("/zonas/", idx + PIE)
    urls_zona.insert(0, "/zonas/")
    # mapas del sitio
    for f in os.listdir(RAIZ):
        if re.match(r"sitemap-(propiedades-\d+|zonas)\.xml$", f):
            os.remove(os.path.join(RAIZ, f))
    def xml_urls(items, img=False):
        filas = []
        for u, foto in items:
            im = f"<image:image><image:loc>{E(foto)}</image:loc></image:image>" if img and foto else ""
            filas.append(f"<url><loc>{SITIO}{E(u)}</loc><lastmod>{HOY}</lastmod>{im}</url>")
        return ('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:image="http://www.google.com/schemas/sitemap-image/1.1">\n'
                + "\n".join(filas) + "\n</urlset>\n")
    mapas = []
    for i in range(0, len(urls_prop), 40000):
        n = i // 40000 + 1
        with open(os.path.join(RAIZ, f"sitemap-propiedades-{n}.xml"), "w", encoding="utf-8") as fh:
            fh.write(xml_urls(urls_prop[i:i + 40000], img=True))
        mapas.append(f"sitemap-propiedades-{n}.xml")
    with open(os.path.join(RAIZ, "sitemap-zonas.xml"), "w", encoding="utf-8") as fh:
        fh.write(xml_urls([(u, None) for u in urls_zona]))
    mapas.append("sitemap-zonas.xml")
    rob = os.path.join(RAIZ, "robots.txt")
    with open(rob, encoding="utf-8") as fh:
        r = [ln for ln in fh.read().splitlines() if not re.match(r"Sitemap: .*/sitemap-(propiedades-\d+|zonas)\.xml", ln)]
    while r and not r[-1].strip():
        r.pop()
    r += [f"Sitemap: {SITIO}/{m}" for m in mapas]
    with open(rob, "w", encoding="utf-8") as fh:
        fh.write("\n".join(r) + "\n")
    print(f"Páginas para buscadores: {len(urls_prop):,} propiedades · {len(urls_zona):,} de zonas · mapas: {', '.join(mapas)}", flush=True)


if __name__ == "__main__":
    main()

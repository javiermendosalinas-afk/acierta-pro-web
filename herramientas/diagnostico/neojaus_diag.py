"""Diagnóstico de la estructura pública de neojaus.com (solo lectura, lento).
Escribe reportes/diagnostico/neojaus.md SIN datos personales (no guarda teléfonos ni correos)."""
import os, re, json, time
import requests

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
H = {"User-Agent": "Mozilla/5.0 (compatible; AciertaMaxInventarioBot/2.0; +https://acierta.pro)"}
s = requests.Session()
out = ["# Diagnóstico de neojaus.com", ""]

def get(url, pausa=4):
    try:
        r = s.get(url, headers=H, timeout=30)
        time.sleep(pausa)
        return r
    except Exception as e:
        out.append(f"- error en {url}: {e}")
        return None

def sin_datos_personales(t):
    t = re.sub(r"[\w.+-]+@[\w-]+\.[\w.]+", "[correo]", t)
    return re.sub(r"\+?\d[\d\s\-()]{8,}\d", "[tel]", t)

# 1) robots y sitemaps
r = get("https://neojaus.com/robots.txt")
out += ["## robots.txt", "```", (r.text[:3000] if r is not None else "error"), "```", ""]
sitemaps = re.findall(r"(?im)^sitemap:\s*(\S+)", r.text if r is not None else "") or ["https://neojaus.com/sitemap.xml"]
out.append("## Sitemaps")
urls_prop = []
for sm in sitemaps[:5]:
    r = get(sm)
    if r is None: continue
    locs = re.findall(r"<loc>([^<]+)</loc>", r.text)
    out.append(f"- {sm}: HTTP {r.status_code}, {len(locs)} <loc>; ejemplos: {locs[:5]}")
    for sub in [l for l in locs if l.endswith(".xml")][:6]:
        r2 = get(sub)
        if r2 is None: continue
        l2 = re.findall(r"<loc>([^<]+)</loc>", r2.text)
        props = [u for u in l2 if "/propiedades/" in u]
        urls_prop += props
        out.append(f"  - {sub}: {len(l2)} <loc>, con /propiedades/: {len(props)}; ejemplos: {l2[:3]}")
    urls_prop += [l for l in locs if "/propiedades/" in l]
out.append(f"- Total de fichas encontradas en sitemaps (muestra): {len(urls_prop)}")

# 2) páginas de búsqueda candidatas
out += ["", "## Búsqueda"]
for u in ("https://neojaus.com/propiedades", "https://neojaus.com/propiedades/venta/jalisco/zapopan",
          "https://neojaus.com/inmuebles/venta/jalisco/zapopan", "https://neojaus.com/buscar?q=zapopan",
          "https://neojaus.com/propiedades?estado=jalisco&municipio=zapopan"):
    r = get(u)
    if r is None: continue
    links = sorted(set(re.findall(r'href="(/propiedades/[^"#?]+)"', r.text)))
    datos = "__NEXT_DATA__" in r.text or "window.__NUXT__" in r.text or "application/ld+json" in r.text
    apis = sorted(set(re.findall(r'https://api\.neojaus\.com/[^"\'\s<>]+', r.text)))[:8]
    out.append(f"- {u}: HTTP {r.status_code}, {len(links)} ligas a fichas, json embebido: {datos}, apis vistas: {apis}")

# 3) tres fichas de muestra: qué campos trae
out += ["", "## Fichas de muestra (texto sin datos personales)"]
for u in urls_prop[:3]:
    r = get(u)
    if r is None: continue
    html = r.text
    txt = re.sub(r"<script.*?</script>|<style.*?</style>", " ", html, flags=re.S)
    txt = re.sub(r"<[^>]+>", "\n", txt); txt = re.sub(r"\n\s*\n+", "\n", txt)
    claves = {k: (k.lower() in html.lower()) for k in ("AMPI Guadalajara", "comparte comisión", "comisión compartida", "share_commission", "latitude", "lat", "application/ld+json", "cdn.neojaus.com/properties")}
    out.append(f"### {u}")
    out.append(f"- HTTP {r.status_code}; contiene: {claves}")
    out.append("```"); out.append(sin_datos_personales(txt[:2500])); out.append("```")

os.makedirs(os.path.join(RAIZ, "reportes", "diagnostico"), exist_ok=True)
open(os.path.join(RAIZ, "reportes", "diagnostico", "neojaus.md"), "w", encoding="utf-8").write("\n".join(out) + "\n")
print("\n".join(out)[:4000])

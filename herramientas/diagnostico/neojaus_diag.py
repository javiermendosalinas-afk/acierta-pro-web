"""Diagnóstico 2 de neojaus.com: lee los sitemaps de propiedades, cuenta las de los 5
municipios de la ZMG y analiza 4 fichas (campos disponibles). Sin datos personales."""
import os, re, json, time, collections
import requests

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
H = {"User-Agent": "Mozilla/5.0 (compatible; AciertaMaxInventarioBot/2.0; +https://acierta.pro)"}
s = requests.Session()
out = ["# Diagnóstico 2 de neojaus.com", ""]
MUNIS = ("zapopan", "guadalajara", "tlaquepaque", "tonala", "tlajomulco")

def get(url, pausa=3):
    try:
        r = s.get(url, headers=H, timeout=40); time.sleep(pausa); return r
    except Exception as e:
        out.append(f"- error {url}: {e}"); return None

def limpio(t):
    t = re.sub(r"[\w.+-]+@[\w-]+\.[\w.]+", "[correo]", t)
    return re.sub(r"\+?\d[\d\s\-()]{8,}\d", "[tel]", t)

urls = []
for i in (1, 2, 3):
    r = get(f"https://cdn.neojaus.com/sitemaps/all-properties/sitemap-{i}.xml")
    if r is None or r.status_code != 200:
        out.append(f"- sitemap-{i}: HTTP {getattr(r,'status_code','error')}"); continue
    locs = re.findall(r"<loc>([^<]+)</loc>", r.text)
    lastmod = re.findall(r"<lastmod>([^<]+)</lastmod>", r.text)
    out.append(f"- sitemap-{i}: {len(locs)} fichas; lastmod ejemplos: {lastmod[:2]}; ejemplos: {locs[:3]}")
    urls += locs
out.append(f"- TOTAL fichas en sitemaps: {len(urls)}")
cont = collections.Counter(m for u in urls for m in MUNIS if m in u.lower())
out.append(f"- Con municipio de la ZMG en la URL: {dict(cont)} (total {sum(cont.values())})")
jal = sum(1 for u in urls if "jalisco" in u.lower())
out.append(f"- Con 'jalisco' en la URL: {jal}")

# Página de listado: tipo de JSON embebido
r = get("https://neojaus.com/propiedades")
if r is not None:
    m = re.search(r'<script[^>]+application/ld\+json[^>]*>(.*?)</script>', r.text, re.S)
    out.append(f"- /propiedades ld+json: {(m.group(1)[:600] if m else 'no')}")
    nxt = re.search(r'id="__NEXT_DATA__"[^>]*>(.*?)</script>', r.text, re.S)
    out.append(f"- /propiedades __NEXT_DATA__: {'sí, ' + str(len(nxt.group(1))) + ' caracteres' if nxt else 'no'}")
    out.append(f"- paginación vista: {sorted(set(re.findall(r'[?&]page=(\\d+)', r.text)))[:10]}")

# Fichas de muestra de la ZMG
muestra = [u for u in urls if any(m in u.lower() for m in MUNIS)][:4] or urls[:4]
out += ["", "## Fichas de muestra"]
for u in muestra:
    r = get(u)
    if r is None: continue
    h = r.text
    ld = re.findall(r'<script[^>]+application/ld\+json[^>]*>(.*?)</script>', h, re.S)
    nxt = re.search(r'id="__NEXT_DATA__"[^>]*>(.*?)</script>', h, re.S)
    claves = {k: (k.lower() in h.lower()) for k in ("AMPI Guadalajara", "comisión", "share_commission", "shared_commission", "latitude", "\"lat\"", "geo", "Agencia ", "cdn.neojaus.com/properties", "no está disponible")}
    out.append(f"### {u}\n- HTTP {r.status_code}; contiene: {claves}")
    for b in ld[:2]:
        out.append("- ld+json: `" + limpio(re.sub(r"\s+", " ", b))[:900] + "`")
    if nxt:
        out.append("- __NEXT_DATA__ (inicio): `" + limpio(nxt.group(1))[:900] + "`")
    txt = re.sub(r"<script.*?</script>|<style.*?</style>", " ", h, flags=re.S)
    txt = re.sub(r"<[^>]+>", "\n", txt); txt = re.sub(r"\n\s*\n+", "\n", txt)
    i = txt.find("Contacta"); out.append("```\n" + limpio(txt[max(0, i - 900): i + 600]) + "\n```")

os.makedirs(os.path.join(RAIZ, "reportes", "diagnostico"), exist_ok=True)
open(os.path.join(RAIZ, "reportes", "diagnostico", "neojaus.md"), "w", encoding="utf-8").write("\n".join(out) + "\n")
print("\n".join(out)[:3000])

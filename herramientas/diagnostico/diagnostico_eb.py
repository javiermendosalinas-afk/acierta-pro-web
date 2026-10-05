"""Diagnóstico: ¿por qué unas claves EB de EasyBroker no llegan al inventario?

Corre en GitHub Actions (allí sí se puede abrir aciertamax.com). Escribe
reportes/diagnostico/resultado.md. Uso: python diagnostico_eb.py EB-XXXX EB-YYYY ...
"""
import os, re, sys, json, time, importlib.util
import requests
from bs4 import BeautifulSoup

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
spec = importlib.util.spec_from_file_location("S", os.path.join(RAIZ, "herramientas", "inventario_sync.py"))
S = importlib.util.module_from_spec(spec); spec.loader.exec_module(S)
BASE = S.BASE
EBS = [e.upper() for e in sys.argv[1:]] or ["EB-XB4792"]
ses = requests.Session()
out = ["# Diagnóstico de claves EB faltantes", "", f"Claves: {', '.join(EBS)}", ""]

def get(url):
    try:
        r = ses.get(url, headers=S.HEADERS, timeout=25, allow_redirects=True)
        return r
    except Exception as e:
        return None

# 1) Formas de búsqueda por clave
out += ["## 1. Búsqueda directa por clave", ""]
for eb in EBS:
    for url in (f"{BASE}/search?q={eb}", f"{BASE}/search_text?search_text={eb}",
                f"{BASE}/properties?search%5Bquery%5D={eb}", f"{BASE}/property/{eb.lower()}",
                f"{BASE}/renta?search%5Bquery%5D={eb}"):
        r = get(url)
        if r is None:
            out.append(f"- {url} → error"); continue
        presente = eb in r.text
        tarjetas = S.parsear_tarjetas(r.text) if r.status_code == 200 else []
        out.append(f"- {url} → HTTP {r.status_code}, final {r.url}, clave en página: {presente}, tarjetas: {len(tarjetas)}")
        time.sleep(1)

# 2) Listados de renta: total que declara el sitio vs tarjetas leídas, y si aparecen las claves
out += ["", "## 2. Listados de renta", ""]
for muni in ("zapopan", "guadalajara"):
    for orden in ("price-desc", "price-asc", ""):
        vistos, pagina, total_txt, paginas = set(), 1, "", 0
        while pagina <= 120:
            q = f"?page={pagina}" + (f"&sort_by={orden}" if orden else "") if pagina > 1 else (f"?sort_by={orden}" if orden else "")
            url = f"{BASE}/renta/mexico/jalisco/{muni}{q}"
            r = get(url)
            if r is None or r.status_code != 200:
                break
            if pagina == 1:
                m = re.search(r"([\d,]+)\s+(?:propiedades|resultados|inmuebles)", r.text, re.I)
                total_txt = m.group(0) if m else "(sin texto de total)"
            t = S.parsear_tarjetas(r.text)
            if not t:
                break
            vistos |= {x.get("codigo_eb") for x in t}
            paginas = pagina
            if "Siguiente" not in r.text or f"page={pagina + 1}" not in r.text:
                break
            pagina += 1
            time.sleep(0.8)
        hallados = [eb for eb in EBS if eb in vistos]
        out.append(f"- renta/{muni} orden={orden or 'por defecto'}: {len(vistos)} claves en {paginas} páginas; el sitio dice: {total_txt}; de las buscadas aparecen: {hallados or 'ninguna'}")

# 3) Página principal: enlaces de búsqueda y filtros que usa el sitio
out += ["", "## 3. Formularios y enlaces del sitio", ""]
r = get(BASE + "/")
if r is not None and r.status_code == 200:
    soup = BeautifulSoup(r.text, "html.parser")
    for f in soup.find_all("form")[:6]:
        campos = [i.get("name") for i in f.find_all(["input", "select"]) if i.get("name")]
        out.append(f"- form action={f.get('action')} method={f.get('method')} campos={campos[:15]}")
    rutas = sorted({a.get("href").split("?")[0] for a in soup.find_all("a", href=True) if a.get("href", "").startswith("/")})[:60]
    out.append(f"- rutas: {rutas}")
# 4) Listado de renta: qué filtros/paginación muestra
r = get(f"{BASE}/renta/mexico/jalisco/zapopan")
if r is not None and r.status_code == 200:
    soup = BeautifulSoup(r.text, "html.parser")
    sel = soup.select("select option")
    out.append(f"- opciones de orden/filtro en listado: {[o.get('value') for o in sel][:40]}")
    txt = re.sub(r"\s+", " ", soup.get_text(" "))
    i = txt.lower().find("propiedades")
    out.append(f"- texto cerca de 'propiedades': {txt[max(0,i-120):i+120]}")

os.makedirs(os.path.join(RAIZ, "reportes", "diagnostico"), exist_ok=True)
open(os.path.join(RAIZ, "reportes", "diagnostico", "resultado.md"), "w", encoding="utf-8").write("\n".join(out) + "\n")
print("\n".join(out))

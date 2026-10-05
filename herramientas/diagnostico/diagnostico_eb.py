"""Diagnóstico 2 (lento, para no recibir HTTP 429): busca cada clave EB en
aciertamax.com con /properties?search[query]=, muestra su tarjeta y compara los
listados /rentals y /renta/mexico/jalisco/<municipio>. Escribe reportes/diagnostico/resultado.md."""
import os, re, sys, time, importlib.util
import requests

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
spec = importlib.util.spec_from_file_location("S", os.path.join(RAIZ, "herramientas", "inventario_sync.py"))
S = importlib.util.module_from_spec(spec); spec.loader.exec_module(S)
BASE, EBS = S.BASE, [e.upper() for e in sys.argv[1:]]
ses = requests.Session()
out = ["# Diagnóstico 2 de claves EB", ""]

def get(url, pausa=6):
    for intento in range(4):
        try:
            r = ses.get(url, headers=S.HEADERS, timeout=30)
            if r.status_code == 429:
                time.sleep(30 * (intento + 1)); continue
            time.sleep(pausa)
            return r
        except Exception:
            time.sleep(10)
    return None

def total(html):
    m = re.search(r"([\d,\.]+)\s*(propiedades|resultados|inmuebles)", html or "", re.I)
    return m.group(0) if m else "(sin total visible)"

out += ["## Búsqueda por clave (/properties?search[query]=)", ""]
for eb in EBS:
    r = get(f"{BASE}/properties?search%5Bquery%5D={eb}")
    if r is None or r.status_code != 200:
        out.append(f"- {eb}: HTTP {getattr(r, 'status_code', 'error')}"); continue
    t = S.parsear_tarjetas(r.text)
    match = [x for x in t if x.get("codigo_eb") == eb]
    i = r.text.find(eb)
    contexto = re.sub(r"\s+", " ", r.text[max(0, i - 300):i + 120]) if i >= 0 else ""
    if match:
        x = match[0]
        out.append(f"- {eb}: tarjeta encontrada · tipo={x['tipo']} · colonia={x['colonia']} · municipio_tarjeta={x['municipio_tarjeta']} · precio={x['precio']} · href={x['href']} · lat={x['lat']}")
    else:
        out.append(f"- {eb}: la clave está en la página pero ninguna tarjeta la trae como código ({len(t)} tarjetas: {[y.get('codigo_eb') for y in t][:5]}). Contexto: `{contexto[:400]}`")

out += ["", "## Totales de listados", ""]
for url in (f"{BASE}/rentals", f"{BASE}/properties", f"{BASE}/renta/mexico/jalisco/zapopan", f"{BASE}/renta/mexico/jalisco/guadalajara"):
    r = get(url)
    if r is None:
        out.append(f"- {url}: error"); continue
    t = S.parsear_tarjetas(r.text)
    sig = re.findall(r'href="([^"]*page=2[^"]*)"', r.text)[:1]
    out.append(f"- {url}: HTTP {r.status_code} · {total(r.text)} · tarjetas pág. 1: {len(t)} · enlace a pág. 2: {sig}")

os.makedirs(os.path.join(RAIZ, "reportes", "diagnostico"), exist_ok=True)
open(os.path.join(RAIZ, "reportes", "diagnostico", "resultado.md"), "w", encoding="utf-8").write("\n".join(out) + "\n")
print("\n".join(out))

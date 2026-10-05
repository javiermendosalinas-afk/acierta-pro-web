"""Diagnóstico 3 de neojaus.com: estructura del bloque __NEXT_DATA__ de 3 fichas de la ZMG
(nombres de campos y valores no personales). Sin teléfonos, correos ni nombres de asesores."""
import os, re, json, time
import requests

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
H = {"User-Agent": "Mozilla/5.0 (compatible; AciertaMaxInventarioBot/2.0; +https://acierta.pro)"}
s = requests.Session()
out = ["# Diagnóstico 3 de neojaus.com: estructura de datos de la ficha", ""]
PERSONALES = re.compile(r"phone|tel|mobile|whats|email|correo|first_name|last_name|full_name|^name$|curp|rfc", re.I)

def get(url, pausa=3):
    r = s.get(url, headers=H, timeout=40); time.sleep(pausa); return r

def esquema(o, ruta="", prof=0, filas=None):
    filas = [] if filas is None else filas
    if prof > 5: return filas
    if isinstance(o, dict):
        for k, v in o.items():
            r = f"{ruta}.{k}" if ruta else k
            if isinstance(v, (dict, list)):
                filas.append(f"{r}: {type(v).__name__}({len(v)})")
                esquema(v[0] if isinstance(v, list) and v else v, r + ("[0]" if isinstance(v, list) else ""), prof + 1, filas)
            else:
                val = "«oculto»" if PERSONALES.search(k) else repr(v)[:70]
                filas.append(f"{r} = {val}")
    return filas

r = get("https://cdn.neojaus.com/sitemaps/all-properties/sitemap-1.xml")
urls = [u for u in re.findall(r"<loc>([^<]+)</loc>", r.text) if re.search(r"zapopan|guadalajara", u, re.I)]
for u in [urls[0], urls[7], urls[25]]:
    h = get(u).text
    m = re.search(r'id="__NEXT_DATA__"[^>]*>(.*?)</script>', h, re.S)
    if not m: out.append(f"- {u}: sin __NEXT_DATA__"); continue
    d = json.loads(m.group(1))
    pp = d.get("props", {}).get("pageProps", {})
    out.append(f"## {u}")
    out.append(f"- claves de pageProps: {list(pp.keys())}")
    out.append("```")
    out += esquema(pp)[:260]
    out.append("```")

os.makedirs(os.path.join(RAIZ, "reportes", "diagnostico"), exist_ok=True)
open(os.path.join(RAIZ, "reportes", "diagnostico", "neojaus.md"), "w", encoding="utf-8").write("\n".join(out) + "\n")
print("\n".join(out)[:2000])

"""Muestra (solo nombres de campos y nombres comerciales, sin teléfonos ni correos) de qué datos del anunciante
trae la página pública de una propiedad de NeoJaus, para guardar el originador al descargar el inventario."""
import json, re, requests
nj = json.load(open("herramientas/neojaus/neojaus.json", encoding="utf-8"))
urls = [r["url_fuente"] for r in nj if r.get("url_fuente")][:4]
H = {"User-Agent": "Mozilla/5.0 (compatible; AciertaMaxBot/1.0)"}
SENSIBLE = re.compile(r"phone|tel|mail|whats|celular|movil|mobile|email", re.I)
def resumen(o, prof=0):
    if isinstance(o, dict):
        return {k: ("[omitido]" if SENSIBLE.search(k) else resumen(v, prof + 1)) for k, v in list(o.items())[:60]} if prof < 3 else "{…}"
    if isinstance(o, list):
        return [resumen(o[0], prof + 1)] if o else []
    s = str(o)
    return s[:60]
out = []
for u in urls:
    r = requests.get(u, headers=H, timeout=30)
    m = re.search(r'id="__NEXT_DATA__"[^>]*>(.*?)</script>', r.text, re.S)
    pp = json.loads(m.group(1))["props"]["pageProps"] if m else {}
    otros = {k: resumen(v) for k, v in pp.items() if k != "property"}
    prop = pp.get("property") or {}
    candidatos = {k: resumen(v) for k, v in prop.items() if re.search(r"agen|agency|company|office|owner|user|broker|real_?estate|inmob|organization|publisher|account", k, re.I)}
    out.append({"url": u, "pageProps_otros": otros, "property_anunciante": candidatos})
json.dump(out, open("herramientas/neojaus/muestra_originador.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("ok")

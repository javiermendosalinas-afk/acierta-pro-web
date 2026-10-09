"""Guarda la estructura de 3 fichas de NeoJaus (campos y ejemplos) para diseñar la ficha completa."""
import json, re, requests
nj = json.load(open("herramientas/neojaus/neojaus.json", encoding="utf-8"))
urls = [r["url_fuente"] for r in nj if r.get("url_fuente")][:3]
H = {"User-Agent": "Mozilla/5.0 (compatible; AciertaMaxBot/1.0)"}
out = []
for u in urls:
    r = requests.get(u, headers=H, timeout=30)
    m = re.search(r'id="__NEXT_DATA__"[^>]*>(.*?)</script>', r.text, re.S)
    p = json.loads(m.group(1))["props"]["pageProps"]["property"] if m else {}
    def corto(v):
        s = json.dumps(v, ensure_ascii=False)
        return v if len(s) < 400 else s[:400] + "…"
    out.append({"url": u, "campos": {k: corto(v) for k, v in (p or {}).items()}})
json.dump(out, open("herramientas/neojaus/muestra_ficha.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("ok", [len(x["campos"]) for x in out])

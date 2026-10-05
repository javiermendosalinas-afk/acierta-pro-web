"""Pruebas del lector de NeoJaus con fichas simuladas (sin internet)."""
import os, sys, json, gzip, shutil, tempfile, importlib.util, contextlib, io
RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
fallas = 0
def ok(c, m):
    global fallas
    print(("OK    " if c else "FALLA ") + m)
    fallas += 0 if c else 1

tmp = tempfile.mkdtemp()
for d in ("herramientas", "herramientas/pruebas"):
    os.makedirs(os.path.join(tmp, d), exist_ok=True)
shutil.copy(os.path.join(RAIZ, "herramientas", "inventario_sync.py"), os.path.join(tmp, "herramientas"))
shutil.copy(os.path.join(RAIZ, "herramientas", "neojaus_sync.py"), os.path.join(tmp, "herramientas"))
eb = [{"municipio": "Zapopan", "operacion": "VENTA", "precio": 5000000.0, "titulo": "Casa EB", "tipo": "casa", "recamaras": 3,
       "banos": 2, "m2": 200.0, "niveles": None, "eb": "EB-AAA111", "liga": "https://www.aciertamax.com/property/x",
       "foto": "https://x/f.jpg", "lat": 20.70, "lon": -103.40, "colonia": "Virreyes", "segmento": "vivienda"},
      {"municipio": "Guadalajara", "operacion": "RENTA", "precio": 20000.0, "titulo": "Viejo NJ", "tipo": "casa", "eb": "NJ-OLD",
       "fuente": "neojaus", "liga": "x", "foto": "y", "lat": 1, "lon": 1, "colonia": "", "segmento": "vivienda", "m2": 100.0}]
json.dump(eb, open(os.path.join(tmp, "data.json"), "w"))

def ficha(nj, municipio="Zapopan", comparte=True, activo=True, estado="jalisco", venta=None, renta=None, lat=20.75, lon=-103.45,
          titulo_og="Casa en venta en Virreyes, Zapopan.", tipo_clave="house", base="valor_total", area=180, fotos=True, terreno=250):
    prop = {"is_active": activo, "uid": "u" + nj, "nj_uid": nj, "name": "Casa bonita " + nj, "property_type": tipo_clave,
            "rooms": 3, "bathrooms": 2, "floors": 2, "construction_area": area, "land": {"area": terreno, "unit": "m2"},
            "exclusivity": {"shared_commission": comparte}, "ordered_images": ([{"order": 0, "url": "a.webp"}] if fotos else []),
            "location": {"mexican_state": estado, "municipality": municipio, "neighborhood": "Virreyes", "coords": {"lat": lat, "lng": lon}},
            "pricing": {"sales": ({"price": venta, "based_on": base, "currency_type": "mxn"} if venta else None),
                        "rents": ({"price": renta, "based_on": "valor_total", "currency_type": "mxn"} if renta else None)}}
    nd = json.dumps({"props": {"pageProps": {"property": prop}}})
    return f'<html><head><meta property="og:title" content="{titulo_og}"></head><body><script id="__NEXT_DATA__" type="application/json">{nd}</script></body></html>'

paginas = {
    "https://neojaus.com/propiedades/casa-zapopan-1": ficha("10A01", venta=4200000),
    "https://neojaus.com/propiedades/casa-gdl-dice-pero-zapopan-2": ficha("10A02", venta=3000000, renta=25000),
    "https://neojaus.com/propiedades/duplicada-de-eb-3": ficha("10A03", venta=5050000, lat=20.7002, lon=-103.4002),
    "https://neojaus.com/propiedades/no-comparte-4": ficha("10A04", venta=2000000, comparte=False),
    "https://neojaus.com/propiedades/cancun-5": ficha("10A05", venta=2000000, estado="quintana_roo", municipio="Benito Juárez"),
    "https://neojaus.com/propiedades/inactiva-6": ficha("10A06", venta=2000000, activo=False),
    "https://neojaus.com/propiedades/terreno-por-m2-7": ficha("10A07", venta=3000, base="m2", area=None, terreno=None, titulo_og="Terreno en venta en El Bajío, Zapopan.", tipo_clave="land"),
    "https://neojaus.com/propiedades/terreno-por-m2-10": ficha("10A10", venta=3000, base="m2", area=None, terreno=250, lat=20.80, titulo_og="Terreno en venta en El Bajío, Zapopan.", tipo_clave="land"),
    "https://neojaus.com/propiedades/sin-foto-8": ficha("10A08", venta=2500000, fotos=False),
    "https://neojaus.com/propiedades/tlajomulco-9": ficha("10A09", renta=12000, municipio="Tlajomulco de Zúñiga", titulo_og="Departamento en renta en Santa Fe, Tlajomulco."),
}
sitemap = "<urlset>" + "".join(f"<url><loc>{u}</loc><lastmod>2026-10-01</lastmod></url>" for u in paginas) + "".join(
    f"<url><loc>https://neojaus.com/propiedades/relleno-{i}</loc><lastmod>2026-10-01</lastmod></url>" for i in range(1200)) + "</urlset>"

class R:
    def __init__(s, code, text=""): s.status_code, s.text = code, text

llamadas = []
def get_falso(url, timeout=40):
    llamadas.append(url)
    if "sitemap-1.xml" in url: return R(200, sitemap)
    if "sitemap-" in url: return R(403)
    if url in paginas: return R(200, paginas[url])
    if "relleno" in url: return R(200, ficha("R" + url[-4:].replace("-", ""), venta=1000000, estado="nuevo_leon", municipio="Monterrey"))
    return R(404)

os.chdir(tmp)
spec = importlib.util.spec_from_file_location("N", os.path.join(tmp, "herramientas", "neojaus_sync.py"))
N = importlib.util.module_from_spec(spec); spec.loader.exec_module(N)
N.get = get_falso; N.PAUSA = 0
sys.argv = ["neojaus_sync.py"]
with contextlib.redirect_stdout(io.StringIO()):
    N.main()
data = json.load(open(os.path.join(tmp, "data.json")))
nj = {(d["eb"], d["operacion"]): d for d in data if d.get("fuente") == "neojaus"}
ok(("NJ-10A01", "VENTA") in nj, "entra una casa de Zapopan activa que comparte comisión")
ok(("NJ-10A02", "VENTA") in nj and ("NJ-10A02", "RENTA") in nj, "una ficha en venta y renta genera dos registros")
ok(("NJ-10A03", "VENTA") not in nj, "no se repite la ficha que ya está en EasyBroker (a <80 m y precio ±3%)")
gem = [d for d in data if d["eb"] == "EB-AAA111"][0]
ok(gem.get("tambien_en") == [{"clave": "NJ-10A03", "url": "https://neojaus.com/propiedades/duplicada-de-eb-3"}], "pero la ficha de EasyBroker guarda la clave NJ y su liga para hallar al originador")
ok(("NJ-10A04", "VENTA") in nj, "entra aunque la ficha no marque comisión compartida (NeoJaus es para compartir)")
ok(("NJ-10A05", "VENTA") not in nj, "no entra la de otro estado")
ok(("NJ-10A06", "VENTA") not in nj, "no entra la inactiva")
ok(("NJ-10A07", "VENTA") not in nj, "precio por m² sin superficie: no se publica (no se inventa el total)")
ok(("NJ-10A08", "VENTA") not in nj, "sin foto no se publica")
tr = nj.get(("NJ-10A10", "VENTA"), {})
ok(tr.get("precio") == 750000 and tr.get("tipo") == "terreno", "precio por m² con superficie de terreno: se calcula el total ($3,000 × 250 m²)")
t = nj.get(("NJ-10A09", "RENTA"), {})
ok(t.get("municipio") == "Tlajomulco de Zúñiga" and t.get("tipo") == "departamento", "municipio y tipo correctos (Tlajomulco, departamento)")
c = nj.get(("NJ-10A01", "VENTA"), {})
ok(c.get("liga", "").startswith("https://acierta.pro/ficha.html?eb=NJ-10A01") and "neojaus" in c.get("url_fuente", ""), "la liga pública es la ficha de acierta.pro (no la de la otra inmobiliaria)")
ok(c.get("foto") == "https://cdn.neojaus.com/properties/u10A01/a.webp", "foto del CDN de NeoJaus")
ok(not any(k.startswith("_") for d in data for k in d), "no se filtran campos internos al sitio")
ok(any(d["eb"] == "EB-AAA111" for d in data) and not any(d["eb"] == "NJ-OLD" for d in data), "conserva EasyBroker y reemplaza las NJ anteriores")
meta = json.load(open(os.path.join(tmp, "inventario-meta.json")))
ok(meta.get("por_fuente", {}).get("neojaus") == len(nj) and meta["por_fuente"]["easybroker"] == 1, "inventario-meta registra las fuentes")
cache = json.load(gzip.open(os.path.join(tmp, "herramientas", "neojaus", "cache.json.gz"), "rt"))
ok(len(cache) == len(paginas) + 1200, "la caché guarda el estado de cada ficha revisada")
# segunda corrida: no vuelve a abrir fichas sin cambios
llamadas.clear()
with contextlib.redirect_stdout(io.StringIO()):
    N.main()
ok(not [u for u in llamadas if "/propiedades/" in u], "la segunda corrida no vuelve a abrir fichas sin cambios (solo lee el sitemap)")
data2 = json.load(open(os.path.join(tmp, "data.json")))
ok(len([d for d in data2 if d.get("fuente") == "neojaus"]) == len(nj), "y conserva las mismas fichas de NeoJaus")
ok(len([d for d in data2 if d["eb"] == "EB-AAA111"][0].get("tambien_en", [])) == 1, "la clave relacionada no se duplica entre corridas")
# una caché de la versión anterior (filtro de comisión) se vuelve a revisar
c = json.load(gzip.open(os.path.join(tmp, "herramientas", "neojaus", "cache.json.gz"), "rt"))
for v in c.values():
    if v["estado"] == "fuera": v.pop("v", None)
with gzip.open(os.path.join(tmp, "herramientas", "neojaus", "cache.json.gz"), "wt") as fh: json.dump(c, fh)
llamadas.clear()
with contextlib.redirect_stdout(io.StringIO()):
    N.main()
ok(len([u for u in llamadas if "/propiedades/" in u]) == sum(1 for v in c.values() if v["estado"] == "fuera"), "las fichas descartadas con el filtro anterior se vuelven a revisar una vez")
shutil.rmtree(tmp)
print(f"\nFALLAS: {fallas}")
sys.exit(1 if fallas else 0)

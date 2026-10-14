"""Inventario comercial unificado (locales, oficinas, bodegas y naves) de EasyBroker (acierta.pro) y bolsa NeoJaus (inmobiliaria.pro),
para Guadalajara, Zapopan, Tlaquepaque, Tlajomulco y Tonalá. Sin duplicados. Lo usan acierta.pro, inmobiliaria.pro y losprofesionalesinmobiliarios.com."""
import json, os, re, urllib.request
MUN = {"Guadalajara", "Zapopan", "Tlaquepaque", "Tlajomulco de Zúñiga", "Tonalá"}
def tipo(t):
    t = str(t or "").lower()
    if "centro comercial" in t: return "cc"
    if "local" in t: return "local"
    if "oficina" in t or "consultorio" in t: return "oficina"
    if "nave" in t or "bodega industrial" in t: return "nave"
    if "bodega" in t: return "bodega"
    return None
def n(v):
    try: return float(v)
    except Exception: return 0
def cargar(fuente):
    if os.path.exists(fuente): return json.load(open(fuente, encoding="utf-8"))
    return json.loads(urllib.request.urlopen(urllib.request.Request(fuente, headers={"User-Agent": "Mozilla/5.0"}), timeout=90).read())
eb = cargar("data.json")
try:
    nj = cargar(os.environ.get("BOLSA", "https://raw.githubusercontent.com/javiermendosalinas-afk/aciertamax-bolsa/main/data.json"))
except Exception as e:
    print("bolsa no disponible:", e); nj = []
salida, vistos = [], []
def clave(x):
    return (x["o"], round(x["la"], 3) if x["la"] else None, round(x["lo"], 3) if x["lo"] else None)
for origen, datos in (("acierta", eb), ("neojaus", nj)):
    for x in datos:
        t = tipo(x.get("tipo"))
        if not t or x.get("municipio") not in MUN or str(x.get("revisar")) == "True" or n(x.get("precio")) < 1000: continue
        r = {"e": x.get("eb"), "o": "V" if x.get("operacion") == "VENTA" else "R", "p": int(n(x["precio"])), "t": t, "m": int(n(x.get("m2") or x.get("construccion") or x.get("terreno"))) or None,
             "c": str(x.get("colonia") or "")[:40], "u": x["municipio"], "f": x.get("foto") or "", "ti": re.sub(r"\s+", " ", str(x.get("titulo") or ""))[:90],
             "la": n(x.get("lat")) or None, "lo": n(x.get("lon")) or None, "fu": origen,
             "l": f"https://acierta.pro/ficha.html?eb={x.get('eb')}" if origen == "acierta" else (x.get("liga") or "")}
        k = clave(r)
        if k[1] and any(v[0] == k and abs(v[1] - r["p"]) <= 0.03 * r["p"] and (not r["m"] or not v[2] or abs(v[2] - r["m"]) <= 0.08 * r["m"]) for v in vistos):
            continue  # misma propiedad publicada en las dos fuentes: se queda la primera (EasyBroker)
        vistos.append((k, r["p"], r["m"])); salida.append(r)
json.dump(salida, open("comercial.json", "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
import collections
print(len(salida), "propiedades comerciales;", dict(collections.Counter(x["t"] for x in salida)), dict(collections.Counter(x["fu"] for x in salida)), round(os.path.getsize("comercial.json")/1048576, 2), "MB")

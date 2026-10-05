"""Inventario compartido de NeoJaus (bolsa AMPI) -> herramientas/neojaus/neojaus.json.

DECISIÓN DE JAVIER (5-oct-2026): el inventario de NeoJaus NO se publica en acierta.pro;
va a un sitio aparte. Este script solo escribe su propio archivo y, en data.json de
acierta.pro, (1) quita cualquier ficha de NeoJaus y (2) anota en las fichas de EasyBroker
que también están en NeoJaus la clave NJ y su liga (`tambien_en`), solo para que el
portal de coaches encuentre al originador. El archivo de ChatGPT, el CSV y la meta de
acierta.pro se regeneran solo con EasyBroker.

NeoJaus es la bolsa de AMPI, MIO, PAIS y la Cámara de Comercio: todo lo que se publica
ahí es para compartir comisión entre socios (Javier lo confirmó, oct-2026), así que se
toma todo lo que está activo, en Jalisco y en los 5 municipios de la ZMG (según los
datos de la ficha, no la dirección: la dirección a veces dice otro municipio).
La clave NJ- y url_fuente sirven para localizar al originador cuando haya cliente.

Funcionamiento:
  1. Lee el mapa del sitio (sitemap) con todas las fichas y su fecha de modificación.
  2. Abre solo las nuevas o modificadas desde la última vez (caché en
     herramientas/neojaus/cache.json.gz). La primera corrida abre todas; si se acaba el
     tiempo, guarda el avance y la siguiente corrida continúa.
  3. Aplica las mismas reglas que EasyBroker (segmento, guardas de precio, foto).
  4. Marca gemelas con EasyBroker (misma operación, a menos de 80 m y precio a ±3%).
  5. Escribe neojaus.json (todas las de NeoJaus) y deja data.json solo con EasyBroker.

Respeta robots.txt de neojaus.com (solo prohíbe /cdn-cgi/) y va a ritmo pausado.
Uso:  python herramientas/neojaus_sync.py [--max-minutos 300] [--max-fichas N] [--sin-escribir]
"""
import argparse
import concurrent.futures as cf
import gzip
import importlib.util
import json
import math
import os
import re
import sys
import threading
import time
from collections import Counter
from datetime import datetime, timezone

import requests

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(RAIZ)
spec = importlib.util.spec_from_file_location("S", os.path.join(RAIZ, "herramientas", "inventario_sync.py"))
S = importlib.util.module_from_spec(spec)
spec.loader.exec_module(S)

DIR = os.path.join(RAIZ, "herramientas", "neojaus")
RUTA_CACHE = os.path.join(DIR, "cache.json.gz")
RUTA_NJ = os.path.join(DIR, "neojaus.json")            # fichas NJ publicables de la última corrida
SITEMAP = "https://cdn.neojaus.com/sitemaps/all-properties/sitemap-{}.xml"
CDN_FOTOS = "https://cdn.neojaus.com/properties/{uid}/{nombre}"
HEADERS = dict(S.HEADERS)
TRABAJADORES = 3
PAUSA = 0.6            # por trabajador: ~4-5 fichas por segundo en total
DIST_DUPLICADO_M = 80
VERSION_FILTRO = 2      # v2: ya no se exige shared_commission; las 'fuera' de v1 se vuelven a revisar
TOLERANCIA_PRECIO = 0.03

TIPO_POR_CLAVE = {      # respaldo si el título no trae el tipo
    "land": "terreno", "house": "casa", "condo_house": "casa en condominio", "house_in_condo": "casa en condominio",
    "apartment": "departamento", "departamento": "departamento", "local_comercial": "local comercial",
    "local_en_centro_comercial": "local en centro comercial", "office": "oficina", "oficina": "oficina",
    "bodega_comercial": "bodega comercial", "bodega_industrial": "bodega industrial", "warehouse": "bodega comercial",
    "nave_industrial": "nave industrial", "building": "edificio", "edificio": "edificio",
    "terreno_comercial": "terreno comercial", "terreno_industrial": "terreno industrial",
    "quinta": "quinta", "rancho": "rancho", "huerta": "rancho", "villa": "casa", "casa_con_uso_de_suelo": "casa con uso de suelo",
}
TIPOS_VALIDOS = {"casa", "casa en condominio", "departamento", "terreno", "terreno comercial", "terreno industrial",
                 "local comercial", "local en centro comercial", "oficina", "bodega comercial", "bodega industrial",
                 "nave industrial", "edificio", "quinta", "rancho", "casa con uso de suelo", "huerta", "villa"}

_local = threading.local()


def sesion():
    if not hasattr(_local, "s"):
        _local.s = requests.Session()
    return _local.s


def get(url, timeout=40):
    espera = 2
    for _ in range(4):
        try:
            r = sesion().get(url, headers=HEADERS, timeout=timeout)
            if r.status_code == 200:
                return r
            if r.status_code in (404, 410):
                return r
            if r.status_code not in (429, 500, 502, 503, 504):
                return r
        except requests.RequestException:
            pass
        time.sleep(espera)
        espera *= 2
    return None


# ---------------------------------------------------------------- sitemap
def leer_sitemap():
    """{url: lastmod} de todas las fichas publicadas en NeoJaus."""
    urls = {}
    for i in range(1, 30):
        r = get(SITEMAP.format(i))
        if r is None or r.status_code != 200 or "<loc>" not in r.text:
            break
        for bloque in re.findall(r"<url>(.*?)</url>", r.text, re.S):
            loc = re.search(r"<loc>([^<]+)</loc>", bloque)
            lm = re.search(r"<lastmod>([^<]+)</lastmod>", bloque)
            if loc:
                urls[loc.group(1).strip()] = lm.group(1).strip() if lm else ""
    return urls


# ---------------------------------------------------------------- ficha
def _tipo(titulo_og, clave):
    m = re.match(r"\s*(.+?)\s+en\s+(venta|renta|pre[- ]?venta)\b", titulo_og or "", re.I)
    if m:
        t = S.sin_acentos(m.group(1)).lower().strip()
        t = {"casa en condominio": "casa en condominio", "local en centro comercial": "local en centro comercial"}.get(t, t)
        if t in TIPOS_VALIDOS:
            return {"huerta": "rancho", "villa": "casa"}.get(t, t)
    return TIPO_POR_CLAVE.get((clave or "").lower(), "otro")


def leer_ficha(url):
    """Devuelve (estado, registros). estado: 'ok' | 'fuera' | 'error' | 'baja'."""
    r = get(url)
    time.sleep(PAUSA)
    if r is None:
        return "error", []
    if r.status_code in (404, 410):
        return "baja", []
    if r.status_code != 200:
        return "error", []
    m = re.search(r'id="__NEXT_DATA__"[^>]*>(.*?)</script>', r.text, re.S)
    if not m:
        return "error", []
    try:
        p = json.loads(m.group(1))["props"]["pageProps"]["property"]
    except Exception:
        return "error", []
    if not p or not p.get("is_active"):
        return "baja", []
    loc = p.get("location") or {}
    estado = (loc.get("mexican_state") or loc.get("state") or "").lower()
    municipio = S.ALIAS_MUNICIPIO.get(S.sin_acentos(loc.get("municipality") or "").lower()) if loc.get("municipality") else None
    if estado != "jalisco" or not municipio:
        return "fuera", []
    og = re.search(r'<meta[^>]+property="og:title"[^>]+content="([^"]*)"', r.text)
    tipo = _tipo(og.group(1) if og else "", p.get("property_type"))
    imgs = sorted(p.get("ordered_images") or [], key=lambda x: x.get("order") or 0)
    foto = CDN_FOTOS.format(uid=p.get("uid"), nombre=imgs[0]["url"]) if imgs and p.get("uid") else None
    land = p.get("land") or {}
    area_terreno = land.get("area") if (land.get("unit") or "m2") == "m2" else None
    m2 = p.get("construction_area") or area_terreno
    coords = loc.get("coords") or {}
    nj = "NJ-" + str(p.get("nj_uid") or "").upper()
    if nj == "NJ-":
        return "error", []
    regs = []
    for clave_op, operacion in (("sales", "VENTA"), ("rents", "RENTA")):
        pr = (p.get("pricing") or {}).get(clave_op)
        if not pr or not pr.get("price"):
            continue
        precio = float(pr["price"])
        base = (pr.get("based_on") or "valor_total")
        if base == "m2":
            if not m2:
                continue
            precio = round(precio * float(m2), 2)
        elif base == "ha":
            continue
        reg = {
            "municipio": municipio, "operacion": operacion, "precio": precio,
            "titulo": (p.get("name") or "").strip(), "tipo": tipo,
            "recamaras": p.get("rooms") or None, "banos": p.get("bathrooms"),
            "m2": float(m2) if m2 else None, "niveles": p.get("floors"),
            "eb": nj, "liga": None,     # la pone el sitio de la bolsa (no acierta.pro)
            "foto": foto, "lat": coords.get("lat"), "lon": coords.get("lng"),
            "colonia": loc.get("neighborhood") or "", "fuente": "neojaus", "url_fuente": url,
        }
        moneda = (pr.get("currency_type") or "mxn").upper()
        if moneda != "MXN":
            reg["moneda"] = moneda
        regs.append(reg)
    return ("ok" if regs else "fuera"), regs


# ---------------------------------------------------------------- utilidades
def cargar_cache():
    if os.path.exists(RUTA_CACHE):
        with gzip.open(RUTA_CACHE, "rt", encoding="utf-8") as fh:
            return json.load(fh)
    return {}


def guardar_cache(cache):
    os.makedirs(DIR, exist_ok=True)
    tmp = RUTA_CACHE + ".tmp"
    with gzip.open(tmp, "wt", encoding="utf-8") as fh:
        json.dump(cache, fh, ensure_ascii=False, separators=(",", ":"))
    os.replace(tmp, RUTA_CACHE)


def distancia_m(a, b):
    if None in (a.get("lat"), a.get("lon"), b.get("lat"), b.get("lon")):
        return 1e9
    la1, lo1, la2, lo2 = map(math.radians, (a["lat"], a["lon"], b["lat"], b["lon"]))
    h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 6371000 * 2 * math.asin(math.sqrt(h))


def es_duplicado(nj, candidatos):
    for e in candidatos:
        if e["operacion"] != nj["operacion"] or not e.get("precio") or not nj.get("precio"):
            continue
        if abs(e["precio"] - nj["precio"]) / max(e["precio"], nj["precio"]) > TOLERANCIA_PRECIO:
            continue
        if distancia_m(e, nj) <= DIST_DUPLICADO_M:
            return e
    return None


def aplicar_reglas(regs):
    """Mismas reglas que EasyBroker: segmento, m2, guardas de precio y foto obligatoria."""
    publicables, bloqueadas = [], []
    for f in regs:
        f = dict(f)
        f["segmento"], _ = S.clasificar_segmento(f["tipo"], f["titulo"])
        if f.get("banos") is not None and f["banos"] > S.BANOS_MAX_CREIBLE:
            f["banos"] = None
        if f.get("recamaras") is not None and f["recamaras"] > S.RECAMARAS_MAX_CREIBLE:
            f["recamaras"] = None
        aviso_m2 = S.sanear_m2(f)
        nivel, motivo = S.evaluar_precio(f)
        if not f.get("foto"):
            bloqueadas.append((f, "sin foto"))
            continue
        if nivel == "bloquea":
            bloqueadas.append((f, motivo))
            continue
        notas = [x for x in (motivo if nivel == "aviso" else "", (aviso_m2 + " (no mencionar m2)") if aviso_m2 else "") if x]
        if notas:
            f["nota"] = " | ".join(notas)
        if nivel == "aviso" or aviso_m2:
            f["revisar"] = True
        publicables.append({k: v for k, v in f.items() if not k.startswith("_")})
    return publicables, bloqueadas


# ---------------------------------------------------------------- principal
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-minutos", type=float, default=300)
    ap.add_argument("--max-fichas", type=int, default=0, help="limita fichas a revisar (prueba)")
    ap.add_argument("--sin-escribir", action="store_true", help="no toca data.json (prueba)")
    ap.add_argument("--solo-limpiar", action="store_true",
                    help="solo quita de acierta.pro (data.json, CSV, ChatGPT, meta) cualquier ficha de NeoJaus y termina")
    args = ap.parse_args()
    if args.solo_limpiar:
        data = S.cargar_previo(S.RUTA_DATA)
        eb = [d for d in data if d.get("fuente") != "neojaus" and not str(d.get("eb", "")).startswith("NJ-")]
        if len(eb) == len(data):
            print("acierta.pro no tiene fichas de NeoJaus: nada que limpiar")
            return
        with open(S.RUTA_DATA, "w", encoding="utf-8") as fh:
            json.dump(eb, fh, ensure_ascii=False, separators=(",", ":"))
        S.escribir_csv(S.RUTA_CSV, eb)
        S.escribir_chatgpt(eb, datetime.now(timezone.utc).strftime("%Y-%m-%d"))
        meta = json.load(open(S.RUTA_META, encoding="utf-8")) if os.path.exists(S.RUTA_META) else {}
        meta.pop("por_fuente", None)
        meta.update({"total": len(eb), "por_segmento": dict(Counter(f.get("segmento") for f in eb))})
        with open(S.RUTA_META, "w", encoding="utf-8") as fh:
            json.dump(meta, fh, ensure_ascii=False, indent=1)
        print(f"Se quitaron {len(data) - len(eb):,} fichas de NeoJaus de acierta.pro; quedan {len(eb):,} de EasyBroker")
        return
    inicio = time.time()
    ahora = datetime.now(timezone.utc)
    os.makedirs(DIR, exist_ok=True)
    cache = cargar_cache()
    sitemap = leer_sitemap()
    print(f"Sitemap de NeoJaus: {len(sitemap):,} fichas · en caché: {len(cache):,}", flush=True)
    if len(sitemap) < 1000:
        print("[FRENO] El sitemap vino incompleto: se conservan las fichas de NeoJaus de la corrida anterior.")
        sitemap = {}

    pendientes = [u for u, lm in sitemap.items() if u not in cache or cache[u].get("lm") != lm
                  or cache[u].get("estado") == "error"
                  or (cache[u].get("estado") == "fuera" and cache[u].get("v") != VERSION_FILTRO)]
    # primero las que probablemente son de la ZMG (más útiles si el tiempo no alcanza)
    zmg = re.compile(r"zapopan|guadalajara|tlaquepaque|tonala|tlajomulco|jalisco", re.I)
    pendientes.sort(key=lambda u: 0 if zmg.search(u) else 1)
    if args.max_fichas:
        pendientes = pendientes[:args.max_fichas]
    print(f"Fichas por revisar (nuevas o modificadas): {len(pendientes):,}", flush=True)

    revisadas, cont = 0, Counter()
    limite = inicio + args.max_minutos * 60
    with cf.ThreadPoolExecutor(max_workers=TRABAJADORES) as ex:
        futuros = {}
        it = iter(pendientes)
        for u in it:
            futuros[ex.submit(leer_ficha, u)] = u
            if len(futuros) >= TRABAJADORES * 4:
                break
        while futuros:
            hecho = next(cf.as_completed(futuros))
            u = futuros.pop(hecho)
            try:
                estado, regs = hecho.result()
            except Exception:
                estado, regs = "error", []
            cache[u] = {"lm": sitemap.get(u, ""), "estado": estado, "regs": regs, "v": VERSION_FILTRO}
            cont[estado] += 1
            revisadas += 1
            if revisadas % 500 == 0:
                print(f"  {revisadas:,} revisadas · {dict(cont)}", flush=True)
                guardar_cache(cache)
            if time.time() < limite:
                siguiente = next(it, None)
                if siguiente:
                    futuros[ex.submit(leer_ficha, siguiente)] = siguiente
    # fichas que ya no están en el sitemap: fuera
    if sitemap:
        for u in list(cache):
            if u not in sitemap:
                del cache[u]
    guardar_cache(cache)
    faltan = len(pendientes) - revisadas
    print(f"Revisadas en esta corrida: {revisadas:,} {dict(cont)} · pendientes para la siguiente: {faltan:,}", flush=True)

    # registros NJ vigentes (de la caché completa)
    regs = [r for v in cache.values() if v.get("estado") == "ok" for r in v.get("regs", [])]
    if not sitemap and os.path.exists(RUTA_NJ):
        with open(RUTA_NJ, encoding="utf-8") as fh:
            regs = json.load(fh)
    # quitar repetidas dentro de NeoJaus (misma clave y operación)
    vistos, unicos = set(), []
    for r in regs:
        k = (r["eb"], r["operacion"])
        if k not in vistos:
            vistos.add(k)
            unicos.append(r)
    publicables, bloqueadas = aplicar_reglas(unicos)

    # gemelas con EasyBroker (solo se anotan; las de NeoJaus van todas a su propio archivo)
    data = S.cargar_previo(S.RUTA_DATA)
    quitadas_de_acierta = sum(1 for d in data if d.get("fuente") == "neojaus")
    eb = [d for d in data if d.get("fuente") != "neojaus"]
    por_muni = {}
    for e in eb:
        e.pop("tambien_en", None)
        por_muni.setdefault((e["municipio"], e["operacion"]), []).append(e)
    nj_final, dup_eb, dup_nj = [], 0, 0
    nj_por_muni = {}
    for r in publicables:
        gemela_nj = es_duplicado(r, nj_por_muni.get((r["municipio"], r["operacion"]), []))
        if gemela_nj:              # la misma propiedad publicada dos veces dentro de NeoJaus
            dup_nj += 1
            gemela_nj.setdefault("tambien_en", []).append({"clave": r["eb"], "url": r["url_fuente"]})
            continue
        gemela_eb = es_duplicado(r, por_muni.get((r["municipio"], r["operacion"]), []))
        if gemela_eb:
            dup_eb += 1
            gemela_eb.setdefault("tambien_en", []).append({"clave": r["eb"], "url": r["url_fuente"]})
            r = dict(r, tambien_en=[{"clave": gemela_eb["eb"], "url": gemela_eb.get("liga")}])
        nj_por_muni.setdefault((r["municipio"], r["operacion"]), []).append(r)
        nj_final.append(r)

    nj_final.sort(key=lambda f: (f["operacion"], f["municipio"], -(f["precio"] or 0)))
    por_seg = Counter(f.get("segmento") for f in nj_final)
    por_mun = Counter(f["municipio"] for f in nj_final)
    resumen = [
        f"# NeoJaus (bolsa AMPI) - corrida {ahora:%Y-%m-%d}",
        "",
        f"- Fichas en el sitemap de NeoJaus: {len(sitemap):,} · revisadas en esta corrida: {revisadas:,} · pendientes: {faltan:,}",
        f"- Resultado de lo revisado: {dict(cont)} (ok = activa y en la ZMG)",
        f"- Registros activos en la ZMG: {len(unicos):,} · bloqueados por precio o sin foto: {len(bloqueadas):,}",
        f"- Gemelas: {dup_eb:,} también están en EasyBroker (se conservan en la bolsa y se anotan) · {dup_nj:,} repetidas dentro de NeoJaus (se muestra una)",
        f"- **Fichas de la bolsa NeoJaus: {len(nj_final):,}** · por segmento {dict(por_seg)} · por municipio {dict(por_mun)}",
        f"- acierta.pro sigue solo con EasyBroker: {len(eb):,} fichas" + (f" (se quitaron {quitadas_de_acierta:,} fichas de NeoJaus que había)" if quitadas_de_acierta else ""),
    ]
    texto = "\n".join(resumen)
    print("\n" + texto)
    os.makedirs(S.DIR_REPORTES, exist_ok=True)
    with open(os.path.join(S.DIR_REPORTES, "neojaus_resumen.md"), "w", encoding="utf-8") as fh:
        fh.write(texto + "\n")
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as fh:
            fh.write("\n" + texto + "\n")
    if args.sin_escribir:
        return
    with open(RUTA_NJ, "w", encoding="utf-8") as fh:
        json.dump(nj_final, fh, ensure_ascii=False, separators=(",", ":"))
    # acierta.pro: solo EasyBroker (con la anotación tambien_en para el portal de coaches)
    with open(S.RUTA_DATA, "w", encoding="utf-8") as fh:
        json.dump(eb, fh, ensure_ascii=False, separators=(",", ":"))
    if quitadas_de_acierta:
        S.escribir_csv(S.RUTA_CSV, eb)
        S.escribir_chatgpt(eb, ahora.strftime("%Y-%m-%d"))
        meta = {}
        if os.path.exists(S.RUTA_META):
            with open(S.RUTA_META, encoding="utf-8") as fh:
                meta = json.load(fh)
        meta.pop("por_fuente", None)
        meta.update({"total": len(eb), "por_segmento": dict(Counter(f.get("segmento") for f in eb))})
        with open(S.RUTA_META, "w", encoding="utf-8") as fh:
            json.dump(meta, fh, ensure_ascii=False, indent=1)

if __name__ == "__main__":
    main()

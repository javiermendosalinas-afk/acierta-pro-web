#!/usr/bin/env python3
"""
inventario_sync.py - Sincroniza el inventario de aciertamax.com (EasyBroker)
hacia acierta.pro. Es la UNICA fuente de datos del sitio.

QUE HACE
- Recorre aciertamax.com (venta y renta) en Guadalajara, Zapopan, Tlaquepaque,
  Tonala y Tlajomulco de Zuniga. Sin pisos de precio: entra todo.
- Clasifica cada ficha en un SEGMENTO: "vivienda" o "comercial".
- Guardas de precio: lo implausible NO se publica y va a un reporte para
  verificarlo con quien lo capturo; lo dudoso se publica pero se reporta.
- Fotos: toda ficha debe tener foto. Si la tarjeta no la trae se busca en la
  corrida anterior y luego en la pagina de detalle. Si aun asi no hay, no se
  publica y se reporta.
- Frenos de seguridad: si la corrida salio incompleta NO sobreescribe el
  inventario vigente.
- Genera: data.json (sitio), inventario.csv (para ChatGPT/Instagram u otras
  herramientas), inventario-meta.json y reportes en reportes/inventario/.

COMO CORRERLO
    python3 herramientas/inventario_sync.py                  # corrida completa
    python3 herramientas/inventario_sync.py --paginas-max 2 --sin-escribir   # prueba rapida
"""

import argparse
import csv
import json
import os
import re
import sys
import time
import unicodedata
from collections import Counter
from datetime import datetime, timezone

import requests
from bs4 import BeautifulSoup

# ----------------------------------------------------------------------
# CONFIGURACION (lo que se puede ajustar sin tocar la logica)
# ----------------------------------------------------------------------
BASE = "https://www.aciertamax.com"

# slug en la URL de aciertamax.com -> nombre canonico en el sitio
MUNICIPIOS = {
    "guadalajara": "Guadalajara",
    "zapopan": "Zapopan",
    "tlaquepaque": "Tlaquepaque",
    "tonala": "Tonalá",
    "tlajomulco-de-zuniga": "Tlajomulco de Zúñiga",
}
# Como puede venir escrito el municipio en una tarjeta -> canonico
ALIAS_MUNICIPIO = {
    "guadalajara": "Guadalajara",
    "zapopan": "Zapopan",
    "tlaquepaque": "Tlaquepaque",
    "san pedro tlaquepaque": "Tlaquepaque",
    "tonala": "Tonalá",
    "tlajomulco de zuniga": "Tlajomulco de Zúñiga",
    "tlajomulco": "Tlajomulco de Zúñiga",
}

OPERACIONES = {"VENTA": "properties", "RENTA": "rentals"}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; AciertaMaxInventarioBot/2.0; +https://acierta.pro)"
}
PAUSA_ENTRE_PAGINAS = 1.5      # cortesia con el sitio
PAUSA_DETALLE = 1.0
MAX_DETALLES_FOTO = 600        # tope de paginas de detalle para rescatar fotos
REINTENTOS = 4

# Segmentos
TIPOS_COMERCIALES = {
    "oficina", "local comercial", "local en centro comercial",
    "bodega comercial", "bodega industrial", "nave industrial",
    "terreno comercial", "terreno industrial",
}
# Tipos "por decidir": se van a VIVIENDA salvo que el titulo diga claramente
# que es comercial (decision de Javier: lo indeciso se queda en vivienda).
TIPOS_POR_DECIDIR = {"terreno", "edificio", "casa con uso de suelo", "otro"}
# 'casa con uso de suelo' se queda SIEMPRE en vivienda (decision de Javier).
TIPOS_SIEMPRE_VIVIENDA = {"casa con uso de suelo"}
PALABRAS_COMERCIALES = re.compile(
    r"\b(comercial(es)?|usos? mixtos?|industrial(es)?|corporativ[oa]s?|bodegas?|"
    r"oficinas?|hotel|gasolinera|estacionamiento|locales?|naves?|plaza comercial)\b"
)
PALABRAS_HABITACIONALES = re.compile(r"\b(habitacional(es)?|residencial(es)?|departamentos?|vivienda)\b")

# Guardas de precio (en MXN salvo que se indique). Se evalua por precio/m2 cuando
# hay m2, porque un terreno enorme de cientos de millones puede ser legitimo.
# Formato: (aviso_si_mayor_que, bloquea_si_mayor_que)
GUARDA_PM2_VENTA = {          # pesos por m2
    "vivienda": (300_000, 1_000_000),
    "terreno": (150_000, 500_000),
    "comercial": (200_000, 600_000),
}
GUARDA_PM2_RENTA = {          # pesos por m2 al mes
    "vivienda": (800, 1_500),
    "comercial": (2_500, 6_000),
}
# m2 por debajo de esto es casi seguro un error de captura (ej. una casa de "1 m2"):
# no se bloquea la ficha por eso; se publica SIN m2 y se avisa.
M2_MIN_CREIBLE = {"vivienda": 15, "terreno": 20, "comercial": 8}
VENTA_ABS_BLOQUEA_MXN = 5_000_000_000      # sin m2: mas de 5 mil millones
VENTA_ABS_AVISO_MXN = 500_000_000
VENTA_USD_AVISO = 50_000_000
VENTA_USD_BLOQUEA = 500_000_000
VENTA_MIN_BLOQUEA = 20_000                 # menos de esto es placeholder/error
VENTA_MIN_AVISO = 150_000
RENTA_MIN_BLOQUEA = 1_000
RENTA_MIN_AVISO = 2_500
RENTA_VIVIENDA_ABS_BLOQUEA = 1_000_000     # renta mensual de vivienda

# Precio por m2: en terrenos y espacios comerciales es comun anunciar "$18,000 por m2" o una renta
# "$120 por m2 al mes". Eso NO es un error: se convierte a precio total (precio x m2) y se conserva
# el dato original en 'pm2_pub'. Si el anuncio lo dice, es seguro; si no, se infiere cuando el precio
# es imposible como total (y se avisa).
TIPOS_PRECIO_M2 = ("terreno", "bodega", "nave", "local", "oficina", "edificio")
M2_MIN_INFERIR = {"VENTA": 100, "RENTA": 50}
UMBRAL_PM2 = {                 # (operacion, moneda_es_mxn) -> si el precio es menor, se asume por m2
    ("VENTA", True): 150_000,
    ("RENTA", True): 2_500,
    ("VENTA", False): 5_000,
    ("RENTA", False): 60,
}
MARCADOR_POR_M2 = re.compile(r"(por|x|/)\s*m\s*(2|²|etro)", re.I)

BANOS_MAX_CREIBLE = 30
RECAMARAS_MAX_CREIBLE = 30

# Frenos de seguridad
FRENO_COMBO = 0.5     # un municipio+operacion no puede caer a menos de 50% de lo anterior
FRENO_TOTAL = 0.7     # el total no puede caer a menos de 70% de lo anterior
FRENO_SIN_FOTO = 0.05 # si mas de 5% no tiene foto, algo fallo: no se descartan

RUTA_DATA = "data.json"
RUTA_CSV = "inventario.csv"
RUTA_META = "inventario-meta.json"
DIR_REPORTES = os.path.join("reportes", "inventario")


# ----------------------------------------------------------------------
# UTILIDADES
# ----------------------------------------------------------------------
def sin_acentos(texto):
    t = unicodedata.normalize("NFD", texto or "")
    return "".join(c for c in t if unicodedata.category(c) != "Mn").lower().strip()


def limpiar_precio(texto):
    """'$31,500,000 MXN En Venta' -> (31500000.0, 'MXN')"""
    m = re.search(r"\$\s*([\d,]+(?:\.\d+)?)\s*(USD|MXN)?", texto or "")
    if not m:
        return None, None
    return float(m.group(1).replace(",", "")), (m.group(2) or "MXN")


def a_numero(valor, entero=False):
    """'3' -> 3 ; '2.5' -> 2.5 ; '4+' -> 4 ; None/'' -> None"""
    if valor is None or valor == "":
        return None
    m = re.search(r"\d+(?:\.\d+)?", str(valor))
    if not m:
        return None
    n = float(m.group(0))
    if entero or n == int(n):
        return int(n) if entero else n
    return n


def extraer_codigo_eb(*textos):
    for t in textos:
        m = re.search(r"EB-[A-Z0-9]+", t or "")
        if m:
            return m.group(0)
    return ""


def normalizar_municipio(texto_tarjeta, slug_url):
    """Devuelve el municipio canonico, o None si la tarjeta es de otro municipio."""
    clave = sin_acentos(texto_tarjeta)
    if clave:
        return ALIAS_MUNICIPIO.get(clave)   # None => fuera de zona
    return MUNICIPIOS.get(slug_url)


def foto_con_tamano(url, ancho, alto):
    """Reescribe width/height de la URL de EasyBroker (o los agrega)."""
    if not url:
        return url
    if re.search(r"[?&]width=\d+", url):
        url = re.sub(r"([?&])width=\d+", rf"\g<1>width={ancho}", url)
    else:
        url += ("&" if "?" in url else "?") + f"width={ancho}"
    if re.search(r"[?&]height=\d+", url):
        url = re.sub(r"([?&])height=\d+", rf"\g<1>height={alto}", url)
    else:
        url += f"&height={alto}"
    return url


# ----------------------------------------------------------------------
# SEGMENTO
# ----------------------------------------------------------------------
def clasificar_segmento(tipo, titulo):
    """Devuelve (segmento, razon). Lo indeciso se queda en vivienda."""
    t = sin_acentos(tipo)
    if t in TIPOS_COMERCIALES:
        return "comercial", "tipo comercial"
    if t in TIPOS_SIEMPRE_VIVIENDA:
        return "vivienda", "por decidir -> vivienda"
    if t in TIPOS_POR_DECIDIR:
        tit = sin_acentos(titulo)
        if PALABRAS_COMERCIALES.search(tit):
            if t == "edificio" and PALABRAS_HABITACIONALES.search(tit) and not re.search(
                    r"\b(comercial(es)?|oficinas?|hotel|locales?|corporativ[oa]s?|estacionamiento)\b", tit):
                return "vivienda", "por decidir -> vivienda"
            return "comercial", "palabra clave en el titulo"
        return "vivienda", "por decidir -> vivienda"
    return "vivienda", "tipo de vivienda"


# ----------------------------------------------------------------------
# GUARDAS DE PRECIO
# ----------------------------------------------------------------------
def grupo_m2(fila):
    if sin_acentos(fila.get("tipo")).startswith("terreno"):
        return "terreno"
    return "comercial" if fila.get("segmento") == "comercial" else "vivienda"


def sanear_m2(fila):
    """Si los m2 son imposibles de creer, se publica sin m2 y se devuelve el aviso."""
    m2 = fila.get("m2")
    if m2 is None:
        return None
    if m2 < M2_MIN_CREIBLE[grupo_m2(fila)]:
        fila["_m2_original"] = m2
        fila["m2"] = None
        return f"m2 dudoso ({m2:g}); se publica sin m2"
    return None


def resolver_precio_por_m2(fila):
    """Convierte un precio por m2 a precio total. Devuelve (via, motivo, bloquea):
    via in {None, 'anuncio', 'inferido'}."""
    precio, m2 = fila.get("precio"), fila.get("m2")
    if not precio:
        return None, "", False
    texto = fila.get("_precio_texto") or ""
    tipo = sin_acentos(fila.get("tipo"))
    es_mxn = (fila.get("moneda") or "MXN") == "MXN"
    op = fila["operacion"]
    dice_por_m2 = bool(MARCADOR_POR_M2.search(texto))
    infiere = (tipo.startswith(TIPOS_PRECIO_M2) and m2 is not None and m2 >= M2_MIN_INFERIR[op]
               and precio < UMBRAL_PM2[(op, es_mxn)])
    if not (dice_por_m2 or infiere):
        return None, "", False
    if not m2:
        return None, f"el anuncio es por m2 ({precio:,.0f}) pero no trae superficie", True
    total = round(precio * m2)
    fila["pm2_pub"] = precio
    fila["precio"] = total
    via = "anuncio" if dice_por_m2 else "inferido"
    return via, f"precio por m2 {precio:,.0f} x {m2:,.0f} m2 = {total:,.0f} ({via})", False


def evaluar_precio(fila):
    """Devuelve (nivel, motivo): nivel in {'ok','aviso','bloquea'}."""
    precio = fila.get("precio")
    if precio is None or precio <= 0:
        return "bloquea", "sin precio"
    op = fila["operacion"]
    seg = fila["segmento"]
    moneda = fila.get("moneda") or "MXN"
    m2 = fila.get("m2")
    tipo = sin_acentos(fila.get("tipo"))

    if op == "VENTA":
        if moneda != "MXN":
            if precio > VENTA_USD_BLOQUEA:
                return "bloquea", f"precio en {moneda} irreal ({precio:,.0f})"
            if precio > VENTA_USD_AVISO:
                return "aviso", f"precio en {moneda} muy alto ({precio:,.0f})"
            return "ok", ""
        if precio < VENTA_MIN_BLOQUEA:
            return "bloquea", f"precio de venta demasiado bajo ({precio:,.0f})"
        if m2 and m2 > 0:
            pm2 = precio / m2
            grupo = "terreno" if tipo.startswith("terreno") else ("comercial" if seg == "comercial" else "vivienda")
            aviso, bloquea = GUARDA_PM2_VENTA[grupo]
            if pm2 > bloquea:
                return "bloquea", f"precio/m2 imposible ({pm2:,.0f} $/m2 con {m2:,.0f} m2)"
            if pm2 > aviso:
                return "aviso", f"precio/m2 muy alto ({pm2:,.0f} $/m2)"
        else:
            if precio > VENTA_ABS_BLOQUEA_MXN:
                return "bloquea", f"precio irreal sin m2 ({precio:,.0f})"
            if precio > VENTA_ABS_AVISO_MXN:
                return "aviso", f"precio muy alto sin m2 ({precio:,.0f})"
        if precio < VENTA_MIN_AVISO:
            return "aviso", f"precio de venta muy bajo ({precio:,.0f})"
        return "ok", ""

    # RENTA
    if moneda != "MXN":
        return "ok", ""
    if precio < RENTA_MIN_BLOQUEA:
        return "bloquea", f"renta demasiado baja ({precio:,.0f})"
    if seg == "vivienda" and not tipo.startswith("terreno") and precio > RENTA_VIVIENDA_ABS_BLOQUEA:
        return "bloquea", f"renta mensual de vivienda irreal ({precio:,.0f})"
    if m2 and m2 > 0:
        pm2 = precio / m2
        aviso, bloquea = GUARDA_PM2_RENTA["comercial" if seg == "comercial" else "vivienda"]
        if pm2 > bloquea:
            return "bloquea", f"renta/m2 imposible ({pm2:,.0f} $/m2/mes con {m2:,.0f} m2)"
        if pm2 > aviso:
            return "aviso", f"renta/m2 muy alta ({pm2:,.0f} $/m2/mes)"
    if precio < RENTA_MIN_AVISO:
        return "aviso", f"renta muy baja ({precio:,.0f})"
    return "ok", ""


# ----------------------------------------------------------------------
# LECTURA DEL SITIO
# ----------------------------------------------------------------------
def get_con_reintentos(session, url):
    espera = 2
    for intento in range(1, REINTENTOS + 1):
        try:
            resp = session.get(url, headers=HEADERS, timeout=25)
            if resp.status_code == 200:
                return resp
            if resp.status_code not in (429, 500, 502, 503, 504):
                print(f"  [HTTP {resp.status_code}] {url}")
                return None
            print(f"  [HTTP {resp.status_code}] reintento {intento}/{REINTENTOS}: {url}")
        except requests.RequestException as e:
            print(f"  [ERROR] reintento {intento}/{REINTENTOS}: {url} -> {e}")
        time.sleep(espera)
        espera *= 2
    return None


def parsear_tarjetas(html):
    """Una dict por propiedad a partir del HTML de un listado de aciertamax.com."""
    soup = BeautifulSoup(html, "html.parser")
    resultados = []
    for tarjeta in soup.select("div.property-listing"):
        raw = tarjeta.get("data-popover-data", "")
        if not raw:
            continue
        try:
            data = json.loads(raw)
        except (json.JSONDecodeError, ValueError):
            continue

        precio, moneda = limpiar_precio(data.get("price", "") or "")

        m2 = None
        m2_match = re.search(r"[\d,]+(?:\.\d+)?", data.get("size") or "")
        if m2_match:
            try:
                m2 = float(m2_match.group(0).replace(",", ""))
            except ValueError:
                m2 = None

        tipo_tag = tarjeta.select_one("p.property-type")
        tipo = tipo_tag.get_text(strip=True) if tipo_tag else ""

        location = data.get("location", "") or ""
        resto = location
        if tipo and resto.startswith(tipo):
            resto = resto[len(tipo):].strip()
            if resto.lower().startswith("en "):
                resto = resto[3:].strip()
        colonia, municipio_tarjeta = "", ""
        if "," in resto:
            colonia, municipio_tarjeta = resto.rsplit(",", 1)
            colonia, municipio_tarjeta = colonia.strip(), municipio_tarjeta.strip()
        else:
            colonia = resto.strip()

        img = tarjeta.select_one("img")
        img_alt = img.get("alt", "") if img else ""
        foto = data.get("image_url", "") or (img.get("src", "") if img else "")
        codigo_eb = extraer_codigo_eb(img_alt, data.get("image_url", ""), foto)

        url_rel = data.get("url", "") or ""
        href = url_rel if url_rel.startswith("http") else f"{BASE}{url_rel}"

        def _f(v):
            try:
                return float(v)
            except (TypeError, ValueError):
                return None

        resultados.append({
            "href": href, "precio": precio, "moneda": moneda, "m2": m2,
            "recamaras": a_numero(data.get("bedrooms"), entero=True),
            "banos": a_numero(data.get("bathrooms")),
            "colonia": colonia, "municipio_tarjeta": municipio_tarjeta,
            "tipo": (tipo or "").strip().lower(), "titulo": data.get("title", "") or "",
            "codigo_eb": codigo_eb, "foto": foto or None, "precio_texto": data.get("price", "") or "",
            "lat": _f(tarjeta.get("data-lat")), "lon": _f(tarjeta.get("data-long")),
        })
    return resultados


def recorrer(session, operacion, slug_operacion, slug_municipio, paginas_max):
    """Devuelve (filas, completo). completo=False si una pagina fallo a medio camino."""
    filas, pagina, completo = [], 1, True
    while True:
        if pagina == 1:
            url = f"{BASE}/{slug_operacion}/mexico/jalisco/{slug_municipio}?sort_by=price-desc"
        else:
            url = f"{BASE}/{slug_operacion}/mexico/jalisco/{slug_municipio}?page={pagina}&sort_by=price-desc"
        resp = get_con_reintentos(session, url)
        if resp is None:
            completo = False
            break
        tarjetas = parsear_tarjetas(resp.text)
        if not tarjetas:
            break
        for t in tarjetas:
            t["operacion"] = operacion
            t["slug_municipio"] = slug_municipio
        filas.extend(tarjetas)
        print(f"  {operacion} {slug_municipio} pag {pagina}: {len(tarjetas)} (acum {len(filas)})", flush=True)
        if paginas_max and pagina >= paginas_max:
            break
        if "Siguiente" not in resp.text or f"page={pagina + 1}" not in resp.text:
            break
        pagina += 1
        time.sleep(PAUSA_ENTRE_PAGINAS)
    return filas, completo


def foto_desde_detalle(session, href):
    """Rescata la foto principal desde la pagina de detalle (og:image)."""
    resp = get_con_reintentos(session, href)
    if resp is None:
        return None
    soup = BeautifulSoup(resp.text, "html.parser")
    og = soup.find("meta", attrs={"property": "og:image"})
    if og and og.get("content"):
        return og["content"]
    for img in soup.find_all("img"):
        src = img.get("src") or ""
        if "property_images" in src:
            return src
    return None


# ----------------------------------------------------------------------
# CONSTRUCCION DE FILAS
# ----------------------------------------------------------------------
def clave(fila):
    return (fila.get("eb") or fila.get("liga"), fila["operacion"])


def construir_fila(t, previas):
    """Convierte una tarjeta en una fila con el formato de data.json."""
    municipio = normalizar_municipio(t["municipio_tarjeta"], t["slug_municipio"])
    if municipio is None:
        return None, "fuera de zona"
    seg, razon = clasificar_segmento(t["tipo"], t["titulo"])
    fila = {
        "municipio": municipio, "operacion": t["operacion"], "precio": t["precio"],
        "titulo": t["titulo"], "tipo": t["tipo"], "recamaras": t["recamaras"],
        "banos": t["banos"], "m2": t["m2"], "niveles": None,
        "eb": t["codigo_eb"], "liga": t["href"], "foto": t["foto"],
        "lat": t["lat"], "lon": t["lon"], "colonia": t["colonia"], "segmento": seg,
    }
    if t.get("moneda") and t["moneda"] != "MXN":
        fila["moneda"] = t["moneda"]
    # datos imposibles -> vacio (no se inventa nada)
    if fila["banos"] is not None and fila["banos"] > BANOS_MAX_CREIBLE:
        fila["banos"] = None
    if fila["recamaras"] is not None and fila["recamaras"] > RECAMARAS_MAX_CREIBLE:
        fila["recamaras"] = None
    # lo que el listado no trae se conserva de la corrida anterior
    previa = previas.get(clave(fila))
    if previa:
        if previa.get("niveles"):
            fila["niveles"] = previa["niveles"]
        if not fila["foto"] and previa.get("foto"):
            fila["foto"] = previa["foto"]
    fila["_razon_segmento"] = razon
    fila["_precio_texto"] = t.get("precio_texto", "")
    return fila, None


# ----------------------------------------------------------------------
# SALIDAS
# ----------------------------------------------------------------------
COLUMNAS_CSV = ["eb", "operacion", "segmento", "tipo", "municipio", "colonia", "titulo", "precio", "pm2_pub",
                "moneda", "recamaras", "banos", "m2", "niveles", "lat", "lon", "foto", "liga"]


def escribir_csv(ruta, filas):
    with open(ruta, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNAS_CSV, extrasaction="ignore")
        w.writeheader()
        for fila in filas:
            w.writerow({**fila, "moneda": fila.get("moneda", "MXN")})


def cargar_previo(ruta):
    if not os.path.exists(ruta):
        return []
    with open(ruta, encoding="utf-8") as f:
        return json.load(f)


def probar_foto_grande(filas, muestra=12):
    """Prueba si assets.easybroker.com entrega fotos mas grandes cambiando width/height."""
    try:
        from io import BytesIO
        from PIL import Image
    except ImportError:
        return None, "Pillow no instalado"
    con_foto = [f for f in filas if f.get("foto")]
    paso = max(1, len(con_foto) // muestra)
    resultados = []
    for f in con_foto[::paso][:muestra]:
        try:
            r = requests.get(foto_con_tamano(f["foto"], 1200, 800), headers=HEADERS, timeout=25)
            if r.status_code == 200:
                w, h = Image.open(BytesIO(r.content)).size
                resultados.append((w, h))
            else:
                resultados.append((0, 0))
        except Exception:
            resultados.append((0, 0))
    buenas = sum(1 for w, h in resultados if max(w, h) >= 900)
    detalle = ", ".join(f"{w}x{h}" for w, h in resultados)
    return buenas >= max(1, int(len(resultados) * 0.8)), f"{buenas}/{len(resultados)} fotos con lado mayor >= 900px ({detalle})"


# ----------------------------------------------------------------------
# PRINCIPAL
# ----------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--paginas-max", type=int, default=0, help="limita paginas por municipio/operacion (pruebas)")
    ap.add_argument("--sin-escribir", action="store_true", help="no escribe data.json (pruebas)")
    ap.add_argument("--reusar-data", action="store_true",
                    help="no rastrea: aplica 4 municipios, segmento y guardas de precio a data.json existente")
    args = ap.parse_args()

    ahora = datetime.now(timezone.utc)
    fecha = ahora.strftime("%Y-%m-%d")
    previo = cargar_previo(RUTA_DATA)
    previas = {clave(p): p for p in previo}
    municipios_ok = set(MUNICIPIOS.values())
    previo_zona = [p for p in previo if p.get("municipio") in municipios_ok]
    fuera_de_zona_previas = sum(1 for p in previo if p.get("municipio") not in municipios_ok)

    session = requests.Session()
    tarjetas, incompletos = [], []
    cuenta_combo = Counter()
    fuera_zona, duplicadas = 0, 0
    if args.reusar_data:
        # Sin rastreo: se reutiliza lo que ya esta en data.json y solo se aplican las reglas nuevas.
        filas = []
        for p in previo_zona:
            fila = dict(p)
            fila["segmento"], fila["_razon_segmento"] = clasificar_segmento(p.get("tipo"), p.get("titulo"))
            if fila.get("banos") is not None and fila["banos"] > BANOS_MAX_CREIBLE:
                fila["banos"] = None
            if fila.get("recamaras") is not None and fila["recamaras"] > RECAMARAS_MAX_CREIBLE:
                fila["recamaras"] = None
            filas.append(fila)
    else:
        for operacion, slug_op in OPERACIONES.items():
            for slug_mun, nombre in MUNICIPIOS.items():
                print(f"\n== {operacion} - {nombre} ==", flush=True)
                filas_mun, completo = recorrer(session, operacion, slug_op, slug_mun, args.paginas_max)
                tarjetas.extend(filas_mun)
                cuenta_combo[(nombre, operacion)] = len(filas_mun)
                if not completo:
                    incompletos.append(f"{operacion} {nombre}")

        # --- construir y deduplicar
        filas, vistos = [], set()
        for t in tarjetas:
            fila, motivo = construir_fila(t, previas)
            if fila is None:
                fuera_zona += 1
                continue
            k = clave(fila)
            if k in vistos:
                duplicadas += 1
                continue
            vistos.add(k)
            filas.append(fila)

    # --- frenos de seguridad (no aplican en corrida de prueba)
    if not args.sin_escribir and not args.reusar_data:
        previo_combo = Counter((p["municipio"], p["operacion"]) for p in previo_zona)
        problemas = []
        for combo, n_prev in previo_combo.items():
            if n_prev >= 20 and cuenta_combo.get(combo, 0) < n_prev * FRENO_COMBO:
                problemas.append(f"{combo[1]} {combo[0]}: {cuenta_combo.get(combo, 0)} fichas vs {n_prev} antes")
        if previo_zona and len(filas) < len(previo_zona) * FRENO_TOTAL:
            problemas.append(f"total {len(filas)} vs {len(previo_zona)} antes")
        if incompletos:
            problemas.append("paginacion interrumpida en: " + ", ".join(incompletos))
        if problemas and os.environ.get("FORZAR") != "1":
            print("\n[FRENO] La corrida salio incompleta, NO se sobreescribe el inventario vigente:")
            for p in problemas:
                print("  -", p)
            sys.exit(2)

    # --- fotos: rescate por pagina de detalle
    sin_foto = [f for f in filas if not f.get("foto")]
    rescatadas = 0
    for f in ([] if args.reusar_data else sin_foto[:MAX_DETALLES_FOTO]):
        foto = foto_desde_detalle(session, f["liga"])
        time.sleep(PAUSA_DETALLE)
        if foto:
            f["foto"] = foto
            rescatadas += 1
    sin_foto = [f for f in filas if not f.get("foto")]

    # --- guardas de precio
    publicables, bloqueadas, avisos = [], [], []
    conversiones = []
    for f in filas:
        aviso_m2 = sanear_m2(f)
        via_pm2, motivo_pm2, bloquea_pm2 = resolver_precio_por_m2(f)
        if bloquea_pm2:
            nivel, motivo = "bloquea", motivo_pm2
        else:
            nivel, motivo = evaluar_precio(f)
            if via_pm2:
                conversiones.append((f, via_pm2, motivo_pm2))
                if via_pm2 == "inferido":
                    motivo = (motivo + " | " if motivo else "") + motivo_pm2
                    if nivel == "ok":
                        nivel = "aviso"
        if aviso_m2:
            motivo = (motivo + " | " if motivo else "") + aviso_m2
            if nivel == "ok":
                nivel = "aviso"
        if nivel == "bloquea":
            bloqueadas.append((f, motivo))
        else:
            if nivel == "aviso":
                avisos.append((f, motivo))
            publicables.append(f)

    # --- regla de fotos: toda ficha debe tener foto
    freno_foto = args.reusar_data or (len(filas) > 0 and (len(sin_foto) / len(filas)) > FRENO_SIN_FOTO)
    descartadas_sin_foto = []
    if not freno_foto:
        descartadas_sin_foto = [f for f in publicables if not f.get("foto")]
        publicables = [f for f in publicables if f.get("foto")]

    # --- comparacion contra la corrida anterior
    k_nuevo = {clave(f): f for f in publicables}
    k_prev = {clave(p): p for p in previo_zona}
    nuevas = [k for k in k_nuevo if k not in k_prev]
    bajas = [k for k in k_prev if k not in k_nuevo]
    cambios_precio = [k for k in k_nuevo if k in k_prev and k_prev[k].get("precio") != k_nuevo[k].get("precio")]

    publicables.sort(key=lambda f: (f["operacion"], f["municipio"], -(f["precio"] or 0)))
    por_segmento = Counter(f["segmento"] for f in publicables)
    por_seg_op = Counter((f["segmento"], f["operacion"]) for f in publicables)
    por_municipio = Counter(f["municipio"] for f in publicables)
    razones = Counter(f["_razon_segmento"] for f in publicables)
    foto_ok, foto_detalle = (None, "no aplica (sin rastreo)") if args.reusar_data else probar_foto_grande(publicables)

    # --- escribir
    salida = [{k: v for k, v in f.items() if not k.startswith("_")} for f in publicables]
    os.makedirs(DIR_REPORTES, exist_ok=True)
    if not args.sin_escribir:
        with open(RUTA_DATA, "w", encoding="utf-8") as fh:
            json.dump(salida, fh, ensure_ascii=False, separators=(",", ":"))
        escribir_csv(RUTA_CSV, salida)
        with open(RUTA_META, "w", encoding="utf-8") as fh:
            json.dump({
                "actualizado": ahora.isoformat(timespec="seconds"), "total": len(salida),
                "por_segmento": dict(por_segmento), "municipios": sorted(municipios_ok),
                "foto_grande_ok": bool(foto_ok),
            }, fh, ensure_ascii=False, indent=1)

    def _escribir_reporte(nombre, encabezado, filas_rep):
        with open(os.path.join(DIR_REPORTES, nombre), "w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh)
            w.writerow(encabezado)
            w.writerows(filas_rep)

    _escribir_reporte("anomalias_precio.csv",
                      ["nivel", "eb", "operacion", "tipo", "municipio", "precio", "moneda", "m2", "motivo", "liga", "precio_texto_anuncio"],
                      [["BLOQUEADA (no publicada)", f["eb"], f["operacion"], f["tipo"], f["municipio"], f["precio"],
                        f.get("moneda", "MXN"), f["m2"], m, f["liga"], f.get("_precio_texto", "")] for f, m in bloqueadas] +
                      [["AVISO (publicada)", f["eb"], f["operacion"], f["tipo"], f["municipio"], f["precio"],
                        f.get("moneda", "MXN"), f["m2"], m, f["liga"], f.get("_precio_texto", "")] for f, m in avisos])
    _escribir_reporte("precios_por_m2.csv",
                      ["eb", "operacion", "tipo", "municipio", "moneda", "precio_publicado_por_m2", "m2", "precio_total", "como_se_supo", "liga", "precio_texto_anuncio"],
                      [[f["eb"], f["operacion"], f["tipo"], f["municipio"], f.get("moneda", "MXN"), f.get("pm2_pub"), f["m2"], f["precio"], via,
                        f["liga"], f.get("_precio_texto", "")] for f, via, _m in conversiones if f in publicables])
    _escribir_reporte("sin_foto.csv", ["eb", "operacion", "tipo", "municipio", "titulo", "liga"],
                      [[f["eb"], f["operacion"], f["tipo"], f["municipio"], f["titulo"], f["liga"]]
                       for f in (sin_foto if freno_foto else descartadas_sin_foto)])

    resumen = [
        f"# Inventario acierta.pro - corrida {fecha}",
        "",
        f"- Fichas publicadas: **{len(salida):,}**",
        f"- Por segmento: {dict(por_segmento)}",
        f"- Por segmento y operacion: { {f'{s}/{o}': n for (s, o), n in por_seg_op.items()} }",
        f"- Por municipio: {dict(por_municipio)}",
        f"- Segmento por: {dict(razones)}",
        "",
        "## Contra la corrida anterior (mismos 4 municipios)",
        f"- Nuevas: {len(nuevas):,} | Bajas: {len(bajas):,} | Cambios de precio: {len(cambios_precio):,}",
        f"- Fichas de otros municipios retiradas del sitio: {fuera_de_zona_previas:,}",
        "",
        "## Calidad",
        f"- Precios BLOQUEADOS (no publicados, verificar con el originador): {len(bloqueadas)}",
        f"- Precios con AVISO (publicados, conviene revisar): {len(avisos)}",
        f"- Precios por m2 convertidos a total: {sum(1 for f, v, m in conversiones if f in publicables)} "
        f"(el anuncio lo dice: {sum(1 for f, v, m in conversiones if v == 'anuncio' and f in publicables)}"
        f" | inferidos, con aviso: {sum(1 for f, v, m in conversiones if v == 'inferido' and f in publicables)})",
        f"- Fotos rescatadas desde la pagina de detalle: {rescatadas}",
        f"- Fichas sin foto: {len(sin_foto)} "
        + ("(sin rastreo / FRENO: no se descartaron)" if freno_foto else f"(descartadas del sitio: {len(descartadas_sin_foto)})"),
        f"- Fuera de zona descartadas: {fuera_zona} | Duplicadas: {duplicadas}",
        f"- Prueba de foto grande: {foto_detalle}",
        "",
        "Reportes: reportes/inventario/anomalias_precio.csv, sin_foto.csv y precios_por_m2.csv",
    ]
    texto = "\n".join(resumen)
    with open(os.path.join(DIR_REPORTES, "resumen.md"), "w", encoding="utf-8") as fh:
        fh.write(texto + "\n")
    print("\n" + texto)
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as fh:
            fh.write(texto + "\n")

    if not salida and not args.sin_escribir:
        print("[AVISO] No quedo ninguna ficha publicable.")
        sys.exit(1)


if __name__ == "__main__":
    main()

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
from datetime import datetime, timezone, timedelta

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
    "el-salto": "El Salto",            # SOLO segmento comercial (corredor industrial: bodegas, naves)
}
MUNICIPIOS_SOLO_COMERCIAL = {"El Salto"}
# Como puede venir escrito el municipio en una tarjeta -> canonico
ALIAS_MUNICIPIO = {
    "guadalajara": "Guadalajara",
    "zapopan": "Zapopan",
    "tlaquepaque": "Tlaquepaque",
    "san pedro tlaquepaque": "Tlaquepaque",
    "tonala": "Tonalá",
    "tlajomulco de zuniga": "Tlajomulco de Zúñiga",
    "tlajomulco": "Tlajomulco de Zúñiga",
    "el salto": "El Salto",
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
# Rango creible de precio POR m2 (pesos; en renta, por mes). Sirve para decidir si el numero de un anuncio
# "por m2" es de verdad el precio por m2 o ya es el total (error de captura frecuente en EasyBroker).
RANGO_UNIT = {
    ("VENTA", True): (150, 250_000),
    ("RENTA", True): (30, 3_000),
    ("VENTA", False): (8, 12_000),
    ("RENTA", False): (1, 120),
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
    via in {None, 'anuncio', 'inferido', 'total'}.
      'anuncio'  : el anuncio dice "por m2" y el numero es creible como precio por m2 -> se convierte a total.
      'inferido' : el anuncio no lo dice, pero el numero es imposible como total -> se convierte (con aviso).
      'total'    : el anuncio dice "por m2" pero el numero ya es el total (error de captura) -> se deja igual (con aviso)."""
    precio, m2 = fila.get("precio"), fila.get("m2")
    if not precio:
        return None, "", False
    texto = fila.get("_precio_texto") or ""
    tipo = sin_acentos(fila.get("tipo"))
    es_mxn = (fila.get("moneda") or "MXN") == "MXN"
    op = fila["operacion"]
    dice_por_m2 = bool(MARCADOR_POR_M2.search(texto))

    if dice_por_m2:
        if not m2:
            return None, f"el anuncio es por m2 ({precio:,.0f}) pero no trae superficie", True
        lo, hi = RANGO_UNIT[(op, es_mxn)]
        unitario_b = precio / m2
        if lo <= precio <= hi:
            via = "anuncio"
        elif lo <= unitario_b <= hi:
            return "total", (f"el anuncio dice 'por m2' pero {precio:,.0f} es el total "
                             f"(equivale a {unitario_b:,.0f} por m2)"), False
        else:
            return None, "", False          # ninguna lectura es creible: que decidan las guardas
    else:
        infiere = (tipo.startswith(TIPOS_PRECIO_M2) and m2 is not None and m2 >= M2_MIN_INFERIR[op]
                   and precio < UMBRAL_PM2[(op, es_mxn)])
        if not infiere:
            return None, "", False
        via = "inferido"
    total = round(precio * m2)
    fila["pm2_pub"] = precio
    fila["precio"] = total
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


TOPE_PAGINAS_EB = 100   # EasyBroker no entrega mas de 100 paginas (~1,800 fichas) por busqueda
AVISOS_TOPE = []        # combos donde ni con las dos pasadas se cubrio todo (va al resumen)


def _pasada(session, operacion, slug_operacion, slug_municipio, orden, paginas_max, ya_vistos=None):
    """Recorre una busqueda en un orden dado. Devuelve (filas, completo, paginas,
    toco_repetidas). Si ya_vistos viene, se detiene en cuanto una pagina trae
    solo fichas ya vistas (las dos pasadas ya se encontraron)."""
    filas, pagina, completo, toco = [], 1, True, False
    while True:
        url = f"{BASE}/{slug_operacion}/mexico/jalisco/{slug_municipio}?sort_by={orden}"
        if pagina > 1:
            url = f"{BASE}/{slug_operacion}/mexico/jalisco/{slug_municipio}?page={pagina}&sort_by={orden}"
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
        print(f"  {operacion} {slug_municipio} [{orden}] pag {pagina}: {len(tarjetas)} (acum {len(filas)})", flush=True)
        if ya_vistos is not None and all(t.get("codigo_eb") in ya_vistos for t in tarjetas):
            toco = True
            break
        if paginas_max and pagina >= paginas_max:
            break
        if "Siguiente" not in resp.text or f"page={pagina + 1}" not in resp.text:
            break
        pagina += 1
        time.sleep(PAUSA_ENTRE_PAGINAS)
    return filas, completo, pagina, toco


def recorrer(session, operacion, slug_operacion, slug_municipio, paginas_max):
    """Devuelve (filas, completo). completo=False si una pagina fallo a medio camino.
    EasyBroker corta en 100 paginas: si la pasada de mayor a menor precio llega
    al tope, se hace una segunda de menor a mayor hasta encontrarse con la
    primera, para no perder las propiedades mas baratas (antes en Zapopan y
    Guadalajara solo llegaban las caras)."""
    filas, completo, paginas, _ = _pasada(session, operacion, slug_operacion, slug_municipio,
                                          "price-desc", paginas_max)
    if completo and not paginas_max and paginas >= TOPE_PAGINAS_EB:
        vistos = {t.get("codigo_eb") for t in filas}
        print(f"  {operacion} {slug_municipio}: llego al tope de {TOPE_PAGINAS_EB} paginas, "
              f"segunda pasada de menor a mayor precio", flush=True)
        filas2, completo2, paginas2, toco = _pasada(session, operacion, slug_operacion, slug_municipio,
                                                    "price-asc", 0, vistos)
        nuevas = [t for t in filas2 if t.get("codigo_eb") not in vistos]
        print(f"  {operacion} {slug_municipio}: segunda pasada agrego {len(nuevas)} fichas", flush=True)
        filas.extend(filas2)
        completo = completo and completo2
        primera_pag = {t.get("codigo_eb") for t in filas[:len(filas2)]}
        if toco and paginas2 == 1 and {t.get("codigo_eb") for t in filas2} <= primera_pag:
            AVISOS_TOPE.append(f"{operacion} {slug_municipio}: EasyBroker ignoro el orden de menor a mayor "
                               f"precio; siguen faltando las fichas mas baratas")
        elif completo2 and not toco:
            AVISOS_TOPE.append(f"{operacion} {slug_municipio}: ni con las dos pasadas se cubrio todo "
                               f"(+{len(nuevas)} en la segunda); pueden faltar fichas de precio medio")
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
    if municipio in MUNICIPIOS_SOLO_COMERCIAL and seg != "comercial":
        return None, "fuera de zona"      # El Salto: solo bodegas, naves, terrenos y locales
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
# ARCHIVO PARA CHATGPT (publicidad en redes) - CSV y Excel
# ----------------------------------------------------------------------
RUTA_CHATGPT_CSV = "inventario-chatgpt.csv"
RUTA_CHATGPT_XLSX = "inventario-chatgpt.xlsx"
WHATSAPP_ACIERTA = "523333777337"      # el mismo que usa el sitio (wa.me)
SITIO = "https://acierta.pro"

GRUPOS_TIPO = {   # igual que AM.GRUPOS_TIPO en js/comun.js
    "casa": ("casa", "casa en condominio", "casa con uso de suelo", "quinta", "rancho", "villa"),
    "departamento": ("departamento",),
    "terreno": ("terreno", "terreno industrial", "terreno comercial"),
    "local": ("local comercial", "local en centro comercial"),
    "oficina": ("oficina",),
    "bodega": ("bodega comercial", "bodega industrial", "nave industrial"),
    "edificio": ("edificio",),
}
ETIQUETA_HASHTAG_TIPO = {"casa": "Casa", "departamento": "Departamento", "terreno": "Terreno",
                         "local": "LocalComercial", "oficina": "Oficina", "bodega": "Bodega", "edificio": "Edificio"}
HASHTAG_MUNICIPIO = {"Guadalajara": "Guadalajara", "Zapopan": "Zapopan", "Tlaquepaque": "Tlaquepaque",
                     "Tonalá": "Tonala", "Tlajomulco de Zúñiga": "Tlajomulco", "El Salto": "ElSalto"}
RANGOS_VENTA = [(1e6, "Menos de $1 millón"), (2e6, "$1 a $2 millones"), (3e6, "$2 a $3 millones"),
                (5e6, "$3 a $5 millones"), (8e6, "$5 a $8 millones"), (12e6, "$8 a $12 millones"),
                (20e6, "$12 a $20 millones"), (40e6, "$20 a $40 millones")]
RANGOS_RENTA = [(8000, "Menos de $8,000 al mes"), (12000, "$8,000 a $12,000 al mes"), (18000, "$12,000 a $18,000 al mes"),
                (25000, "$18,000 a $25,000 al mes"), (40000, "$25,000 a $40,000 al mes"),
                (60000, "$40,000 a $60,000 al mes"), (100000, "$60,000 a $100,000 al mes")]

COLUMNAS_CHATGPT = [
    ("codigo_eb", "Clave de la propiedad (EB-XXXXXX). Es la que Wati/MAX usa para identificar la propiedad: debe ir SIEMPRE en el texto."),
    ("operacion", "VENTA o RENTA. Una misma clave EB puede aparecer en venta y en renta: la clave siempre va junto con la operación."),
    ("segmento", "vivienda o comercial. Son clientes distintos: no se mezclan en una publicación."),
    ("tipo", "Tipo tal como lo captura EasyBroker (casa, departamento, terreno, local comercial, bodega industrial...)."),
    ("grupo_tipo", "Tipo agrupado para filtrar: casa, departamento, terreno, local, oficina, bodega, edificio."),
    ("municipio", "Guadalajara, Zapopan, Tlaquepaque, Tonalá, Tlajomulco de Zúñiga o El Salto (solo comercial)."),
    ("colonia", "Colonia o zona, tal como viene del anuncio."),
    ("titulo_anuncio", "Título original del anuncio en EasyBroker (sirve de referencia; no es obligatorio usarlo)."),
    ("precio", "Precio numérico (total). En renta es por mes."),
    ("moneda", "MXN o USD."),
    ("precio_texto", "Precio ya redactado para usar en el texto (ej. $3,200,000 MXN o $18,500 MXN al mes)."),
    ("precio_por_m2", "Precio total entre m² (en renta, por mes). Vacío si no hay superficie confiable."),
    ("precio_publicado_por_m2", "Si el anuncio original estaba por m², aquí va ese precio; el total ya está calculado en 'precio'."),
    ("rango_precio", "Rango de precio para filtrar (ej. $3 a $5 millones)."),
    ("m2", "Superficie en m². Vacía = no se conoce o no es confiable: NO mencionarla."),
    ("recamaras", "Número de recámaras (vivienda). Vacío = no se conoce."),
    ("banos", "Número de baños. Vacío = no se conoce."),
    ("niveles", "Número de niveles o plantas. Vacío = no se conoce."),
    ("lat", "Latitud."),
    ("lon", "Longitud."),
    ("foto_principal", "Foto principal en tamaño grande (1200x800 aprox.). Usar para la imagen."),
    ("foto_miniatura", "La misma foto en miniatura (respaldo si la grande no abre)."),
    ("liga_aciertamax", "Anuncio original en aciertamax.com (la fuente)."),
    ("liga_ficha_acierta_pro", "Ficha de la propiedad en acierta.pro (con comparador, mapa y simulador)."),
    ("liga_whatsapp", "Liga de WhatsApp que ya trae el mensaje con la clave EB: al tocarla, Wati recibe la clave. Usar como llamada a la acción."),
    ("imagen_titular", "Titular corto para la imagen (ej. Casa en venta)."),
    ("imagen_ubicacion", "Ubicación para la imagen (colonia, municipio)."),
    ("imagen_datos", "Línea de datos para la imagen (recámaras, baños, m²). Puede estar vacía."),
    ("imagen_precio", "Precio para la imagen."),
    ("datos_clave", "Datos verificables de la propiedad para la descripción. No agregar nada que no esté aquí."),
    ("hashtags_sugeridos", "Hashtags sugeridos."),
    ("apto_para_publicar", "si = se puede publicar. revisar = hay una duda en el precio: NO publicar sin autorización de Javier."),
    ("nota_calidad", "Aviso sobre el dato (ej. precio calculado, m² no confiable). Respetarlo."),
    ("fecha_inventario", "Fecha de la actualización del inventario."),
]


def _txt_precio(f):
    n = f.get("precio") or 0
    moneda = f.get("moneda") or "MXN"
    sufijo = " al mes" if f["operacion"] == "RENTA" else ""
    return f"${n:,.0f} {moneda}{sufijo}"


def _rango_precio(f):
    if (f.get("moneda") or "MXN") != "MXN":
        return "En dólares (USD)"
    n = f.get("precio") or 0
    if f["operacion"] == "RENTA":
        for tope, texto in RANGOS_RENTA:
            if n < tope:
                return texto
        return "Más de $100,000 al mes"
    for tope, texto in RANGOS_VENTA:
        if n < tope:
            return texto
    return "Más de $40 millones"


def _grupo_tipo(tipo):
    t = sin_acentos(tipo)
    for grupo, tipos in GRUPOS_TIPO.items():
        if t in tipos:
            return grupo
    return "otro"


def _plural(n, uno, varios):
    n = float(n)
    num = f"{n:g}"
    return f"{num} {uno if n == 1 else varios}"


def _datos_clave(f):
    partes = []
    if f.get("recamaras"):
        partes.append(_plural(f["recamaras"], "recámara", "recámaras"))
    if f.get("banos"):
        partes.append(_plural(f["banos"], "baño", "baños"))
    if f.get("m2"):
        partes.append(f"{f['m2']:,.0f} m²")
    if f.get("niveles"):
        partes.append(_plural(f["niveles"], "nivel", "niveles"))
    return " · ".join(partes)


def _hashtag(texto):
    limpio = re.sub(r"[^A-Za-z0-9 ]", "", sin_acentos(texto))
    palabras = [w.capitalize() for w in limpio.split()]
    return "#" + "".join(palabras)[:28] if palabras else ""


HASHTAG_TIPO_ESPECIFICO = {"rancho": "Rancho", "quinta": "Quinta", "villa": "Villa",
                           "casa en condominio": "Casa", "casa con uso de suelo": "Casa"}


def _hashtags(f):
    grupo = _grupo_tipo(f["tipo"])
    en = "EnVenta" if f["operacion"] == "VENTA" else "EnRenta"
    etiqueta = HASHTAG_TIPO_ESPECIFICO.get(sin_acentos(f["tipo"])) or ETIQUETA_HASHTAG_TIPO.get(grupo, "Propiedad")
    tags = ["#AciertaMax", "#" + HASHTAG_MUNICIPIO.get(f["municipio"], "Guadalajara"), "#" + etiqueta + en]
    tags.append("#InmueblesComerciales" if f.get("segmento") == "comercial" else "#BienesRaicesGDL")
    col = _hashtag(f.get("colonia") or "")
    if col and col.lower() not in [t.lower() for t in tags]:
        tags.append(col)
    return " ".join(tags)


def _liga_whatsapp(f):
    from urllib.parse import quote
    op = "venta" if f["operacion"] == "VENTA" else "renta"
    ficha = f"{SITIO}/ficha.html?eb={f['eb']}&op={f['operacion']}"
    texto = f"Hola, me interesa esta propiedad: {f.get('titulo') or ''} ({f['eb']}, {op}) — {ficha}"
    return f"https://wa.me/{WHATSAPP_ACIERTA}?text={quote(texto)}"


def fila_chatgpt(f, fecha):
    """Una fila del archivo para ChatGPT a partir de una ficha publicada."""
    op = "venta" if f["operacion"] == "VENTA" else "renta"
    m2 = f.get("m2")
    precio = f.get("precio") or 0
    tipo = (f.get("tipo") or "").strip()
    nota = f.get("_nota") or f.get("nota") or ""
    revisar = f.get("_revisar") or f.get("revisar")
    if not f.get("eb"):
        nota = (nota + " | " if nota else "") + "Sin clave EB: Wati no podria identificarla"
    if not m2 and "m2" not in nota.lower():
        nota = (nota + " | " if nota else "") + "Sin superficie confiable (no mencionar m2)"
    nota = re.sub(r"\bm2\b", "m²", nota)
    return {
        "codigo_eb": f["eb"], "operacion": f["operacion"], "segmento": f.get("segmento", "vivienda"),
        "tipo": tipo, "grupo_tipo": _grupo_tipo(tipo), "municipio": f["municipio"], "colonia": f.get("colonia") or "",
        "titulo_anuncio": f.get("titulo") or "", "precio": round(precio), "moneda": f.get("moneda") or "MXN",
        "precio_texto": _txt_precio(f),
        "precio_por_m2": round(precio / m2) if (m2 and precio) else "",
        "precio_publicado_por_m2": f.get("pm2_pub") or "",
        "rango_precio": _rango_precio(f), "m2": round(m2, 1) if m2 else "",
        "recamaras": f.get("recamaras") or "", "banos": f.get("banos") or "", "niveles": f.get("niveles") or "",
        "lat": f.get("lat") or "", "lon": f.get("lon") or "",
        "foto_principal": foto_con_tamano(f.get("foto"), 1200, 800) if f.get("foto") else "",
        "foto_miniatura": f.get("foto") or "",
        "liga_aciertamax": f.get("liga") or "",
        "liga_ficha_acierta_pro": f"{SITIO}/ficha.html?eb={f['eb']}&op={f['operacion']}",
        "liga_whatsapp": _liga_whatsapp(f),
        "imagen_titular": f"{tipo[:1].upper()}{tipo[1:]} en {op}",
        "imagen_ubicacion": ", ".join(x for x in [f.get("colonia"), f["municipio"]] if x),
        "imagen_datos": _datos_clave(f), "imagen_precio": _txt_precio(f),
        "datos_clave": _datos_clave(f), "hashtags_sugeridos": _hashtags(f),
        "apto_para_publicar": "revisar" if revisar or not f.get("foto") or not precio or not f.get("eb") else "si",
        "nota_calidad": nota, "fecha_inventario": fecha,
    }


def escribir_chatgpt(filas, fecha):
    """Escribe inventario-chatgpt.csv e inventario-chatgpt.xlsx. Devuelve el numero de filas."""
    cols = [c for c, _d in COLUMNAS_CHATGPT]
    registros = [fila_chatgpt(f, fecha) for f in filas]
    registros.sort(key=lambda r: (r["segmento"], r["operacion"], r["municipio"], -(r["precio"] or 0)))
    with open(RUTA_CHATGPT_CSV, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        w.writerows(registros)
    escribir_xlsx(RUTA_CHATGPT_XLSX, registros, fecha)
    return len(registros)


def escribir_xlsx(ruta, registros, fecha):
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.utils import get_column_letter
    cols = [c for c, _d in COLUMNAS_CHATGPT]
    wb = Workbook()
    ws = wb.active
    ws.title = "Inventario"
    ws.append(cols)
    for r in registros:
        ws.append([r[c] for c in cols])
    fuente = Font(name="Arial", size=10)
    cab = Font(name="Arial", size=10, bold=True, color="FFFFFF")
    relleno = PatternFill("solid", fgColor="0F1F3D")
    for celda in ws[1]:
        celda.font, celda.fill = cab, relleno
        celda.alignment = Alignment(vertical="center", wrap_text=True)
    for fila in ws.iter_rows(min_row=2):
        for celda in fila:
            celda.font = fuente
    anchos = {"codigo_eb": 12, "operacion": 10, "segmento": 11, "tipo": 20, "grupo_tipo": 13, "municipio": 20, "colonia": 24,
              "titulo_anuncio": 46, "precio": 14, "precio_texto": 24, "rango_precio": 24, "imagen_titular": 24,
              "imagen_ubicacion": 30, "imagen_datos": 34, "imagen_precio": 24, "datos_clave": 34, "hashtags_sugeridos": 50,
              "nota_calidad": 44, "apto_para_publicar": 12, "foto_principal": 40, "liga_whatsapp": 40,
              "liga_ficha_acierta_pro": 40, "liga_aciertamax": 40, "foto_miniatura": 30}
    for i, c in enumerate(cols, 1):
        ws.column_dimensions[get_column_letter(i)].width = anchos.get(c, 11)
    for c in ("precio", "precio_por_m2", "precio_publicado_por_m2"):
        letra = get_column_letter(cols.index(c) + 1)
        for celda in ws[letra][1:]:
            celda.number_format = "#,##0"
    ws.freeze_panes = "B2"
    ws.auto_filter.ref = ws.dimensions
    ws.row_dimensions[1].height = 30

    gu = wb.create_sheet("Guia de columnas")
    gu.append(["Columna", "Que contiene / como usarla"])
    for c, d in COLUMNAS_CHATGPT:
        gu.append([c, d])
    for celda in gu[1]:
        celda.font, celda.fill = cab, relleno
    for fila in gu.iter_rows(min_row=2):
        for celda in fila:
            celda.font = fuente
            celda.alignment = Alignment(wrap_text=True, vertical="top")
    gu.column_dimensions["A"].width = 26
    gu.column_dimensions["B"].width = 120
    gu.freeze_panes = "A2"

    lee = wb.create_sheet("Leeme")
    lineas = [
        f"Inventario de Acierta Max para publicidad · actualizado el {fecha}",
        "Fuente: aciertamax.com (EasyBroker). Se actualiza el día 3 de cada mes.",
        "Municipios: Guadalajara, Zapopan, San Pedro Tlaquepaque, Tonalá y Tlajomulco de Zúñiga; El Salto solo en comercial.",
        "Usar los filtros de la fila de encabezados (segmento, operación, municipio, tipo, rango_precio...).",
        "Publicar solo filas con apto_para_publicar = si. Las marcadas 'revisar' tienen una duda en el precio.",
        "La clave codigo_eb (EB-XXXXXX) debe ir siempre en el texto: así Wati identifica la propiedad.",
    ]
    for l in lineas:
        lee.append([l])
    lee["A1"].font = Font(name="Arial", size=12, bold=True)
    for fila in lee.iter_rows(min_row=2):
        fila[0].font = fuente
    lee.column_dimensions["A"].width = 110
    wb.move_sheet("Leeme", offset=-2)
    wb.save(ruta)


# ----------------------------------------------------------------------
# PRINCIPAL
# ----------------------------------------------------------------------
# --- Terreno y construcción (para la opinión de valor) ---
# El listado de aciertamax.com solo trae un número de m². La ficha de cada propiedad muestra
# terreno y construcción por separado: se lee cada ficha UNA vez y se guarda en caché
# (herramientas/eb_terrenos.json.gz). Si existiera EASYBROKER_API_KEY se usaría la API.
# Las fichas sin dato se reintentan después de 30 días.
RUTA_CACHE_TERRENOS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "eb_terrenos.json.gz")
_NUM = r"([\d]{1,3}(?:,\d{3})*(?:\.\d+)?|\d+(?:\.\d+)?)"
_U = r"\s*(?:m²|m2|mts²|mts|metros)"
_ET_T = r"(?:tama[ñn]o\s+del\s+terreno|superficie\s+(?:de|del|total\s+de)\s+terreno|[áa]rea\s+de\s+terreno|terreno|lote)"
_ET_C = r"(?:tama[ñn]o\s+de\s+(?:la\s+)?construcci[óo]n|superficie\s+(?:aproximada\s+)?(?:de\s+)?construi(?:da|do)|superficie\s+(?:aproximada\s+)?de\s+construcci[óo]n|[áa]rea\s+(?:de\s+)?constru(?:ida|cci[óo]n)|construcci[óo]n)"
# En orden de confianza: «Terreno: 375 m²» · «375 m² de terreno» · «375 m² Lot Size» · «Terreno 375 m²»
RX_T = [re.compile(_ET_T + r"(?:\s+\w+){0,2}\s*:\s*" + _NUM + _U, re.I),
        re.compile(_NUM + _U + r"\s+de\s+" + _ET_T, re.I),
        re.compile(_NUM + _U + r"\s*(?:lot\s+size|land\s+size)", re.I),
        re.compile(r"(?:lot\s+size|land)\s*:?\s*" + _NUM + _U, re.I),
        re.compile(_ET_T + r"\s+" + _NUM + _U, re.I)]
RX_C = [re.compile(_ET_C + r"(?:\s+\w+){0,2}\s*:\s*" + _NUM + _U, re.I),
        re.compile(_NUM + _U + r"\s+de\s+" + _ET_C, re.I),
        re.compile(_NUM + _U + r"\s*(?:construction(?:\s+size)?|built|construidos)", re.I),
        re.compile(r"construction(?:\s+size)?\s*:?\s*" + _NUM + _U, re.I),
        re.compile(_ET_C + r"\s+" + _NUM + _U, re.I)]


def terreno_desde_html(html):
    """(terreno, construccion) leídos del texto de la ficha; None si no aparecen."""
    texto = BeautifulSoup(html, "html.parser").get_text(" ", strip=True)
    def leer(patrones, lo, hi):
        for rx in patrones:
            for m in rx.finditer(texto):
                try:
                    v = float(m.group(1).replace(",", ""))
                except ValueError:
                    continue
                if lo <= v <= hi:
                    return round(v, 2)
        return None
    return leer(RX_T, 10, 2_000_000), leer(RX_C, 10, 200_000)


def _cargar_cache_terrenos():
    import gzip
    if os.path.exists(RUTA_CACHE_TERRENOS):
        try:
            with gzip.open(RUTA_CACHE_TERRENOS, "rt", encoding="utf-8") as fh:
                return json.load(fh)
        except Exception:
            pass
    return {}


def _guardar_cache_terrenos(cache):
    import gzip
    with gzip.open(RUTA_CACHE_TERRENOS, "wt", encoding="utf-8") as fh:
        json.dump(cache, fh, separators=(",", ":"))


def enriquecer_terrenos(filas, max_consultas=4000, pausa=0.3):
    import time as _t
    clave_api = os.environ.get("EASYBROKER_API_KEY", "").strip()
    cache = _cargar_cache_terrenos()
    hoy = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    hace30 = (datetime.now(timezone.utc) - timedelta(days=30)).strftime("%Y-%m-%d")
    hechas = encontradas = 0
    s = requests.Session()
    if clave_api:
        s.headers.update({"X-Authorization": clave_api, "Accept": "application/json"})
    vistos = set()
    for f in filas:
        eb = f.get("eb") or ""
        if not eb.startswith("EB-") or eb in vistos or hechas >= max_consultas:
            continue
        vistos.add(eb)
        c = cache.get(eb)
        if c and (c.get("t") is not None or c.get("c") is not None or c.get("f", "") >= hace30):
            continue
        hechas += 1
        dato = None
        if clave_api:
            for ruta in (f"/properties/{eb}", f"/mls_properties/{eb}"):
                try:
                    r = s.get("https://api.easybroker.com/v1" + ruta, timeout=20)
                except requests.RequestException:
                    continue
                if r.ok:
                    j = r.json(); dato = {"t": j.get("lot_size"), "c": j.get("construction_size"), "f": hoy}
                    break
        elif f.get("liga"):
            resp = get_con_reintentos(s, f["liga"])
            if resp is not None:
                te, co = terreno_desde_html(resp.text)
                if te or co:
                    dato = {"t": te, "c": co, "f": hoy}
        cache[eb] = dato or {"t": None, "c": None, "f": hoy}
        encontradas += 1 if dato else 0
        if hechas % 250 == 0:
            _guardar_cache_terrenos(cache)
            print(f"  terrenos: {hechas} fichas leídas ({encontradas} con dato)", flush=True)
        _t.sleep(pausa)
    if hechas:
        _guardar_cache_terrenos(cache)
    con = 0
    for f in filas:
        c = cache.get(f.get("eb") or "")
        if not c:
            continue
        if c.get("t"):
            f["terreno"] = round(float(c["t"]), 2); con += 1
        if c.get("c"):
            f["construccion"] = round(float(c["c"]), 2)
    if hechas >= 20 and encontradas == 0:
        print("[AVISO] Ninguna ficha mostró terreno ni construcción: revisar el formato de las fichas de aciertamax.com", flush=True)
    print(f"Terrenos: {hechas} fichas consultadas ({encontradas} con dato) · {con} propiedades con terreno en total"
          + (" · vía API" if clave_api else " · vía fichas de aciertamax.com"), flush=True)
    return con


def solo_terrenos(max_consultas):
    """Completa terreno y construcción en data.json sin volver a recorrer el inventario."""
    filas = cargar_previo(RUTA_DATA)
    if not filas:
        print("No hay data.json"); return
    antes = sum(1 for f in filas if f.get("terreno"))
    enriquecer_terrenos(filas, max_consultas=max_consultas)
    with open(RUTA_DATA, "w", encoding="utf-8") as fh:
        json.dump(filas, fh, ensure_ascii=False, separators=(",", ":"))
    print(f"data.json: {antes} → {sum(1 for f in filas if f.get('terreno'))} propiedades con terreno", flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--paginas-max", type=int, default=0, help="limita paginas por municipio/operacion (pruebas)")
    ap.add_argument("--sin-escribir", action="store_true", help="no escribe data.json (pruebas)")
    ap.add_argument("--solo-exportar", action="store_true",
                    help="no rastrea ni cambia data.json: solo regenera el archivo para ChatGPT (CSV y Excel)")
    ap.add_argument("--reusar-data", action="store_true",
                    help="no rastrea: aplica 4 municipios, segmento y guardas de precio a data.json existente")
    ap.add_argument("--solo-terrenos", type=int, default=0, help="solo completa terrenos en data.json (máximo de fichas a leer)")
    args = ap.parse_args()
    if args.solo_terrenos:
        return solo_terrenos(args.solo_terrenos)

    ahora = datetime.now(timezone.utc)
    fecha = ahora.strftime("%Y-%m-%d")
    previo = cargar_previo(RUTA_DATA)
    if args.solo_exportar:
        n = escribir_chatgpt(previo, fecha)
        print(f"Archivo para ChatGPT regenerado: {n:,} fichas -> {RUTA_CHATGPT_CSV} y {RUTA_CHATGPT_XLSX}")
        return
    # Las fichas de NeoJaus (bolsa AMPI) las agrega después herramientas/neojaus_sync.py:
    # aquí se ignoran para que los frenos y la comparación sean solo de EasyBroker.
    previo = [p for p in previo if p.get("fuente") != "neojaus"]
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
    conversiones, total_en_realidad = [], []
    for f in filas:
        aviso_m2 = sanear_m2(f)
        via_pm2, motivo_pm2, bloquea_pm2 = resolver_precio_por_m2(f)
        notas, revisar = [], False
        if bloquea_pm2:
            nivel, motivo = "bloquea", motivo_pm2
        else:
            nivel, motivo = evaluar_precio(f)
            if via_pm2 in ("anuncio", "inferido"):
                conversiones.append((f, via_pm2, motivo_pm2))
            if via_pm2 == "anuncio":
                notas.append(f"Precio total calculado: ${f['pm2_pub']:,.0f} por m2 x {f['m2']:,.0f} m2")
            if via_pm2 in ("inferido", "total"):
                if via_pm2 == "total":
                    total_en_realidad.append(f)
                motivo = (motivo + " | " if motivo else "") + motivo_pm2
                revisar = True
                if nivel == "ok":
                    nivel = "aviso"
            if nivel == "aviso":
                revisar = True
        if revisar and motivo:
            notas.append(motivo)
        if aviso_m2:
            motivo = (motivo + " | " if motivo else "") + aviso_m2
            notas.append(aviso_m2 + " (no mencionar m2)")
            if nivel == "ok":
                nivel = "aviso"
        f["_nota"] = " | ".join(notas)
        f["_revisar"] = revisar
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
    salida = []
    for f in publicables:
        fila_pub = {k: v for k, v in f.items() if not k.startswith("_")}
        if f.get("_nota"):
            fila_pub["nota"] = f["_nota"]
        if f.get("_revisar"):
            fila_pub["revisar"] = True
        salida.append(fila_pub)
    if not args.reusar_data:
        enriquecer_terrenos(salida)
    os.makedirs(DIR_REPORTES, exist_ok=True)
    if not args.sin_escribir:
        with open(RUTA_DATA, "w", encoding="utf-8") as fh:
            json.dump(salida, fh, ensure_ascii=False, separators=(",", ":"))
        escribir_csv(RUTA_CSV, salida)
        escribir_chatgpt(publicables, fecha)
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
        f"- Anuncios que dicen 'por m2' pero el numero ya era el total (error de captura en EasyBroker, se publican tal cual con aviso): "
        f"{sum(1 for f in total_en_realidad if f in publicables)}",
        f"- Fotos rescatadas desde la pagina de detalle: {rescatadas}",
        f"- Fichas sin foto: {len(sin_foto)} "
        + ("(sin rastreo / FRENO: no se descartaron)" if freno_foto else f"(descartadas del sitio: {len(descartadas_sin_foto)})"),
        f"- Fuera de zona descartadas: {fuera_zona} | Duplicadas: {duplicadas}",
        *([f"- AVISO tope EasyBroker: {a}" for a in AVISOS_TOPE] or ["- Tope de 100 paginas de EasyBroker: cubierto con doble pasada donde hizo falta"]),
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

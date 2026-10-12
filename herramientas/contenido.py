"""Registro de contenido para MAX (contenido.json) y huella en los botones de WhatsApp del blog.
- contenido.json: artículos del blog, ediciones del PULSO y campañas de redes (herramientas/campanas.json), con su texto.
- En cada artículo: los enlaces a WhatsApp llevan «(BLOG: slug)» y se agrega el botón «Pregúntale a MAX sobre este tema».
Se corre en la tarea diaria; es idempotente."""
import json, os, re, html, urllib.parse
RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WA = "523333777337"


def texto_de(h, limite=3500):
    h = re.sub(r"<(script|style|header|footer|nav)[^>]*>.*?</\1>", " ", h, flags=re.S | re.I)
    m = re.search(r"<(article|main)[^>]*>(.*?)</\1>", h, re.S | re.I)
    cuerpo = m.group(2) if m else h
    t = html.unescape(re.sub(r"<[^>]+>", " ", cuerpo))
    return re.sub(r"\s+", " ", t).strip()[:limite]


def meta(h, nombre):
    m = re.search(rf'<meta (?:name|property)="{nombre}" content="([^"]*)"', h)
    return html.unescape(m.group(1)) if m else ""


BOTON = ('<a class="max-tema" data-max-tema href="{url}" target="_blank" rel="noopener" '
         'style="position:fixed;left:16px;bottom:16px;z-index:999;display:flex;align-items:center;gap:8px;background:#25D366;color:#fff;'
         'font:700 14px Inter,system-ui,sans-serif;padding:12px 16px;border-radius:999px;box-shadow:0 6px 18px rgba(0,0,0,.25);text-decoration:none">'
         '💬 Pregúntale a MAX sobre este tema</a>')


def main():
    items = []
    for f in sorted(os.listdir(os.path.join(RAIZ, "blog"))):
        if not f.endswith(".html") or f == "index.html":
            continue
        ruta = os.path.join(RAIZ, "blog", f)
        h = open(ruta, encoding="utf-8").read()
        slug = f[:-5]
        tit = re.sub(r"\s*[|·–-]\s*Acierta.*$", "", html.unescape(re.search(r"<title>(.*?)</title>", h, re.S).group(1)).strip()) if "<title>" in h else slug
        items.append({"codigo": f"BLOG:{slug}", "tipo": "blog", "titulo": tit, "resumen": meta(h, "description"),
                      "url": f"https://acierta.pro/blog/{f}", "texto": texto_de(h)})
        # huella en los enlaces de WhatsApp
        def poner(m):
            url = html.unescape(m.group(1))
            if f"BLOG: {slug}" in urllib.parse.unquote(url):
                return m.group(0)
            p = urllib.parse.urlparse(url); q = urllib.parse.parse_qs(p.query)
            txt = (q.get("text", ["Hola, quiero más información"])[0]).strip()
            txt = f"{txt} (vengo del artículo «{tit[:70]}» de acierta.pro · BLOG: {slug})"
            return f'href="https://wa.me/{WA}?text={urllib.parse.quote(txt)}"'
        h2 = re.sub(r'href="(https://wa\.me/' + WA + r'[^"]*)"', poner, h)
        if "data-max-tema" not in h2:
            txt = f"Hola, leí «{tit[:70]}» en acierta.pro y quiero más información (BLOG: {slug})"
            h2 = h2.replace("</body>", BOTON.format(url=f"https://wa.me/{WA}?text={urllib.parse.quote(txt)}") + "\n</body>", 1)
        if h2 != h:
            open(ruta, "w", encoding="utf-8").write(h2)
    try:
        eds = json.load(open(os.path.join(RAIZ, "pulso", "ediciones.json"), encoding="utf-8"))["ediciones"]
    except Exception:
        eds = []
    for e in eds:
        n = e["numero"]; pag = os.path.join(RAIZ, "pulso", f"edicion-{n}.html")
        items.append({"codigo": f"PULSO-{n}", "tipo": "pulso", "titulo": e.get("tema", ""), "publicar_desde": e.get("publicar_desde", ""),
                      "url": f"https://acierta.pro/pulso/edicion-{n}.html",
                      "texto": texto_de(open(pag, encoding="utf-8").read()) if os.path.exists(pag) else ""})
    try:
        for c in json.load(open(os.path.join(RAIZ, "herramientas", "campanas.json"), encoding="utf-8"))["campanas"]:
            items.append({"codigo": c["codigo"].upper(), "tipo": "campana", "titulo": c["titulo"], "texto": c["texto"], "relacionado": c.get("relacionado", "")})
    except Exception as ex:
        print("campanas.json:", ex)
    json.dump({"actualizado": __import__("datetime").date.today().isoformat(), "contenido": items},
              open(os.path.join(RAIZ, "contenido.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"Contenido para MAX: {sum(1 for i in items if i['tipo']=='blog')} artículos, {sum(1 for i in items if i['tipo']=='pulso')} PULSO, "
          f"{sum(1 for i in items if i['tipo']=='campana')} campañas")


if __name__ == "__main__":
    main()

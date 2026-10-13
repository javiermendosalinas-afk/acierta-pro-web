"""Publica una edición del PULSO programada para su fecha.
Uso: python herramientas/pulso_nueva.py NUM ARCHIVO.pdf AAAA-MM-DD [REEL.mp4]
Hace: PDF optimizado (solo fotos; el logo intacto), portada, reel (si viene), imágenes del visor,
página web (oculta para Google hasta la fecha), entrada en pulso/ediciones.json y tarjeta en pulso.html."""
import sys, os, io, re, json, html, subprocess
import pymupdf
from PIL import Image
RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MESES = ["", "enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]
E = lambda s: html.escape(str(s or ""), quote=True)


def optimizar(src, dst):
    d = pymupdf.open(src); hechos = set()
    for page in d:
        for img in page.get_images(full=True):
            xref, smask = img[0], img[1]
            if xref in hechos or smask:
                hechos.add(xref); continue
            hechos.add(xref)
            pix = pymupdf.Pixmap(d, xref)
            if pix.width * pix.height < 150000:
                continue
            if pix.n - pix.alpha >= 4 or pix.alpha:
                pix = pymupdf.Pixmap(pymupdf.csRGB, pix)
            im = Image.frombytes("RGB" if pix.n >= 3 else "L", (pix.width, pix.height), pix.samples)
            im.thumbnail((1400, 1400))
            b = io.BytesIO(); im.convert("RGB").save(b, "JPEG", quality=74, optimize=True)
            page.replace_image(xref, stream=b.getvalue())
    d.save(dst, garbage=4, deflate=True, clean=True)


def textos(src):
    """Por página: (encabezado, párrafo) sin pies de página."""
    out = []
    for i, p in enumerate(pymupdf.open(src)):
        lineas = [re.sub(r"\s+", " ", l).strip() for l in p.get_text().split("\n")]
        lineas = [l for l in lineas if l and not re.search(r"acierta\.pro\s*\|\s*whatsapp|^\d{1,2}$|^pulso\s*\d+(\s*·\s*\d+)?$|simulaci[oó]n con ia|historia ficticia", l, re.I)]
        if not lineas:
            continue
        if i == 0:
            lineas = [l for l in lineas if not re.match(r"^(edici[oó]n|pulso)\s*\d", l, re.I) and not re.search(r"\b20\d\d\b", l)]
        enc = lineas[0] if lineas else ""
        cuerpo = " ".join(lineas[1:])
        out.append((enc, cuerpo))
    return out


def titulo_de(src):
    p = pymupdf.open(src)[0]
    bloques = []
    for b in p.get_text("dict")["blocks"]:
        for l in b.get("lines", []):
            for s in l["spans"]:
                t = s["text"].strip()
                if t and not re.match(r"^(edici[oó]n|pulso)\b", t, re.I) and not re.search(r"\b20\d\d\b|simulaci|ficticia|acierta", t, re.I):
                    bloques.append((round(s["size"]), t))
    if not bloques:
        return ""
    mayor = max(sz for sz, _ in bloques)
    t = " ".join(t for sz, t in bloques if sz >= mayor - 1)
    t = re.sub(r"\s+", " ", t).strip()
    return t[:1].upper() + t[1:].lower() if t.isupper() else t


def main(num, pdf, fecha, reel=None):
    num = f"{int(num):02d}"
    anio, mes, _ = fecha.split("-")
    mes_n = MESES[int(mes)]
    base = f"pulso-{num}-{mes_n}-{anio}"
    dst = os.path.join(RAIZ, "assets", "pulso", base + ".pdf")
    optimizar(pdf, dst)
    pymupdf.open(pdf)[0].get_pixmap(dpi=130).save(os.path.join(RAIZ, "assets", "pulso", f"pulso-{num}-portada.jpg"), jpg_quality=82)
    if reel:
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", reel, "-vf", "scale=720:-2", "-c:v", "libx264", "-preset", "slow", "-crf", "28",
                        "-c:a", "aac", "-b:a", "96k", "-movflags", "+faststart", os.path.join(RAIZ, "assets", "pulso", f"pulso-{num}-reel.mp4")], check=True)
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", "2", "-i", os.path.join(RAIZ, "assets", "pulso", f"pulso-{num}-reel.mp4"),
                        "-frames:v", "1", "-q:v", "4", os.path.join(RAIZ, "assets", "pulso", f"pulso-{num}-reel.jpg")], check=True)
    tema = titulo_de(pdf)
    paginas = pymupdf.open(pdf).page_count
    secciones = textos(pdf)
    desc = (secciones[0][1] if secciones else tema)[:300]
    # ediciones.json
    rj = os.path.join(RAIZ, "pulso", "ediciones.json"); d = json.load(open(rj, encoding="utf-8"))
    ent = {"numero": num, "fecha": f"{anio}-{mes}", "publicar_desde": fecha, "titulo": f"PULSO Acierta Max · Edición {num} · {mes_n.capitalize()} {anio}",
           "tema": tema, "archivo": f"PULSO_Acierta_Max_{num}.pdf", "url": f"https://acierta.pro/assets/pulso/{base}.pdf",
           "pdf_raw": f"https://raw.githubusercontent.com/javiermendosalinas-afk/acierta-pro-web/main/assets/pulso/{base}.pdf?v=1",
           "portada": f"/assets/pulso/pulso-{num}-portada.jpg", "vigente": True, "enviar_correo": False, "version_pdf": 1, "palabras": []}
    if reel:
        ent["reel"] = f"/assets/pulso/pulso-{num}-reel.mp4"
    d["ediciones"] = [e for e in d["ediciones"] if e.get("numero") != num] + [ent]
    d["ediciones"].sort(key=lambda e: (e.get("publicar_desde") or "0000", e["numero"]), reverse=True)
    json.dump(d, open(rj, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    # página web (a partir de la plantilla de una edición existente)
    plantilla = open(os.path.join(RAIZ, "pulso", "edicion-14.html"), encoding="utf-8").read()
    cab = plantilla[:plantilla.index("<main")]; pie = plantilla[plantilla.index("</main>"):]
    tit = f"PULSO {num}: {tema}"
    cab = re.sub(r"<title>.*?</title>", f"<title>{E(tit)} | Acierta Max</title>", cab, flags=re.S)
    cab = re.sub(r'<meta name="description" content="[^"]*">', f'<meta name="description" content="{E(desc[:158])}">', cab)
    cab = re.sub(r'data-pulso-programado="[^"]*"', f'data-pulso-programado="{fecha}"', cab)
    cab = cab.replace("edicion-14.html", f"edicion-{num}.html").replace("pulso-14-portada.jpg", f"pulso-{num}-portada.jpg").replace("PULSO%2014", f"PULSO%20{int(num)}")
    cab = re.sub(r'<meta property="og:title" content="[^"]*">', f'<meta property="og:title" content="{E(tit)}">', cab)
    ld = re.search(r'<script type="application/ld\+json">(.*?)</script>', cab, re.S).group(1); j = json.loads(ld)
    j.update({"headline": tit, "description": desc, "datePublished": fecha, "dateModified": fecha, "image": [f"https://acierta.pro/assets/pulso/pulso-{num}-portada.jpg"]})
    cab = cab.replace(ld, json.dumps(j, ensure_ascii=False))
    cuerpo = "".join(f"<section class='seo-card'><h2>{E(h)}</h2><p>{E(c)}</p></section>" for h, c in secciones[1:] if c)
    main_ = (f'<main class="seo-wrap"><nav class="migas"><a href="/">Inicio</a> › <a href="/pulso.html">PULSO</a> › Edición {num}</nav>'
             f'<div class="pw-top"><img src="/assets/pulso/pulso-{num}-portada.jpg" alt="Portada del PULSO {num}" width="720"><div>'
             f'<div class="seo-eyebrow">PULSO Acierta Max · Edición {num}</div><h1>{E(tema)}</h1><p class="muted">{mes_n.capitalize()} {anio} · Por Javier Mendoza Salinas</p>'
             f'<p>{E(desc)}</p><div class="seo-cta"><a class="btn-solid btn-lg" href="/assets/pulso/{base}.pdf" target="_blank" rel="noopener">Descargar el PDF completo</a> '
             f'<a class="btn-outline btn-lg" href="https://wa.me/523333777337?text=PULSO%20{int(num)}" target="_blank" rel="noopener">Recibirlo por WhatsApp</a> '
             f'<a class="btn-outline btn-lg" href="/pulso/ver.html?ed={num}">Verlo en pantalla</a></div></div></div>{cuerpo}'
             f'<section class="seo-card"><h2>Da el siguiente paso</h2><p>Escribe <b>PULSO {int(num)}</b> al <a href="https://wa.me/523333777337?text=PULSO%20{int(num)}">33 3377 7337</a> '
             'y un asesor te ayuda con tus números. Antes de firmar, pide <b>Acierta Verifica</b>.</p></section>\n')
    open(os.path.join(RAIZ, "pulso", f"edicion-{num}.html"), "w", encoding="utf-8").write(cab + main_ + pie)
    # tarjeta en pulso.html, ordenada por fecha
    ph = os.path.join(RAIZ, "pulso.html"); t = open(ph, encoding="utf-8").read()
    t = re.sub(rf'<article class="pu-ed vig" hidden data-desde="[^"]*"><div class="pu-ed-media"><img src="assets/pulso/pulso-{num}-portada\.jpg".*?</article>', "", t, flags=re.S)
    reel_html = (f'<details class="pu-reel"><summary>Ver el reel de esta edición</summary><video controls playsinline preload="none" poster="assets/pulso/pulso-{num}-reel.jpg" '
                 f'src="assets/pulso/pulso-{num}-reel.mp4"></video></details>') if reel else ""
    tarjeta = (f'<article class="pu-ed vig" hidden data-desde="{fecha}"><div class="pu-ed-media"><img src="assets/pulso/pulso-{num}-portada.jpg" alt="Portada del PULSO {num}" loading="lazy" width="720"></div>'
               f'<div class="pu-ed-body"><span class="pu-ed-n">EDICIÓN {num} · LA MÁS RECIENTE</span><h3>{E(tema)}</h3><p>{E(desc[:240])}</p>'
               f'<div class="pu-ed-acc"><a class="pu-cta" href="assets/pulso/{base}.pdf" target="_blank" rel="noopener">Descargar PDF · {paginas} páginas</a> '
               f'<a class="pu-cta verde" href="https://wa.me/523333777337?text=PULSO%20{int(num)}" target="_blank" rel="noopener">Recibir en WhatsApp</a> '
               f'<a class="pu-cta" style="background:#0b1f3a" href="pulso/edicion-{num}.html">Leer en la web</a> '
               f'<a class="pu-cta" style="background:#d62828" href="pulso/ver.html?ed={num}">Ver en pantalla</a></div>{reel_html}</div></article>')
    marcas = [(m.start(), m.group(1)) for m in re.finditer(r'<article class="pu-ed vig" hidden data-desde="([^"]*)">', t)]
    pos = next((p for p, f in marcas if f < fecha), None)
    if pos is None:
        pos = t.index('<article class="pu-ed vig">') if '<article class="pu-ed vig">' in t else t.index('<div class="pu-eds">') + len('<div class="pu-eds">')
    t = t[:pos] + tarjeta + t[pos:]
    open(ph, "w", encoding="utf-8").write(t)
    print(f"PULSO {num} · {fecha} · {paginas} págs · PDF {os.path.getsize(dst)/1048576:.2f} MB · «{tema}»")


if __name__ == "__main__":
    main(*sys.argv[1:5])

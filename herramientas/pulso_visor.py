"""Genera las imágenes del visor del PULSO (assets/pulso/visor/<num>/pNN.jpg) desde el PDF de cada edición
y anota el número de páginas en pulso/ediciones.json. Correr al publicar o reemplazar una edición."""
import json, os, sys
import pymupdf
from PIL import Image
RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ruta = os.path.join(RAIZ, "pulso", "ediciones.json")
d = json.load(open(ruta, encoding="utf-8"))
solo = set(sys.argv[1:])
for e in d["ediciones"]:
    n = e["numero"]
    if solo and n not in solo:
        continue
    pdf = os.path.join(RAIZ, e["url"].split("acierta.pro/")[1])
    if not os.path.exists(pdf):
        print("sin PDF:", n); continue
    carpeta = os.path.join(RAIZ, "assets", "pulso", "visor", n)
    os.makedirs(carpeta, exist_ok=True)
    for f in os.listdir(carpeta):
        os.remove(os.path.join(carpeta, f))
    doc = pymupdf.open(pdf)
    total = 0
    for i, pag in enumerate(doc, start=1):
        ancho = pag.rect.width
        pix = pag.get_pixmap(matrix=pymupdf.Matrix(760 / ancho, 760 / ancho))
        im = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
        destino = os.path.join(carpeta, f"p{i:02d}.jpg")
        im.save(destino, "JPEG", quality=72, optimize=True, progressive=True)
        total += os.path.getsize(destino)
    e["paginas"] = doc.page_count
    e["formato"] = "vertical" if doc[0].rect.height / doc[0].rect.width > 1.5 else "carta"
    print(f"PULSO {n}: {doc.page_count} páginas, {total/1048576:.1f} MB, {e['formato']}")
json.dump(d, open(ruta, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

"""Integra las portadas de Canva a los artículos del blog.

Uso: python3 herramientas/blog/portadas.py <carpeta_con_jpg_exportados>
Cada JPG debe llamarse <slug>.jpg (igual que blog/<slug>.html).
Genera assets/blog/<slug>.jpg (vertical, para redes) y <slug>-og.jpg (1200x630,
vista previa al compartir la liga) y actualiza metas, JSON-LD, índice y sitemap.
Es idempotente: se puede volver a correr sin duplicar nada.
"""
import json, re, sys, pathlib
from PIL import Image, ImageFilter, ImageEnhance

RAIZ = pathlib.Path(__file__).resolve().parents[2]
SITIO = "https://acierta.pro"
ORIGEN = pathlib.Path(sys.argv[1])
DEST = RAIZ / "assets" / "blog"; DEST.mkdir(parents=True, exist_ok=True)

def imagenes(slug):
    im = Image.open(ORIGEN / f"{slug}.jpg").convert("RGB")
    im.save(DEST / f"{slug}.jpg", quality=82, optimize=True, progressive=True)
    W, H = 1200, 630
    fondo = im.resize((W, int(im.height * W / im.width))).crop((0, 0, W, H))
    fondo = ImageEnhance.Brightness(fondo.filter(ImageFilter.GaussianBlur(28))).enhance(0.75)
    h = H - 30; w = int(im.width * h / im.height)
    fondo.paste(im.resize((w, h), Image.LANCZOS), ((W - w) // 2, 15))
    fondo.save(DEST / f"{slug}-og.jpg", quality=84, optimize=True, progressive=True)

def articulo(slug):
    p = RAIZ / "blog" / f"{slug}.html"; t = p.read_text(encoding="utf-8")
    og, vert = f"{SITIO}/assets/blog/{slug}-og.jpg", f"{SITIO}/assets/blog/{slug}.jpg"
    titulo = re.search(r"<h1>(.*?)</h1>", t, re.S).group(1).strip()
    t = re.sub(r'(<meta property="og:image" content=")[^"]*(">)', rf"\g<1>{og}\g<2>", t)
    t = re.sub(r'(<meta name="twitter:image" content=")[^"]*(">)', rf"\g<1>{og}\g<2>", t)
    t = re.sub(r'\n<meta property="og:image:(width|height|alt)"[^>]*>', "", t)
    t = t.replace(f'<meta property="og:image" content="{og}">',
        f'<meta property="og:image" content="{og}">\n<meta property="og:image:width" content="1200">'
        f'\n<meta property="og:image:height" content="630">\n<meta property="og:image:alt" content="{titulo}">', 1)
    # JSON-LD Article: imagen
    t = re.sub(r'\n  "image": \[[^\]]*\],', "", t)
    t = t.replace('"@type": "Article",', f'"@type": "Article",\n  "image": ["{og}", "{vert}"],', 1)
    p.write_text(t, encoding="utf-8")

def indice(slugs):
    p = RAIZ / "blog" / "index.html"; t = p.read_text(encoding="utf-8")
    for s in slugs:
        patron = re.compile(rf'(<a class="blog-card" href="/blog/{re.escape(s)}\.html">\s*<div class="blog-card-media)(?: has-img)?(">)(?:<img[^>]*>)?')
        t, n = patron.subn(rf'\1 has-img\2<img src="/assets/blog/{s}.jpg" alt="" loading="lazy" width="1080" height="1440">', t)
        assert n == 1, f"tarjeta no encontrada en el índice: {s}"
    p.write_text(t, encoding="utf-8")

def sitemap(slugs):
    p = RAIZ / "sitemap.xml"; t = p.read_text(encoding="utf-8")
    if "xmlns:image" not in t:
        t = t.replace('xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"',
            'xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:image="http://www.google.com/schemas/sitemap-image/1.1"')
    for s in slugs:
        loc = f"<loc>{SITIO}/blog/{s}.html</loc>"
        t = re.sub(rf"({re.escape(loc)})<image:image>.*?</image:image>", r"\1", t)
        assert loc in t, f"no está en sitemap: {s}"
        t = t.replace(loc, f"{loc}<image:image><image:loc>{SITIO}/assets/blog/{s}.jpg</image:loc></image:image>")
    p.write_text(t, encoding="utf-8")

CSS = """
/* Portadas de artículos (Canva) */
.blog-card-media.has-img { padding: 0; min-height: 0; aspect-ratio: 4 / 3; overflow: hidden; background: #f7f5f0; }
.blog-card-media.has-img img { width: 100%; height: 100%; object-fit: cover; object-position: top; display: block; }
.blog-card-media.has-img .blog-card-cat { position: absolute; left: 12px; bottom: 12px; }
"""

if __name__ == "__main__":
    slugs = sorted(f.stem for f in ORIGEN.glob("*.jpg"))
    for s in slugs: imagenes(s); articulo(s)
    indice(slugs); sitemap(slugs)
    css = RAIZ / "blog-styles.css"; c = css.read_text(encoding="utf-8")
    if "Portadas de artículos" not in c: css.write_text(c + CSS, encoding="utf-8")
    print(f"{len(slugs)} portadas integradas")

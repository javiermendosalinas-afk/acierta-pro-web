# ── Limpieza de calidad del inventario (se aplica en cada actualización) ──
import re as _re, unicodedata as _ud

_NO_VIVIENDA = _re.compile(r"\b(cripta|fosa|panteon|gaveta|nicho|osario|lote funerario|mausoleo)\b")
_MINUS = {"de", "del", "la", "las", "el", "los", "en", "y", "e", "o", "u", "a", "al", "con", "para", "por", "sin", "su", "sus", "un", "una"}
_SIGLAS = {"gdl", "zmg", "iva", "cfe", "siapa", "itesp", "iteso", "udg", "uag", "tec", "uvm", "nj", "eb", "m2", "m²", "ii", "iii", "iv", "vip", "ac", "sa", "cv"}


def _sin_acentos(s):
    return _ud.normalize("NFKD", str(s or "")).encode("ascii", "ignore").decode().lower()


def titulo_legible(t):
    """Títulos escritos TODO EN MAYÚSCULAS → formato de título (las siglas se respetan)."""
    t = _re.sub(r"\s+", " ", str(t or "")).strip(" -·,.!")
    letras = [c for c in t if c.isalpha()]
    if not letras or sum(c.isupper() for c in letras) / len(letras) < 0.7:
        return t
    pal = t.lower().split(" ")
    out = []
    for i, w in enumerate(pal):
        base = _sin_acentos(w).strip(",.;:!¡¿?()")
        if base in _SIGLAS:
            out.append(w.upper())
        elif i > 0 and base in _MINUS:
            out.append(w)
        else:
            out.append(w[:1].upper() + w[1:])
    return " ".join(out)


def limpiar_inventario(filas):
    """Devuelve (filas_limpias, resumen). Nunca inventa datos: quita lo imposible y marca lo dudoso."""
    res = {"fuera_no_vivienda": 0, "terrenos_corregidos": 0, "marcadas_revisar": 0, "titulos": 0}
    salida = []
    for f in filas:
        tit, tipo = f.get("titulo") or "", _sin_acentos(f.get("tipo"))
        if _NO_VIVIENDA.search(_sin_acentos(tit)):
            res["fuera_no_vivienda"] += 1
            continue
        if any(k in tipo for k in ("terreno", "lote")):
            if f.get("recamaras") or f.get("banos"):
                f["recamaras"] = None; f["banos"] = None; res["terrenos_corregidos"] += 1
        elif any(k in tipo for k in ("casa", "depart", "loft")):
            rec, ban, m2 = f.get("recamaras") or 0, f.get("banos") or 0, f.get("m2") or 0
            dudoso = rec > 9 or ban > 9 or (m2 and m2 < 20) or (rec and m2 and m2 / rec < 12)
            if dudoso and not f.get("revisar"):
                f["revisar"] = True
                f["nota"] = ((f.get("nota") or "") + " · datos fuera de rango (recámaras, baños o superficie)").strip(" ·")
                res["marcadas_revisar"] += 1
        nt = titulo_legible(tit)
        if nt != tit:
            f["titulo"] = nt; res["titulos"] += 1
        salida.append(f)
    return salida, res

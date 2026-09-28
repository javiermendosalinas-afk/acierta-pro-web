#!/usr/bin/env python3
"""Genera el archivo de datos de un "Estudio de oportunidad de inversión" (reportes/<slug>.json)
a partir de data.json. La página reporte-inversion.html lo dibuja.

Método (todo con el inventario de Acierta Max):
  - Candidatos: departamentos EN VENTA en la zona dibujada, en pesos, hasta el presupuesto.
  - Renta esperada: mediana de renta por m² de departamentos EN RENTA a 1, 1.5 o 2 km (recámaras ±1,
    tamaño ±35%, mínimo 5 comparables). Sin comparables locales suficientes => no se evalúa.
  - Precio frente a vecinos: mediana de precio por m² de ventas cercanas (mínimo 8).
  - Puntaje: 50% rendimiento neto + 30% descuento frente a vecinos + 20% confiabilidad de los comparables.
  - Precios de lista (no de cierre). Rendimiento antes de ISR por rentas. Sin administración.

Uso: python3 herramientas/reporte_inversion.py --nombre Karla --tope 3500000 --slug karla-7f3a9c
"""
import argparse, json, math, os, statistics as st, sys, unicodedata

SUPUESTOS = dict(compra=0.06, venta=0.05, mantenimiento=0.010, predial=0.0015, vacancia=1/12,
                 inpc=0.0376, cetes=0.065, plusvalia_base=0.06, plusvalia_alta=0.10)

def norm(s): return ''.join(c for c in unicodedata.normalize('NFD', str(s or '')) if unicodedata.category(c) != 'Mn').lower().strip()
def med(x): return st.median(x) if x else None
def km(a, b):
    la1, lo1, la2, lo2 = map(math.radians, (a['lat'], a['lon'], b['lat'], b['lon']))
    h = math.sin((la2-la1)/2)**2 + math.cos(la1)*math.cos(la2)*math.sin((lo2-lo1)/2)**2
    return 2*6371*math.asin(math.sqrt(h))

def tir(flujos):
    lo, hi = -0.9, 1.0
    for _ in range(200):
        m = (lo+hi)/2; v = sum(f/(1+m)**t for t, f in enumerate(flujos)); lo, hi = (m, hi) if v > 0 else (lo, m)
    return m

def tir_prop(P, renta_anual, g, n, S=SUPUESTOS):
    inv = P*(1+S['compra']); fl = [-inv]
    for a in range(1, n+1):
        val = P*(1+g)**(a-1)
        r = renta_anual*(1+S['inpc'])**(a-1)*(1-S['vacancia']) - val*(S['mantenimiento']+S['predial'])
        if a == n: r += P*(1+g)**n*(1-S['venta'])
        fl.append(r)
    return tir(fl)

def g_equilibrio(P, ra, n, S=SUPUESTOS):
    lo, hi = -0.05, 0.30
    for _ in range(60):
        m = (lo+hi)/2; lo, hi = (m, hi) if tir_prop(P, ra, m, n, S) < S['cetes'] else (lo, m)
    return m

def plusvalia_sin_ganancia(n, S=SUPUESTOS):
    """Plusvalía anual hasta la cual la ganancia fiscal (simplificada) es cero a n años."""
    return ((1+S['compra'])*(1+S['inpc'])**n/(1-S['venta']))**(1/n)-1

def generar(d, nombre, tope, slug, caja, tipo='departamento'):
    S = SUPUESTOS
    ok = lambda p: p.get('moneda') in (None, 'MXN') and p.get('m2') and 25 <= p['m2'] <= 600 and p['precio'] > 0 and p.get('lat') and p.get('lon')
    enz = lambda p: caja['la0'] < p['lat'] < caja['la1'] and caja['lo0'] < p['lon'] < caja['lo1']
    zona = [p for p in d if ok(p) and p['tipo'] == tipo and enz(p)]
    V = [p for p in zona if p['operacion'] == 'VENTA']; R = [p for p in zona if p['operacion'] == 'RENTA']
    cand = [p for p in V if p['precio'] <= tope]
    pmv = lambda p: p['precio']/p['m2']

    def rent_est(p):
        rec = p.get('recamaras') or 0
        for radio in (1.0, 1.5, 2.0):
            c = [r for r in R if km(p, r) <= radio and (not rec or (r.get('recamaras') and abs(r['recamaras']-rec) <= 1)) and 0.65*p['m2'] <= r['m2'] <= 1.35*p['m2']]
            v = sorted(r['precio']/r['m2'] for r in c)
            if len(v) >= 5:
                if len(v) >= 10: v = v[int(len(v)*.1):int(len(v)*.9)+1]
                return med(v)*p['m2'], len(c), radio
        return None, 0, None
    def vent_med(p):
        rec = p.get('recamaras') or 0
        for radio in (1.0, 1.5, 2.0):
            c = [v for v in V if v is not p and km(p, v) <= radio and (not rec or (v.get('recamaras') and abs(v['recamaras']-rec) <= 1))]
            if len(c) >= 8: return med([pmv(v) for v in c]), len(c)
        return None, 0

    filas, sin_comp = [], 0
    for p in cand:
        re_, nr, radio = rent_est(p); vm, nv = vent_med(p)
        if not re_ or not vm: sin_comp += 1; continue
        ra = re_*12; bruto = ra/p['precio']; neto = bruto*(1-S['vacancia'])-(S['mantenimiento']+S['predial'])
        if bruto > 0.12 or bruto < 0.02: sin_comp += 1; continue
        filas.append(dict(p=p, renta=re_, nr=nr, radio=radio, bruto=bruto, neto=neto, desc=1-pmv(p)/vm, nv=nv, ra=ra))
    def rank(vals):
        o = sorted(range(len(vals)), key=lambda i: vals[i]); r = [0]*len(vals)
        for k, i in enumerate(o): r[i] = k/(len(vals)-1 if len(vals) > 1 else 1)
        return r
    rn = rank([x['neto'] for x in filas]); rd = rank([x['desc'] for x in filas])
    for i, x in enumerate(filas):
        conf = min(x['nr']/8, 1.0)*(1.0 if x['radio'] == 1.0 else 0.8 if x['radio'] == 1.5 else 0.6)
        x['score'] = 0.5*rn[i]+0.3*rd[i]+0.2*conf
    filas.sort(key=lambda x: (-x['score'], x['p']['eb']))

    ph = [p for p in V if norm(p['colonia']) == 'puerta de hierro']
    opciones = []
    for k, x in enumerate(filas[:10], 1):
        p = x['p']; t = norm(p['titulo'] + ' ' + p['liga']); flags = []
        if 'preventa' in t or 'eleva' in t or 'bella vittoria' in t or 'bella-vittoria' in t: flags.append('desarrollo_nuevo')
        if 'bella vittoria' in t or 'bella-vittoria' in t: flags.append('comercializamos')
        generico = len(norm(p['titulo']).split()) <= 3
        # Confianza del estimado de renta/precio: alta = vecinos a 1 km con buena muestra; baja = a 2 km, poca muestra o anuncio sin datos
        if x['radio'] == 1.0 and x['nr'] >= 8 and x['nv'] >= 10 and not generico: confianza = 'alta'
        elif x['radio'] == 2.0 or x['nr'] < 7 or generico: confianza = 'baja'
        else: confianza = 'media'
        opciones.append(dict(rank=k, eb=p['eb'], titulo=p['titulo'], colonia=p['colonia'], municipio=p['municipio'], m2=p['m2'], rec=p.get('recamaras'),
            precio=p['precio'], pm2=round(pmv(p)), lat=p['lat'], lon=p['lon'], foto=p.get('foto'), liga=p['liga'], renta=round(x['renta']),
            renta_anual=round(x['ra']), bruto=round(x['bruto'], 4), neto=round(x['neto'], 4), desc=round(x['desc'], 4), n_venta=x['nv'], n_renta=x['nr'], radio_km=x['radio'],
            tir4=dict(inflacion=round(tir_prop(p['precio'], x['ra'], S['inpc'], 4), 4), base=round(tir_prop(p['precio'], x['ra'], S['plusvalia_base'], 4), 4), alta=round(tir_prop(p['precio'], x['ra'], S['plusvalia_alta'], 4), 4)),
            geq4=round(g_equilibrio(p['precio'], x['ra'], 4), 4), confianza=confianza, flags=flags))
    return dict(version=1, cliente=nombre, slug=slug, generado='septiembre de 2026',
        objetivo=dict(tope=tope, tipo=tipo, horizonte='3 a 4 años', zona='Franja poniente interior del Periférico, de Puerta de Hierro a Las Fuentes'),
        zona_caja=caja,
        inventario=dict(total=len(d), en_zona_venta=len(V), candidatos=len(cand), evaluados=len(filas), sin_comparables=sin_comp, rentas_comparables=len(R)),
        puerta_de_hierro=dict(n=len(ph), minimo=min(p['precio'] for p in ph) if ph else None, mediana_pm2=round(med([pmv(p) for p in ph])) if ph else None),
        mercado=dict(cetes=S['cetes'], cetes_nota='Referencia de CETES (Banxico). Verifica la subasta de la semana.', inflacion=0.0342, inpc_ponderado=S['inpc'],
                     plusvalia_zmg=[dict(t='3T 2025', v=0.1178), dict(t='4T 2025', v=0.1248), dict(t='1T 2026', v=0.1229), dict(t='2T 2026', v=0.0999)], plusvalia_nacional_2t26=0.0731),
        supuestos=S,
        isr=dict(plusvalia_sin_ganancia_3=round(plusvalia_sin_ganancia(3), 4), plusvalia_sin_ganancia_4=round(plusvalia_sin_ganancia(4), 4)),
        mediana_neto_evaluados=round(med([x['neto'] for x in filas]), 4),
        mediana_bruto_evaluados=round(med([x['bruto'] for x in filas]), 4),
        opciones=opciones)

if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--nombre', required=True); ap.add_argument('--tope', type=float, required=True); ap.add_argument('--slug', required=True)
    ap.add_argument('--caja', default='20.615,20.725,-103.432,-103.385', help='lat_min,lat_max,lon_min,lon_max')
    a = ap.parse_args()
    raiz = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    d = json.load(open(os.path.join(raiz, 'data.json'), encoding='utf-8'))
    la0, la1, lo0, lo1 = map(float, a.caja.split(','))
    rep = generar(d, a.nombre, int(a.tope), a.slug, dict(la0=la0, la1=la1, lo0=lo0, lo1=lo1))
    out = os.path.join(raiz, 'reportes', a.slug + '.json')
    json.dump(rep, open(out, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f"{out}: {len(rep['opciones'])} opciones | evaluados {rep['inventario']['evaluados']} de {rep['inventario']['candidatos']}")

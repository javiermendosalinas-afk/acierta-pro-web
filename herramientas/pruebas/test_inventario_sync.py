import os, sys, json, importlib.util, tempfile, shutil, io, contextlib
RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
spec = importlib.util.spec_from_file_location("S", os.path.join(RAIZ, "herramientas", "inventario_sync.py"))
S = importlib.util.module_from_spec(spec); spec.loader.exec_module(S)

fallas = 0
def ok(c, m):
    global fallas
    if not c: fallas += 1
    print(('OK   ' if c else 'FALLA') + ' ' + m)

print("── PARSEO DE TARJETAS")
html = '''
<div class="property-listing" data-lat="20.6" data-long="-103.3"
 data-popover-data='{"price": "$1,500,000 MXN", "title": "Casa bonita", "location": "Casa en condominio en Providencia, San Pedro Tlaquepaque", "bedrooms": "3", "bathrooms": "2.5", "size": "150 m2", "url": "/property/casa-bonita", "image_url": "https://assets.easybroker.com/property_images/1/2/EB-WX1234.jpg?height=300&version=1&width=450"}'>
 <div class="property-photo"><a><img alt="EB-WX1234" src="x"></a></div>
 <div class="property-info"><p class="property-type">Casa en condominio</p></div></div>
<div class="property-listing" data-lat="20.7" data-long="-103.4"
 data-popover-data='{"price": "$85,100,000 USD", "title": "Terreno sin foto", "location": "Terreno en Zapopan, Zapopan", "size": "500 m2", "url": "/property/terreno"}'>
 <div class="property-info"><p class="property-type">Terreno</p></div></div>'''
t = S.parsear_tarjetas(html)
ok(len(t) == 2, "lee las 2 tarjetas")
ok(t[0]["foto"].startswith("https://assets.easybroker.com") and t[0]["codigo_eb"] == "EB-WX1234", "captura la foto y el codigo EB (el bug original)")
ok(t[0]["tipo"] == "casa en condominio" and t[0]["recamaras"] == 3 and t[0]["banos"] == 2.5, "tipo en minusculas, recamaras entero, banos decimal")
ok(t[1]["foto"] is None and t[1]["moneda"] == "USD", "sin foto queda None y detecta USD")

print("── SEGMENTO")
casos = [
 ("oficina", "Oficina en Providencia", "comercial"), ("nave industrial", "x", "comercial"),
 ("terreno comercial", "x", "comercial"), ("departamento", "Depa", "vivienda"),
 ("terreno", "TERRENO EN VENTA IDEAL PARA PROYECTOS DE USOS MIXTOS COMERCIAL", "comercial"),
 ("terreno", "Terreno en Zapopan", "vivienda"), ("terreno", "Terreno habitacional en coto", "vivienda"),
 ("edificio", "Se vende Hotel en Av. Vallarta", "comercial"), ("edificio", "Edificio de departamentos residencial", "vivienda"),
 ("edificio", "Edificio sin pista", "vivienda"), ("casa con uso de suelo", "Casa para oficinas corporativas", "vivienda"),
 ("otro", "algo raro", "vivienda"), ("local en centro comercial", "x", "comercial"),
]
for tipo, tit, esp in casos:
    seg, _ = S.clasificar_segmento(tipo, tit)
    ok(seg == esp, f"{tipo!r} / {tit[:40]!r} -> {seg} (esperado {esp})")

print("── GUARDAS DE PRECIO (casos REALES de hoy)")
def f(op, tipo, precio, m2, moneda=None, seg=None):
    seg = seg or S.clasificar_segmento(tipo, "")[0]
    d = {"operacion": op, "tipo": tipo, "precio": precio, "m2": m2, "segmento": seg}
    if moneda: d["moneda"] = moneda
    return d
reales = [
 (f("VENTA","casa en condominio",31_500_000_000,508), "bloquea", "casa 508m2 a 31,500 millones"),
 (f("VENTA","departamento",1_850_000_000,53), "bloquea", "depto 53m2 a 1,850 millones"),
 (f("VENTA","terreno",507_000_000,39), "bloquea", "terreno 39m2 a 507 millones"),
 (f("VENTA","terreno",388_656_000,4.8), "aviso", "terreno 4.8m2 a 388M: m2 dudoso, se juzga sin m2 (aviso)"),
 (f("VENTA","terreno",432_000_000,520_000), "ok", "terreno 520,000m2 a 432M (831 $/m2, legitimo)"),
 (f("VENTA","terreno",2_500_000_000,1_000_000), "ok", "terreno 1,000,000m2 a 2,500M (2,500 $/m2, legitimo)"),
 (f("VENTA","edificio",450_000_000,12185), "ok", "edificio 12,185m2 a 450M (legitimo)"),
 (f("RENTA","casa",5_000_000,180), "bloquea", "renta casa 180m2 a 5M/mes"),
 (f("RENTA","departamento",4_548_289,53), "bloquea", "renta depto 53m2 a 4.5M/mes"),
 (f("RENTA","nave industrial",3_644_912,23200), "ok", "renta nave 23,200m2 a 3.6M (157 $/m2, legitimo)"),
 (f("RENTA","terreno",1_462_500,32500), "ok", "renta de terreno 32,500m2 a 1.46M/mes (45 $/m2, legitimo; no es renta de vivienda)"),
 (f("RENTA","oficina",25_000,20), "ok", "oficina chica 20m2 a 25,000/mes (1,250 $/m2, plausible)"),
 (f("RENTA","local comercial",300_000,30), "bloquea", "local 30m2 a 300,000/mes (10,000 $/m2/mes: imposible)"),
 (f("RENTA","local comercial",90_000,30), "aviso", "local 30m2 a 90,000/mes (3,000 $/m2/mes: caro, se publica con aviso)"),
 (f("VENTA","edificio",85_100_000_000,12185,"USD"), "bloquea", "USD 85,100 millones"),
 (f("VENTA","edificio",85_000_000,8000,"USD"), "aviso", "USD 85 millones (aviso, no se oculta)"),
 (f("VENTA","departamento",2_500_000,70), "ok", "depto normal 2.5M"),
 (f("VENTA","departamento",5_000,70), "bloquea", "venta de $5,000"),
 (f("VENTA","terreno",90_000,200), "aviso", "terreno barato $90,000 (aviso)"),
 (f("RENTA","departamento",800,50), "bloquea", "renta de $800"),
 (f("RENTA","departamento",2_000,50), "aviso", "renta de $2,000 (aviso)"),
 (f("RENTA","departamento",15_000,70), "ok", "renta normal 15,000"),
 (f("VENTA","casa",None,100), "bloquea", "sin precio"),
]
for fila, esp, desc in reales:
    aviso_m2 = S.sanear_m2(fila)                    # igual que en el proceso real
    nivel, motivo = S.evaluar_precio(fila)
    if aviso_m2 and nivel == "ok":
        nivel, motivo = "aviso", aviso_m2
    ok(nivel == esp, f"{desc} -> {nivel}" + (f" ({motivo})" if motivo else ""))

print("── M2 DUDOSOS")
caso = {"operacion":"VENTA","tipo":"casa","precio":3_295_000,"m2":1.0,"segmento":"vivienda"}
aviso = S.sanear_m2(caso)
ok(aviso and caso["m2"] is None and S.evaluar_precio(caso)[0] == "ok", "casa de 3.3M con '1 m2': se publica SIN m2 (el precio es normal), con aviso")
caso2 = {"operacion":"VENTA","tipo":"casa","precio":3_000_000,"m2":120.0,"segmento":"vivienda"}
ok(S.sanear_m2(caso2) is None and caso2["m2"] == 120.0, "m2 normales no se tocan")

print("── MUNICIPIO / FOTO / FILA")
ok(S.normalizar_municipio("San Pedro Tlaquepaque", "tlaquepaque") == "Tlaquepaque", "San Pedro Tlaquepaque -> Tlaquepaque")
ok(S.normalizar_municipio("Tlajomulco de Zúñiga", "zapopan") is None, "Tlajomulco queda fuera de zona")
ok(S.normalizar_municipio("", "tonala") == "Tonalá", "sin municipio en tarjeta usa el de la URL")
u = "https://assets.easybroker.com/property_images/1/2/EB-X.jpg?height=300&version=9&width=450"
ok(S.foto_con_tamano(u, 1200, 800) == "https://assets.easybroker.com/property_images/1/2/EB-X.jpg?height=800&version=9&width=1200", "reescribe width/height conservando version")
prev = {("EB-WX1234","VENTA"): {"niveles": 2, "foto": "https://viejo/foto.jpg"}}
tt = dict(t[0]); tt["operacion"]="VENTA"; tt["slug_municipio"]="tlaquepaque"; tt["foto"]=None
fila, _ = S.construir_fila(tt, prev)
ok(fila["niveles"] == 2 and fila["foto"] == "https://viejo/foto.jpg", "conserva niveles y foto de la corrida anterior cuando el listado no la trae")
tt2 = dict(t[0]); tt2["operacion"]="VENTA"; tt2["slug_municipio"]="zapopan"; tt2["municipio_tarjeta"]="Tlajomulco de Zúñiga"
fila2, motivo = S.construir_fila(tt2, {})
ok(fila2 is None and motivo == "fuera de zona", "una tarjeta de Tlajomulco se descarta")

print("── CORRIDA COMPLETA SIMULADA (con frenos)")
SLUG = {"Guadalajara":"guadalajara","Zapopan":"zapopan","Tlaquepaque":"tlaquepaque","Tonalá":"tonala"}
def tarjeta(eb, op, mun, tipo, precio, m2, foto="http://f/x.jpg", titulo="Prop", moneda="MXN", mun_tarj=None):
    return {"href": f"https://www.aciertamax.com/property/{eb}", "precio": precio, "moneda": moneda, "m2": m2, "recamaras": 3,
            "banos": 2.0, "colonia": "Col", "municipio_tarjeta": mun_tarj if mun_tarj is not None else mun, "tipo": tipo, "titulo": titulo,
            "codigo_eb": eb, "foto": foto, "lat": 20.6, "lon": -103.3, "operacion": op, "slug_municipio": SLUG[mun]}
def correr(tarjetas_por_combo, previo, args=()):
    d = tempfile.mkdtemp(); os.chdir(d)
    json.dump(previo, open("data.json","w"))
    S.recorrer = lambda ses, op, sop, smun, pm: (tarjetas_por_combo.get((op, smun), []), True)
    S.foto_desde_detalle = lambda ses, href: None
    S.probar_foto_grande = lambda filas, muestra=12: (True, "simulada")
    S.time.sleep = lambda s: None
    sys.argv = ["x", *args]
    buf = io.StringIO(); code = 0
    with contextlib.redirect_stdout(buf):
        try: S.main()
        except SystemExit as e: code = e.code
    return d, code, buf.getvalue()

previo = [{"municipio":"Zapopan","operacion":"VENTA","precio":3e6,"titulo":"a","tipo":"casa","recamaras":3,"banos":2.0,"m2":100.0,"niveles":2,"eb":"EB-A1","liga":"l","foto":"f","lat":1.0,"lon":2.0,"colonia":"c"},
          {"municipio":"Tlajomulco de Zúñiga","operacion":"VENTA","precio":3e6,"titulo":"t","tipo":"casa","recamaras":3,"banos":2.0,"m2":100.0,"niveles":None,"eb":"EB-T1","liga":"l2","foto":"f","lat":1.0,"lon":2.0,"colonia":"c"}]
combos = {("VENTA","zapopan"): [
    tarjeta("EB-A1","VENTA","Zapopan","casa",3_000_000,100),
    tarjeta("EB-N1","VENTA","Zapopan","oficina",900_000,40),
    tarjeta("EB-B1","VENTA","Zapopan","casa",31_500_000_000,508),
    tarjeta("EB-F1","VENTA","Zapopan","casa",2_000_000,90,foto=None),
    tarjeta("EB-X1","VENTA","Zapopan","casa",2_000_000,90,mun_tarj="Tlajomulco de Zúñiga"),
    tarjeta("EB-A1","VENTA","Zapopan","casa",3_000_000,100),
] + [tarjeta(f"EB-OK{i}","VENTA","Zapopan","departamento",2_000_000+i,60) for i in range(40)]}
d, code, out = correr(combos, previo)
data = json.load(open(os.path.join(d, "data.json"), encoding="utf-8"))
ebs = {p["eb"] for p in data}
ok(code == 0, f"la corrida termina bien (codigo {code})")
esperado = {"EB-A1", "EB-N1"} | {f"EB-OK{i}" for i in range(40)}
ok(ebs == esperado, f"publica solo lo valido (sin la bloqueada, la sin foto, la fuera de zona ni la duplicada): {len(ebs)} fichas")
ok(next(p for p in data if p["eb"]=="EB-N1")["segmento"] == "comercial" and next(p for p in data if p["eb"]=="EB-A1")["segmento"] == "vivienda", "cada ficha lleva su segmento")
ok(next(p for p in data if p["eb"]=="EB-A1")["niveles"] == 2, "conserva 'niveles' de la corrida anterior")
ok(not any("Tlajomulco" in p["municipio"] for p in data), "Tlajomulco ya no esta en el sitio")
ok(set(data[0].keys()) >= {"municipio","operacion","precio","titulo","tipo","recamaras","banos","m2","niveles","eb","liga","foto","lat","lon","colonia","segmento"}, "mantiene todas las llaves que usa el sitio")
an = open(os.path.join(d,"reportes","inventario","anomalias_precio.csv"), encoding="utf-8").read()
ok("EB-B1" in an and "BLOQUEADA" in an, "la ficha con precio imposible queda en el reporte de anomalias")
sf = open(os.path.join(d,"reportes","inventario","sin_foto.csv"), encoding="utf-8").read()
ok("EB-F1" in sf, "la ficha sin foto queda en el reporte de sin foto")
ok(os.path.exists(os.path.join(d,"inventario.csv")) and os.path.exists(os.path.join(d,"inventario-meta.json")), "genera inventario.csv e inventario-meta.json")

print("── FRENO DE FOTOS: si faltan demasiadas, algo fallo -> NO se descartan")
muchas_sin_foto = {("VENTA","zapopan"): [tarjeta(f"EB-S{i}","VENTA","Zapopan","casa",2_000_000+i,90,foto=None) for i in range(30)] +
                                          [tarjeta(f"EB-C{i}","VENTA","Zapopan","casa",2_100_000+i,90) for i in range(10)]}
dd, cc, oo = correr(muchas_sin_foto, [])
dat = json.load(open(os.path.join(dd, "data.json"), encoding="utf-8"))
ok(cc == 0 and len(dat) == 40 and "FRENO" in open(os.path.join(dd,"reportes","inventario","resumen.md"), encoding="utf-8").read(), f"75% sin foto: se conservan las 40 fichas y el resumen lo avisa ({len(dat)})")

print("── FRENO: corrida incompleta NO sobreescribe")
previo_grande = [dict(previo[0], eb=f"EB-P{i}", liga=f"l{i}") for i in range(100)]
d2, code2, out2 = correr({("VENTA","zapopan"): [tarjeta("EB-A1","VENTA","Zapopan","casa",3_000_000,100)]}, previo_grande)
data2 = json.load(open(os.path.join(d2, "data.json"), encoding="utf-8"))
ok(code2 == 2 and len(data2) == 100 and "FRENO" in out2, f"con 1 ficha vs 100 antes: se frena (codigo {code2}) y data.json queda intacto ({len(data2)} fichas)")

print("── PRUEBA RAPIDA (--sin-escribir) no toca data.json")
d3, code3, _ = correr(combos, previo, ("--sin-escribir", "--paginas-max", "2"))
data3 = json.load(open(os.path.join(d3, "data.json"), encoding="utf-8"))
ok(code3 == 0 and len(data3) == len(previo), "modo prueba no sobreescribe data.json")

print(f"\nFALLAS: {fallas}")
sys.exit(1 if fallas else 0)

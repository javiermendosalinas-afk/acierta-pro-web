# Estado del proyecto acierta.pro — documento de continuidad
Actualizado: 4 de octubre de 2026 (noche). Léelo completo antes de tocar nada. No contiene llaves ni contraseñas.

## 1. Qué es y dónde vive
- **acierta.pro**: sitio de Acierta Max (inmobiliaria de Guadalajara). GitHub Pages desde `javiermendosalinas-afk/acierta-pro-web` (rama main, público).
- **aciertamax.com**: sitio EasyBroker de Acierta Max. Es **la fuente** del inventario y siempre permanece activo. No redirigir ni unificar con acierta.pro.
- **MAX**: bot de WhatsApp con IA (Wati + Render), repo `javiermendosalinas-afk/aciertamax-webhook` (público).
- Director: Javier Mendoza Salinas. Idioma de trabajo: español de México. Le urge vender antes de fin de año.

## 2. Inventario (lo más importante)
**Un solo sincronizador** (`herramientas/inventario_sync.py`) lee aciertamax.com y publica `data.json`, la única fuente de datos del sitio.
- **Municipios (decisión de Javier): Guadalajara, Zapopan, San Pedro Tlaquepaque, Tonalá y Tlajomulco de Zúñiga.** En un momento los quité por error de interpretación; ya están restaurados.
- Sin pisos de precio (antes: venta ≥ $2M y renta ≥ $13k).
- **Segmento** por ficha: `vivienda` o `comercial`. Tipos "por decidir" (terreno genérico, edificio, casa con uso de suelo, otro) se quedan en vivienda, salvo título claramente comercial. Mismo asesor/coach para ambos segmentos; la diferencia está en la página.
- **Guardas de precio**: lo imposible NO se publica y va a `reportes/inventario/anomalias_precio.csv` (Javier lo verifica con quien lo capturó en EasyBroker). Lo dudoso se publica con aviso (`revisar`).
- **Anuncios "por m²"**: EasyBroker a veces dice "por m²" y el número es el precio por m²; otras veces dice "por m²" y el número ya es el total (error de captura). El sincronizador prueba las dos lecturas y elige la creíble. Se conserva el dato en `pm2_pub`. Ver `resolver_precio_por_m2`.
- **Fotos**: toda ficha debe tener foto (regla de EasyBroker). Las tarjetas piden 720×480 y la ficha 1200×800 (EasyBroker entrega el tamaño pedido), con respaldo a la miniatura 450×300 y luego al ícono de casa.
- **Frenos de seguridad**: si la corrida sale incompleta no sobreescribe el inventario vigente.
- Salidas: `data.json`, `inventario.csv`, `inventario-meta.json`, `inventario-chatgpt.csv/.xlsx`, `reportes/inventario/`.
- **Calendario**: automático el **día 3 de cada mes, 5:00 am Guadalajara** (`.github/workflows/inventario.yml`). Corrida completa ≈ 16 minutos. Usa el acceso interno de GitHub (`github.token`), no un token personal.
- **Lanzar a mano**: (a) pestaña Actions → "Actualizar inventario" → Run workflow, o (b) cambiar el contenido de `herramientas/disparar_inventario.txt` y hacer push (si contiene la palabra "prueba" hace una prueba rápida que no publica nada). El workflow guarda su bitácora y resumen en `reportes/inventario/` (`resumen.md`, `ultima_corrida.log`).
- **Tope de EasyBroker**: no entrega más de 100 páginas (~1,800 fichas) por búsqueda. Si una búsqueda llega al tope, el sincronizador hace una segunda pasada de menor a mayor precio hasta encontrarse con la primera (`_pasada`, `TOPE_PAGINAS_EB`). Antes se perdían las más baratas (Zapopan casi no tenía venta debajo de $7.3M). El resumen avisa si aun así falta algo.
- Estado de la última corrida (4-oct-2026, con doble pasada): **9,970 fichas**; Zapopan venta 3,553 (1,119 debajo de $5M), Guadalajara venta 2,026; sin avisos de tope.
- Comandos: `--paginas-max 2 --sin-escribir` (prueba), `--reusar-data` (reaplica reglas sin rastrear), `--solo-exportar` (regenera solo el archivo de ChatGPT).

## 2b. Inventario compartido de NeoJaus (bolsa AMPI, oct-2026)
- **DECISIÓN (5-oct-2026): el inventario de NeoJaus NO se publica en acierta.pro.** Va a `herramientas/neojaus/neojaus.json` para un sitio aparte (por definir dominio y repo). data.json queda solo con EasyBroker; las fichas EB que también están en NeoJaus llevan `tambien_en` (clave NJ y liga) solo para el buscador de originador del portal de coaches, que lee la bolsa desde raw.githubusercontent.com.
- NeoJaus es la bolsa de AMPI, MIO, PAIS y la Cámara de Comercio: todo lo publicado ahí es para compartir comisión entre socios (confirmado por Javier). Se toma TODO lo activo de la ZMG, sin filtro de comisión.
- La clave (NJ- o EB-) es la llave para hallar al originador: el portal de coaches tiene «Buscar al originador por clave» (liga a NeoJaus o aciertamax.com). Si una propiedad está en ambas, se muestra una sola ficha y la de EasyBroker guarda `tambien_en` con la clave NJ y su liga.
- `herramientas/neojaus_sync.py`: lee el sitemap de neojaus.com (~30 mil fichas), abre solo nuevas o modificadas (caché `herramientas/neojaus/cache.json.gz`), toma las activas, de Jalisco y de los 5 municipios **según los datos de la ficha**; aplica las reglas de EasyBroker (segmento, precio, foto obligatoria); quita duplicados contra EasyBroker (misma operación, <80 m, precio ±3%); escribe neojaus.json (`"fuente": "neojaus"`, clave `NJ-xxxxx`); NO toca el inventario publicado de acierta.pro salvo para limpiar NJ y anotar gemelas.
- La liga pública de las NJ es la ficha de acierta.pro (nunca la de la otra inmobiliaria); `url_fuente` guarda la de NeoJaus. La ficha solo muestra «Abrir en aciertamax.com» para EasyBroker.
- Corre en el workflow mensual después de EasyBroker y con su propio workflow «Actualizar NeoJaus» (`herramientas/disparar_neojaus.txt`), que retoma donde se quedó si la primera carga no alcanza en una corrida. `inventario_sync.py` ignora las NJ en sus frenos.
- Sus términos y condiciones no se pudieron leer; robots.txt permite las fichas. Ritmo pausado (3 hilos, 0.6 s).
- La API de NeoJaus (USD 29/mes) solo da acceso al inventario propio: no sirve para traer la bolsa.

## Municipios (oct-2026)
- Guadalajara, Zapopan, Tlaquepaque, Tonalá y Tlajomulco de Zúñiga completos; **El Salto solo segmento comercial** (corredor industrial: bodegas, naves, terrenos industriales/comerciales, locales). Regla en `MUNICIPIOS_SOLO_COMERCIAL` (inventario_sync.py), aplicada también en neojaus_sync.py, en `AM.bolsaValida` y en los selectores de municipio de acierta.pro e inmobiliaria.pro.

## 2b-bis. Réplica blindada de la bolsa en acierta.pro (decisión de Javier, 5-oct-2026)
- inmobiliaria.pro es el ORIGEN del inventario NeoJaus; acierta.pro solo lo REPLICA en el navegador y nunca depende de él.
- `js/comun.js`: `AM.inventarioEB()` (data.json, siempre), `AM.cargarBolsa()` (lee `bolsa-config.json` → url de data.json de aciertamax-bolsa en raw.githubusercontent; espera máx. 6 s; descarta fichas sin clave NJ válida, precio, municipio ZMG, foto https o segmento, y las gemelas de EB; ignora el paquete completo si trae < 50 o si menos del 60% son válidas) y `AM.inventario()` = EB + bolsa. La portada pinta EB de inmediato y suma la bolsa al llegar; ficha, mapa y comparar usan `AM.inventario()`.
- **Interruptor**: `bolsa-config.json` → `"activa": false` quita NeoJaus de acierta.pro al instante (sin tocar código).
- data.json, CSV, archivo de ChatGPT, sitemap y meta de acierta.pro siguen SOLO con EasyBroker. Prueba: `herramientas/pruebas/t_bolsa_replica.js`.

## 2c. Sitio de la bolsa: inmobiliaria.pro (repo aciertamax-bolsa)
- Front-end copiado de acierta.pro (buscador, ficha, mapa, comparador) sin blog, Pulso, simulador, proceso, Verifica ni portal; nada enlaza a acierta.pro. CNAME `inmobiliaria.pro`.
- Su workflow «Actualizar bolsa» (diario 07:00 GDL) trae `herramientas/neojaus/neojaus.json` de acierta-pro-web y lo publica como data.json con ligas a inmobiliaria.pro (freno si viene casi vacío).
- MAX carga acierta.pro + bolsa (sin repetir las gemelas con EasyBroker) y acepta formularios de inmobiliaria.pro.
- Dominio propio inmobiliaria.pro (GoDaddy, comprado 5-oct-2026, renueva ~MXN 762/año). GitHub Pages activo en el repo. DNS en GoDaddy: 4 registros A de GitHub en @ y CNAME www → javiermendosalinas-afk.github.io. NO usar el DNS de aciertamax.com: lo administra EasyBroker (ns1-3.easybroker.com) y su correo es Google Workspace.

## 3. Sitio
- Portada (`index.html` + `app.js`): selector **Vivienda | Comercial** (también `?seg=comercial`), tipos por grupo (Casa incluye casa en condominio), rangos de precio por segmento y operación, sugerencias de colonia, fecha de actualización.
- Inversión, proceso, camino y mapa trabajan **solo con vivienda** (`AM.soloVivienda`); el mapa acepta `?seg=comercial`. Helpers en `js/comun.js` (`AM.segDe`, `AM.fotoImg`...).
- Simulador y proceso: enganche hasta 100% ("pago de contado"); el paso "Precalifica tu crédito" enlaza al simulador. Comparador hasta 10 propiedades, con mapa.
- El FAQ visible de la portada y el FAQPage JSON-LD **deben coincidir** (hay prueba que lo vigila). Textos: "más de 9,000 propiedades", 5 municipios.
- `camino.html` existe pero **no está enlazado** desde la portada (Javier pidió revertir ese enlace).
- Logo: la portada usa el logo de texto original (Javier rechazó el logo PNG por verse pixeleado). Los PNG están en `assets/logo/`.
- Blog: 29 artículos (4 semanas de contenido, octubre 2026), todos en sitemap y en el índice del blog. Recordatorio L–S 9:00 am en Google Calendar.
- Portadas de Canva: las 24 de octubre ya están publicadas (`assets/blog/<slug>.jpg` vertical y `<slug>-og.jpg` 1200×630, metas og/twitter, JSON-LD y sitemap de imágenes). Para portadas nuevas: exportar de Canva como `<slug>.jpg` y correr `python3 herramientas/blog/portadas.py <carpeta>`.

## 3b. Portal del coach y propuesta en PDF (4-oct-2026)
- `asesor.html` (no enlazada, `noindex`): el coach entra con su contraseña, busca al cliente por WhatsApp en el CRM AIDA, elige hasta 12 propiedades (resumen y ventajas se proponen con datos reales y el coach los edita) y genera la carta PDF con mapa.
- Servidor (aciertamax-webhook): `/api/asesor/usuarios|login|cliente|propuesta|pdf/<id>`; PDF en `propuesta.py` (fpdf2 + staticmap/OpenStreetMap, fuentes y logos en `recursos/`).
- Contraseñas: variables de Render `CLAVE_ASESOR_JAVIER`, `_UBALDO`, `_LETICIA`, `_GLORIA`, `_PAOLA` (sin variable, ese coach no entra). Nunca en archivos.
- Envío: PDF directo por WhatsApp si el chat del cliente está abierto; si no, plantilla `seguimiento_cliente` con liga (Drive público en la carpeta del cliente o liga de respaldo del servidor). Copia al coach y a Javier; queda en la hoja de Actividad y en ULTIMA_ACCION del CRM.
- Pie de la carta: NOM-247-SE-2021 y "contratos de adhesión registrados ante PROFECO" como texto (sin logo de PROFECO ni NOM); logos AMPI, NAR y CONOCER (Javier: EC0110.02, folio D-0027837023, "Dirección General certificada").

## 3c. Pulso Inmobiliario acierta.pro (suscripción, oct-2026)
- `pulso.html` (indexable, en sitemap): adelanto con cifras y gráficas, formulario (nombre, WhatsApp, correo opcional, intereses, consentimiento) y luego botón a WhatsApp con "PULSO ####". Invitación en el menú y una sección de la portada y al final de cada artículo del blog.
- MAX: `/api/pulso/suscribir` guarda pendiente; al recibir "PULSO" (con o sin código) activa, manda bienvenida + PDF de la edición vigente (sesión abierta, sin plantilla) y marca el contacto en Wati con `pulso=si` y `pulso_intereses`. "BAJA PULSO" cancela (`pulso=no`). Hoja de Sheets "Suscriptores Pulso". Los mensajes automáticos del Pulso y de la verificación no se copian a Javier (`wati_send_text(..., copiar=False)`).
- Ediciones: `pulso/ediciones.json` (la que tenga `"vigente": true`); PDFs en `assets/pulso/`. Publicar una edición nueva = subir PDF + editar el JSON; MAX la toma sola (caché de 1 h).
- Envío (decisión de Javier, 5-oct-2026, por costo): **cada edición por correo** (Gmail de MAX: `GMAIL_USER`/`GMAIL_PASS` en Render; máx. 400/día; bienvenida con PDF al confirmar y edición nueva cuando en ediciones.json tenga `"enviar_correo": true`; enlace de baja `/api/pulso/baja`). Por WhatsApp solo cuando el suscriptor escribe PULSO (mensaje de servicio, sin plantilla): si ya está activo recibe directo la edición vigente.
- Costo: hoja "Pulso Métricas" (por mes: mensajes WhatsApp, correos, altas, bajas, costo estimado a USD 0.0085 por mensaje, sin descontar los 1,000 gratis). MAX avisa a Javier una vez al mes al llegar a USD 40 (`PULSO_ALERTA_USD`): ahí se evalúa la rentabilidad. Plantilla de marketing `pulso_semanal` descartada por ahora (USD 0.0397 por mensaje desde oct-2026).
- Aviso de privacidad COMPLETO (4-oct-2026): domicilio fiscal de la constancia SAT (Av. Temuco 293, Lote 39, Mz 165, Col. Hacienda Santa Fe, Tlajomulco, C.P. 45653), correo ARCO javier.mendoza@acierta.com.mx, finalidad secundaria del Pulso y baja; `avisoVersion` 2026-10-04. Recomendable que lo revise el abogado.

### Material para el Pulso 02 (ya verificado contra el Anuario Hipotecario 2026, Metric Analysis)
- Tasas: Banxico en pausa en 6.50%, sin recortes previstos en 2026; tasa de colocación bancaria 9.99% (jun-2026, vs 10.31% un año antes), plazo promedio 19.2 años; crédito para pago de pasivos +51.8% en monto (portabilidad: gancho para crédito/Betty).
- Infonavit/Fovissste: 50.7% de sus créditos del 1S 2026 fue a vivienda vendida por persona física (gancho para captar vendedores).
- Oferta: 489.5 mil viviendas registradas en RUV (+183%), inicios de obra +217%; llegan al mercado en 2027.
- Tickets: nueva +79.9% y usada +76.8% (2019 a 1S 2026); en 1S 2026 la usada cuesta $138 mil más.
- Escenarios 2S 2026 a 2028: inercia ~50%, reactivación ~30%, contracción ~20%.
- Regiones (plusvalía 2020 a 1S 2026): Noroeste 96.93%, Noreste 83.12%, Occidente 80.77%, Sureste 74.91%, Centro 58.96%. Jalisco no aparece en las tablas por estado.
- Recordar: cifras del 1S 2026 preliminares por el incidente de ciberseguridad de la SHF (ene-2026, ~44 mil operaciones sin computar).
- Pendiente de decisión: "Termómetro acierta.pro" mensual con precios de OFERTA del inventario propio por municipio (aclarar sesgo a segmento medio-alto y limpiar m² terreno/construcción antes de publicar).

## 4. Archivo para ChatGPT (publicidad en Instagram)
- `inventario-chatgpt.xlsx` / `.csv`: 34 columnas (clave EB, filtros, textos para imagen, foto grande, liga de WhatsApp con la clave, hashtags, `apto_para_publicar`, `nota_calidad`). Se regenera solo cada mes.
- Instrucciones para pegar en el GPT: `herramientas/chatgpt/instrucciones-chatgpt.txt` (4,806 caracteres; límite de ChatGPT 8,000). Diccionario y ejemplos reales: `herramientas/chatgpt/diccionario-y-ejemplos.md`.
- Reglas: solo `apto_para_publicar = si`; la clave EB (`EB-XXXXXX`) siempre en el texto para que Wati/MAX la identifique; mencionar Acierta Verifica (desde $45/m², mínimo $3,500 MXN) y los demás servicios; no inventar datos; vivienda y comercial no se mezclan.
- No se ha probado dentro de ChatGPT (Claude no tiene acceso). Pendiente que Javier haga 3–5 publicaciones de prueba y dé retroalimentación.
- Aún no marca "nueva" ni "bajó de precio": agregarlo después de la corrida del 3 de noviembre (ya habrá un mes para comparar).

## 5. Pruebas
```
python3 herramientas/pruebas/test_inventario_sync.py
cd herramientas/pruebas && npm i jsdom@22        # jsdom 22: las versiones nuevas cambiaron la API
node t_home_segmentos.js; node t_paginas.js; node t_regresion_rapida.js
```
Siempre correrlas antes de publicar. Las pruebas viven en el repo (en otra ocasión se perdieron porque estaban solo en /tmp).

## 6. Trampas conocidas
- El entorno de Claude se reinicia: hay que volver a clonar los repos y configurar `git config user.name/email`.
- Su red solo permite ciertos dominios. **aciertamax.com, assets.easybroker.com, acierta.pro y canva.com están bloqueados** desde el entorno de Claude; por eso el rastreo corre en GitHub Actions. Javier agregó `export-download.canva.com`, `canva.com` y `media.canva.com` a la lista permitida (claude.ai/settings/capabilities): solo aplica en conversaciones nuevas.
- Token de GitHub de Javier (fine-grained, repo acierta-pro-web): vence el **11-oct-2026**. Permisos: Contents y Workflows en lectura/escritura; **Actions NO** (por eso no se puede lanzar el workflow por API: usar el archivo de disparo). Javier debe borrarlo cuando termine el proyecto. Nunca guardar tokens en archivos ni memoria.
- Para leer los repos no hace falta token (son públicos); para publicar, sí.
- Las herramientas de Canva no pueden insertar el logo real; Canva sí está conectado.

## 7. Pendientes
| # | Qué | Quién |
|---|---|---|
| 1 | ~~Render~~ HECHO 4-oct: despliega solo desde GitHub. Plantillas `seguimiento_cliente` y `copia_interna` aprobadas | — |
| 2 | Crear en Wati la plantilla `codigo_verificacion` (categoría Autenticación, una variable {{1}}) y esperar aprobación de Meta: sin ella el código de verificación del formulario no se envía. Luego probar en acierta.pro/camino.html | Javier |
| 3 | Verificar con quien las capturó las 96 fichas de `3_FICHAS_PARA_VERIFICAR…xlsx` (40 no se publican) | Javier |
| 4 | Google Business Profile: verificar y empezar a pedir reseñas; backlinks reales | Javier |
| 5 | Probar el GPT con 3–5 publicaciones y dar retroalimentación | Javier |
| 6 | Subir las 24 portadas de Canva a sus artículos del blog (mapeo en la memoria, archivo `acierta-max-blog-seo`); necesita chat nuevo por la lista de dominios | Claude |
| 7 | HECHO 4-oct: MAX descarga `data.json` del sitio al arrancar y revisa cada 6 h (`_actualizar_inventario_desde_sitio` en app.py; respaldo: CSV local). Sin pisos de precio; filtro de tipo corregido (local/oficina/bodega/nave) | — |
| 8 | Área comercial de la página (landing propia, filtros y textos distintos) — "más tarde" | Claude |
| 9 | SEO: el inventario se carga con JavaScript; páginas por colonia y fichas que Google pueda leer; enviar sitemap a Search Console y Bing | Claude + Javier |
| 10 | Marcas "nueva / bajó de precio" en el archivo de ChatGPT (después del 3-nov) | Claude |
| 11 | Revisar la bitácora de la corrida del 3 de noviembre (primera automática) | Claude |
| 12 | Seguir la rutina de blog (2 mercado, 2 interiorismo, 2 construcción por semana) | Claude |

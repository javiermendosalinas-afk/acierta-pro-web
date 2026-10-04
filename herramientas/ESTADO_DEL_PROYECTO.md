# Estado del proyecto acierta.pro — documento de continuidad
Actualizado: 4 de octubre de 2026. Léelo completo antes de tocar nada. No contiene llaves ni contraseñas.

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
- Estado de la última corrida (4-oct-2026): 7,983 fichas (6,043 vivienda / 1,940 comercial), 0 sin foto, 40 con precio bloqueado, 56 con aviso.
- Comandos: `--paginas-max 2 --sin-escribir` (prueba), `--reusar-data` (reaplica reglas sin rastrear), `--solo-exportar` (regenera solo el archivo de ChatGPT).

## 3. Sitio
- Portada (`index.html` + `app.js`): selector **Vivienda | Comercial** (también `?seg=comercial`), tipos por grupo (Casa incluye casa en condominio), rangos de precio por segmento y operación, sugerencias de colonia, fecha de actualización.
- Inversión, proceso, camino y mapa trabajan **solo con vivienda** (`AM.soloVivienda`); el mapa acepta `?seg=comercial`. Helpers en `js/comun.js` (`AM.segDe`, `AM.fotoImg`...).
- Simulador y proceso: enganche hasta 100% ("pago de contado"); el paso "Precalifica tu crédito" enlaza al simulador. Comparador hasta 10 propiedades, con mapa.
- El FAQ visible de la portada y el FAQPage JSON-LD **deben coincidir** (hay prueba que lo vigila). Textos: "más de 7,000 propiedades", 5 municipios.
- `camino.html` existe pero **no está enlazado** desde la portada (Javier pidió revertir ese enlace).
- Logo: la portada usa el logo de texto original (Javier rechazó el logo PNG por verse pixeleado). Los PNG están en `assets/logo/`.
- Blog: 29 artículos (4 semanas de contenido, octubre 2026), todos en sitemap y en el índice del blog. Recordatorio L–S 9:00 am en Google Calendar.

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
| 1 | Confirmar que Render desplegó la última versión de `aciertamax-webhook` (si el despliegue es manual, hacerlo): código de verificación de WhatsApp, seguimiento a clientes y copia a Javier no funcionan en producción hasta entonces | Javier |
| 2 | Confirmar que Meta aprobó las 3 plantillas de Wati: `seguimiento_cliente`, `copia_interna`, `codigo_verificacion` (sin ellas esos mensajes fallan) | Javier |
| 3 | Verificar con quien las capturó las 96 fichas de `3_FICHAS_PARA_VERIFICAR…xlsx` (40 no se publican) | Javier |
| 4 | Google Business Profile: verificar y empezar a pedir reseñas; backlinks reales | Javier |
| 5 | Probar el GPT con 3–5 publicaciones y dar retroalimentación | Javier |
| 6 | Subir las 24 portadas de Canva a sus artículos del blog (mapeo en la memoria, archivo `acierta-max-blog-seo`); necesita chat nuevo por la lista de dominios | Claude |
| 7 | MAX todavía usa su propio inventario (con pisos viejos de $2M/$13k); unificarlo con el nuevo `inventario-chatgpt`/`data.json` | Claude (a decidir con Javier) |
| 8 | Área comercial de la página (landing propia, filtros y textos distintos) — "más tarde" | Claude |
| 9 | SEO: el inventario se carga con JavaScript; páginas por colonia y fichas que Google pueda leer; enviar sitemap a Search Console y Bing | Claude + Javier |
| 10 | Marcas "nueva / bajó de precio" en el archivo de ChatGPT (después del 3-nov) | Claude |
| 11 | Revisar la bitácora de la corrida del 3 de noviembre (primera automática) | Claude |
| 12 | Seguir la rutina de blog (2 mercado, 2 interiorismo, 2 construcción por semana) | Claude |

# Diccionario de columnas y ejemplos — Inventario Acierta Max para ChatGPT

Inventario actualizado: **2026-10-04** · Se actualiza el **día 3 de cada mes** · Fuente: aciertamax.com (EasyBroker)
Municipios: Guadalajara, Zapopan, San Pedro Tlaquepaque, Tonalá y Tlajomulco de Zúñiga.

## Cómo usarlo en ChatGPT (3 pasos)
1. Crea un GPT o un Proyecto nuevo y pega en **Instrucciones** el contenido de `1_INSTRUCCIONES_PARA_PEGAR_EN_CHATGPT.txt`.
2. En **Conocimiento / Archivos** sube `inventario-chatgpt.xlsx` (o el `.csv`) y este archivo. Activa **Análisis de datos / Intérprete de código**: el inventario tiene casi 8,000 filas y así ChatGPT puede filtrarlo completo en vez de leer solo fragmentos.
3. Pídele por ejemplo: *"Hazme 5 publicaciones de casas en venta en Zapopan de entre $3 y $5 millones"* o *"3 publicaciones de oficinas en renta en Guadalajara"*.

Cada mes, después del día 3, sube la versión nueva del archivo (reemplaza la anterior).

## Reglas rápidas
- Publicar solo `apto_para_publicar = si`. Las filas `revisar` tienen una duda en el precio: no se publican sin autorización.
- La clave **EB-XXXXXX** va siempre escrita exacta en el texto (así la identifica Wati). Una misma clave puede existir en venta y en renta: escribe la clave junto con la operación.
- Si una columna está vacía (m², recámaras, baños, niveles), ese dato **no se menciona**.
- Vivienda y comercial no se mezclan.

## Columnas
| Columna | Qué contiene / cómo usarla |
|---|---|
| `codigo_eb` | Clave de la propiedad (EB-XXXXXX). Es la que Wati/MAX usa para identificar la propiedad: debe ir SIEMPRE en el texto. |
| `operacion` | VENTA o RENTA. Una misma clave EB puede aparecer en venta y en renta: la clave siempre va junto con la operación. |
| `segmento` | vivienda o comercial. Son clientes distintos: no se mezclan en una publicación. |
| `tipo` | Tipo tal como lo captura EasyBroker (casa, departamento, terreno, local comercial, bodega industrial...). |
| `grupo_tipo` | Tipo agrupado para filtrar: casa, departamento, terreno, local, oficina, bodega, edificio. |
| `municipio` | Guadalajara, Zapopan, Tlaquepaque, Tonalá o Tlajomulco de Zúñiga. |
| `colonia` | Colonia o zona, tal como viene del anuncio. |
| `titulo_anuncio` | Título original del anuncio en EasyBroker (sirve de referencia; no es obligatorio usarlo). |
| `precio` | Precio numérico (total). En renta es por mes. |
| `moneda` | MXN o USD. |
| `precio_texto` | Precio ya redactado para usar en el texto (ej. $3,200,000 MXN o $18,500 MXN al mes). |
| `precio_por_m2` | Precio total entre m² (en renta, por mes). Vacío si no hay superficie confiable. |
| `precio_publicado_por_m2` | Si el anuncio original estaba por m², aquí va ese precio; el total ya está calculado en 'precio'. |
| `rango_precio` | Rango de precio para filtrar (ej. $3 a $5 millones). |
| `m2` | Superficie en m². Vacía = no se conoce o no es confiable: NO mencionarla. |
| `recamaras` | Número de recámaras (vivienda). Vacío = no se conoce. |
| `banos` | Número de baños. Vacío = no se conoce. |
| `niveles` | Número de niveles o plantas. Vacío = no se conoce. |
| `lat` | Latitud. |
| `lon` | Longitud. |
| `foto_principal` | Foto principal en tamaño grande (1200x800 aprox.). Usar para la imagen. |
| `foto_miniatura` | La misma foto en miniatura (respaldo si la grande no abre). |
| `liga_aciertamax` | Anuncio original en aciertamax.com (la fuente). |
| `liga_ficha_acierta_pro` | Ficha de la propiedad en acierta.pro (con comparador, mapa y simulador). |
| `liga_whatsapp` | Liga de WhatsApp que ya trae el mensaje con la clave EB: al tocarla, Wati recibe la clave. Usar como llamada a la acción. |
| `imagen_titular` | Titular corto para la imagen (ej. Casa en venta). |
| `imagen_ubicacion` | Ubicación para la imagen (colonia, municipio). |
| `imagen_datos` | Línea de datos para la imagen (recámaras, baños, m²). Puede estar vacía. |
| `imagen_precio` | Precio para la imagen. |
| `datos_clave` | Datos verificables de la propiedad para la descripción. No agregar nada que no esté aquí. |
| `hashtags_sugeridos` | Hashtags sugeridos. |
| `apto_para_publicar` | si = se puede publicar. revisar = hay una duda en el precio: NO publicar sin autorización de Javier. |
| `nota_calidad` | Aviso sobre el dato (ej. precio calculado, m² no confiable). Respetarlo. |
| `fecha_inventario` | Fecha de la actualización del inventario. |

## Ejemplos completos (con propiedades reales del inventario)
### Ejemplo 1: vivienda en venta (EB-VP9839)

**A. CLAVE:** EB-VP9839 · VENTA · vivienda · Guadalajara

**B. GANCHO:** 5 recámaras y 273 m² en la colonia Independencia

**C. DESCRIPCIÓN:**
¿Buscas espacio para toda la familia en Guadalajara? Esta casa en venta en la colonia Independencia tiene 5 recámaras, 3 baños y 273 m² en 2 niveles. Su precio es de $5,690,000 MXN, unos $20,842 por m². Agenda tu visita y conócela.

**D. DATOS CLAVE:**
- Ubicación: Independencia, Guadalajara
- Tipo: casa
- 5 recámaras · 3 baños · 273 m² · 2 niveles
- $5,690,000 MXN (≈ $20,842 por m²)

**E. SERVICIOS DE ACIERTA MAX:**
Antes de firmar puedes pedir **Acierta Verifica**: una revisión física básica y un análisis documental preventivo (agua, luz, humedades, gas, drenaje y que los documentos estén en orden), desde $45 por m² revisado, mínimo $3,500 MXN. Y en acierta.pro simulas tu crédito (bancario, Infonavit o Cofinavit), comparas propiedades, ves la zona en el mapa y MAX te atiende por WhatsApp.

**F. LLAMADA A LA ACCIÓN:**
Escríbenos por WhatsApp con la clave **EB-VP9839**
https://wa.me/523333777337?text=Hola%2C%20me%20interesa%20esta%20propiedad%3A%20Casa%20en%20Venta%20Colonia%20Independencia%20%28EB-VP9839%2C%20venta%29%20%E2%80%94%20https%3A//acierta.pro/ficha.html%3Feb%3DEB-VP9839%26op%3DVENTA
Ficha completa: https://acierta.pro/ficha.html?eb=EB-VP9839&op=VENTA
_Precio y disponibilidad sujetos a confirmación._

**G. HASHTAGS:** #AciertaMax #Guadalajara #CasaEnVenta #BienesRaicesGDL #Independencia

**H. BRIEF DE IMAGEN:** Vertical 1080x1350, foto de la casa como fondo con una franja azul marino (#0f1f3d) abajo para el texto en blanco; el precio destacado en rojo (#d62828); logotipo AciertaMax al pie. No modificar la casa.
- Foto base: https://assets.easybroker.com/property_images/5889839/103604567/EB-VP9839.jpg?height=800&s=0dc7a902ccb4956a&version=1774455913&width=1200
- Texto: «Casa en venta» · «Independencia, Guadalajara» · «5 recámaras · 3 baños · 273 m² · 2 niveles» · «$5,690,000 MXN» · clave pequeña «EB-VP9839»

---
### Ejemplo 2: comercial en renta (EB-WN9310)

**A. CLAVE:** EB-WN9310 · RENTA · comercial · Guadalajara

**B. GANCHO:** 1200 m² de oficina en Country Club, Guadalajara

**C. DESCRIPCIÓN:**
Si tu empresa necesita espacio en Guadalajara, esta oficina en renta en Country Club ofrece 1,200 m². La renta es de $432,194 MXN al mes, alrededor de $360 por m². Solicita informes y agenda una visita.

**D. DATOS CLAVE:**
- Ubicación: Country Club, Guadalajara
- Tipo: oficina
- 1,201 m²
- $432,194 MXN al mes (≈ $360 por m² al mes)

**E. SERVICIOS DE ACIERTA MAX:**
Antes de firmar puedes pedir **Acierta Verifica**: revisión física básica y análisis documental preventivo del inmueble, desde $45 por m² revisado, mínimo $3,500 MXN. En acierta.pro también ves la zona en el mapa y comparas propiedades, y te acompañamos con la documentación.

**F. LLAMADA A LA ACCIÓN:**
Escríbenos por WhatsApp con la clave **EB-WN9310**
https://wa.me/523333777337?text=Hola%2C%20me%20interesa%20esta%20propiedad%3A%20Oficina%20en%20renta%20en%20country%20club%20%28EB-WN9310%2C%20renta%29%20%E2%80%94%20https%3A//acierta.pro/ficha.html%3Feb%3DEB-WN9310%26op%3DRENTA
Ficha completa: https://acierta.pro/ficha.html?eb=EB-WN9310&op=RENTA
_Precio y disponibilidad sujetos a confirmación._

**G. HASHTAGS:** #AciertaMax #Guadalajara #OficinaEnRenta #InmueblesComerciales #CountryClub

**H. BRIEF DE IMAGEN:** Vertical 1080x1350, foto del inmueble de fondo, tipografía sobria; tono de negocios (sin imágenes de familia). Marca: rojo, azul marino y crema; logotipo AciertaMax al pie.
- Foto base: https://assets.easybroker.com/property_images/6129310/108661204/EB-WN9310.jpeg?height=800&s=b7c64220d54bfbca&version=1784919546&width=1200
- Texto: «Oficina en renta» · «Country Club, Guadalajara» · «1,201 m²» · «$432,194 MXN al mes» · clave pequeña «EB-WN9310»


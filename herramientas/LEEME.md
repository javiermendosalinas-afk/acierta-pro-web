# Herramientas de acierta.pro

## Inventario (`inventario_sync.py`)
Trae el inventario de **aciertamax.com** (EasyBroker) y publica `data.json`, la única fuente de datos del sitio.

- Municipios: Guadalajara, Zapopan, San Pedro Tlaquepaque, Tonalá y Tlajomulco de Zúñiga. Venta y renta. Sin pisos de precio.
- Cada ficha lleva `segmento`: `vivienda` o `comercial` (los tipos "por decidir" se quedan en vivienda).
- **Guardas de precio**: lo imposible (p. ej. casa de 508 m² a $31,500 millones) NO se publica y queda en
  `reportes/inventario/anomalias_precio.csv` para verificarlo con quien lo capturó en EasyBroker. Lo dudoso se
  publica con aviso. Un m² imposible (p. ej. "1 m²") se publica sin m².
- **Fotos**: toda ficha debe tener foto; si el listado no la trae se busca en la corrida anterior y luego en la
  página de detalle. Las que sigan sin foto no se publican y quedan en `reportes/inventario/sin_foto.csv`.
- **Frenos**: si la corrida sale incompleta, NO sobreescribe el inventario vigente.
- Salidas: `data.json`, `inventario.csv` (para ChatGPT/Instagram), `inventario-meta.json`, `reportes/inventario/`.

```
python3 herramientas/inventario_sync.py                               # corrida completa (20-40 min)
python3 herramientas/inventario_sync.py --paginas-max 2 --sin-escribir # prueba rápida, no publica nada
python3 herramientas/inventario_sync.py --reusar-data                  # sin rastreo: reaplica reglas a data.json
```
Requiere: `pip install requests beautifulsoup4 pillow`.

### Automatización semanal
`.github/workflows/inventario.yml` es la automatización de GitHub Actions (cada lunes + botón manual).
Para subirla por API el token necesita permiso **Workflows**; para lanzarla, **Actions**.

## Pruebas (`pruebas/`)
```
python3 herramientas/pruebas/test_inventario_sync.py                 # lógica del sincronizador
cd herramientas/pruebas && npm i jsdom@22 && node t_home_segmentos.js # portada: Vivienda | Comercial
node t_paginas.js        # todas las páginas abren sin errores; herramientas de vivienda solo ven vivienda
node t_regresion_rapida.js   # comparador de 10, simulador de contado, enlace del proceso, SEO, blog, FAQ
```

# Diagnóstico de neojaus.com

## robots.txt
```
Sitemap: https://neojaus.com/sitemap.xml

User-agent: *
Disallow: /cdn-cgi/*

User-agent: bingbot
Crawl-delay: 10

```

## Sitemaps
- https://neojaus.com/sitemap.xml: HTTP 200, 4 <loc>; ejemplos: ['https://cdn.neojaus.com/sitemaps/all-properties-sitemap.xml', 'https://cdn.neojaus.com/sitemaps/important-pages.xml', 'https://cdn.neojaus.com/sitemaps/static-pages.xml', 'https://blog.neojaus.com/sitemap.xml']
  - https://cdn.neojaus.com/sitemaps/all-properties-sitemap.xml: 2 <loc>, con /propiedades/: 0; ejemplos: ['https://cdn.neojaus.com/sitemaps/all-properties/sitemap-1.xml', 'https://cdn.neojaus.com/sitemaps/all-properties/sitemap-2.xml']
  - https://cdn.neojaus.com/sitemaps/important-pages.xml: 2 <loc>, con /propiedades/: 0; ejemplos: ['https://cdn.neojaus.com/sitemaps/important-pages/sitemap-1.xml', 'https://cdn.neojaus.com/sitemaps/important-pages/sitemap-2.xml']
  - https://cdn.neojaus.com/sitemaps/static-pages.xml: 10 <loc>, con /propiedades/: 0; ejemplos: ['https://neojaus.com/', 'https://neojaus.com/propietarios-particulares', 'https://neojaus.com/asesores-inmobiliarios']
  - https://blog.neojaus.com/sitemap.xml: 159 <loc>, con /propiedades/: 0; ejemplos: ['https://blog.neojaus.com/2026/10/05/%f0%9f%93%96-como-aparecer-en-el-local-pack-de-google-maps-el-iman-de-clics-para-tu-inmobiliaria/', 'https://blog.neojaus.com/2026/09/30/%f0%9f%93%96-como-valorar-mi-propiedad-rapido-el-iman-de-leads-mas-buscado/', 'https://blog.neojaus.com/2026/09/28/%f0%9f%93%96-cumplimiento-de-la-nom-247-y-transparencia-en-la-publicidad-inmobiliaria-digital/']
- Total de fichas encontradas en sitemaps (muestra): 0

## Búsqueda
- https://neojaus.com/propiedades: HTTP 200, 50 ligas a fichas, json embebido: True, apis vistas: []
- https://neojaus.com/propiedades/venta/jalisco/zapopan: HTTP 404, 0 ligas a fichas, json embebido: True, apis vistas: []
- https://neojaus.com/inmuebles/venta/jalisco/zapopan: HTTP 404, 0 ligas a fichas, json embebido: True, apis vistas: []
- https://neojaus.com/buscar?q=zapopan: HTTP 404, 0 ligas a fichas, json embebido: True, apis vistas: []
- https://neojaus.com/propiedades?estado=jalisco&municipio=zapopan: HTTP 200, 50 ligas a fichas, json embebido: True, apis vistas: []

## Fichas de muestra (texto sin datos personales)

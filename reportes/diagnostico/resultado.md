# Diagnóstico de claves EB faltantes

Claves: EB-XB4792, EB-XA9606, EB-WV3319, EB-XD2631, EB-VY4454, EB-WP7537, EB-WV5084

## 1. Búsqueda directa por clave

- https://www.aciertamax.com/search?q=EB-XB4792 → error
- https://www.aciertamax.com/search_text?search_text=EB-XB4792 → HTTP 200, final https://www.aciertamax.com/search_text?search_text=EB-XB4792, clave en página: False, tarjetas: 0
- https://www.aciertamax.com/properties?search%5Bquery%5D=EB-XB4792 → HTTP 200, final https://www.aciertamax.com/properties?search%5Bquery%5D=EB-XB4792, clave en página: True, tarjetas: 18
- https://www.aciertamax.com/property/eb-xb4792 → HTTP 404, final https://www.aciertamax.com/property/eb-xb4792, clave en página: False, tarjetas: 0
- https://www.aciertamax.com/renta?search%5Bquery%5D=EB-XB4792 → HTTP 404, final https://www.aciertamax.com/renta?search%5Bquery%5D=EB-XB4792, clave en página: False, tarjetas: 0
- https://www.aciertamax.com/search?q=EB-XA9606 → error
- https://www.aciertamax.com/search_text?search_text=EB-XA9606 → HTTP 429, final https://www.aciertamax.com/search_text?search_text=EB-XA9606, clave en página: False, tarjetas: 0
- https://www.aciertamax.com/properties?search%5Bquery%5D=EB-XA9606 → HTTP 200, final https://www.aciertamax.com/properties?search%5Bquery%5D=EB-XA9606, clave en página: True, tarjetas: 18
- https://www.aciertamax.com/property/eb-xa9606 → HTTP 404, final https://www.aciertamax.com/property/eb-xa9606, clave en página: False, tarjetas: 0
- https://www.aciertamax.com/renta?search%5Bquery%5D=EB-XA9606 → HTTP 404, final https://www.aciertamax.com/renta?search%5Bquery%5D=EB-XA9606, clave en página: False, tarjetas: 0
- https://www.aciertamax.com/search?q=EB-WV3319 → error
- https://www.aciertamax.com/search_text?search_text=EB-WV3319 → HTTP 429, final https://www.aciertamax.com/search_text?search_text=EB-WV3319, clave en página: False, tarjetas: 0
- https://www.aciertamax.com/properties?search%5Bquery%5D=EB-WV3319 → error
- https://www.aciertamax.com/property/eb-wv3319 → error
- https://www.aciertamax.com/renta?search%5Bquery%5D=EB-WV3319 → error
- https://www.aciertamax.com/search?q=EB-XD2631 → error
- https://www.aciertamax.com/search_text?search_text=EB-XD2631 → error
- https://www.aciertamax.com/properties?search%5Bquery%5D=EB-XD2631 → error
- https://www.aciertamax.com/property/eb-xd2631 → error
- https://www.aciertamax.com/renta?search%5Bquery%5D=EB-XD2631 → error
- https://www.aciertamax.com/search?q=EB-VY4454 → error
- https://www.aciertamax.com/search_text?search_text=EB-VY4454 → error
- https://www.aciertamax.com/properties?search%5Bquery%5D=EB-VY4454 → error
- https://www.aciertamax.com/property/eb-vy4454 → error
- https://www.aciertamax.com/renta?search%5Bquery%5D=EB-VY4454 → error
- https://www.aciertamax.com/search?q=EB-WP7537 → error
- https://www.aciertamax.com/search_text?search_text=EB-WP7537 → error
- https://www.aciertamax.com/properties?search%5Bquery%5D=EB-WP7537 → error
- https://www.aciertamax.com/property/eb-wp7537 → error
- https://www.aciertamax.com/renta?search%5Bquery%5D=EB-WP7537 → error
- https://www.aciertamax.com/search?q=EB-WV5084 → error
- https://www.aciertamax.com/search_text?search_text=EB-WV5084 → error
- https://www.aciertamax.com/properties?search%5Bquery%5D=EB-WV5084 → error
- https://www.aciertamax.com/property/eb-wv5084 → error
- https://www.aciertamax.com/renta?search%5Bquery%5D=EB-WV5084 → error

## 2. Listados de renta

- renta/zapopan orden=price-desc: 0 claves en 0 páginas; el sitio dice: ; de las buscadas aparecen: ninguna
- renta/zapopan orden=price-asc: 0 claves en 0 páginas; el sitio dice: ; de las buscadas aparecen: ninguna
- renta/zapopan orden=por defecto: 0 claves en 0 páginas; el sitio dice: ; de las buscadas aparecen: ninguna
- renta/guadalajara orden=price-desc: 0 claves en 0 páginas; el sitio dice: ; de las buscadas aparecen: ninguna
- renta/guadalajara orden=price-asc: 0 claves en 0 páginas; el sitio dice: ; de las buscadas aparecen: ninguna
- renta/guadalajara orden=por defecto: 0 claves en 0 páginas; el sitio dice: ; de las buscadas aparecen: ninguna

## 3. Formularios y enlaces del sitio

- form action=/search_text method=get campos=['search[text]', 'commit']
- form action=/search_text method=get campos=['search[text]', 'commit']
- form action=/search_text method=get campos=['search[text]', 'commit']
- rutas: ['/', '/about', '/contact', '/index', '/properties', '/rentals']

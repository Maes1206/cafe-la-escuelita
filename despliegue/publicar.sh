#!/usr/bin/env bash
# Compila la página y sube "plantilla la escuelita/public" a cafelaescuelita.site.
# Uso (Git Bash, desde esta carpeta):  bash publicar.sh
# No toca nginx: para cambios de configuración usa activar-sitio.sh.
set -euo pipefail
cd "$(dirname "$0")"

SITIO="../plantilla la escuelita"
DESTINO=/var/www/sistema-facturacion/cafelaescuelita.site

echo "1) Compilando CSS y versionando archivos..."
python "$SITIO/construir.py"

echo "2) Revisando que no quede nada del CDN de desarrollo..."
if grep -q "cdn.tailwindcss.com" "$SITIO/public/index.html"; then
  echo "   ERROR: index.html todavía usa cdn.tailwindcss.com"; exit 1
fi
# Textos de ejemplo pendientes (notas de cata, envíos, pagos, datos del responsable): no se publican
pendientes=$(grep -l "data-por-confirmar" "$SITIO"/public/*.html || true)
if [ -n "$pendientes" ]; then
  echo "   ERROR: hay datos por confirmar con el cliente (marcados con borde rojo punteado) en:"
  echo "$pendientes" | sed 's|.*/|     - |'
  echo "   Reemplázalos por los datos reales y quita el atributo data-por-confirmar."
  exit 1
fi

echo "3) Subiendo archivos a $DESTINO ..."
tar -C "$SITIO/public" -czf - . | ssh hostinger-vps "mkdir -p $DESTINO && tar -xzf - -C $DESTINO --no-same-owner && chmod -R a+rX $DESTINO"

echo "4) Verificando..."
url=https://cafelaescuelita.site
code=$(curl -s -o /dev/null -w "%{http_code}" "$url/")
css=$(grep -o 'assets/css/estilos.css?v=[0-9a-f]*' "$SITIO/public/index.html" | head -1)
code_css=$(curl -s -o /dev/null -w "%{http_code}" "$url/$css")
gz=$(curl -s -H "Accept-Encoding: gzip" -o /dev/null -D - "$url/" | grep -i '^content-encoding' || true)
echo "   Página: $code | CSS: $code_css | Compresión: ${gz:-sin gzip (aplica activar-sitio.sh)}"
[ "$code" = 200 ] && [ "$code_css" = 200 ] && echo "   OK: $url publicado."

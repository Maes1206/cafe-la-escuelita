#!/usr/bin/env bash
# Activa cafelaescuelita.site en el VPS (contenedor invoiceplane-nginx).
# Uso (Git Bash, desde esta carpeta):  bash activar-sitio.sh
set -euo pipefail
cd "$(dirname "$0")"

DIR=/var/www/sistema-facturacion/resources/docker/nginx-prod

echo "1) Subiendo cafelaescuelita.conf al servidor..."
scp -q cafelaescuelita.conf hostinger-vps:/tmp/cafelaescuelita.conf

ssh hostinger-vps "DIR=$DIR bash -s" <<'EOF'
set -euo pipefail

# Guardar la conf junto a las demás (persistencia). Si ya existía, se respalda y se reemplaza.
RESPALDO=""
if [ -e "$DIR/cafelaescuelita.conf" ]; then
  if cmp -s /tmp/cafelaescuelita.conf "$DIR/cafelaescuelita.conf"; then
    echo "   La conf del servidor ya es igual a la local."
  else
    RESPALDO="$DIR/cafelaescuelita.conf.bak-$(date +%Y%m%d-%H%M%S)"
    cp "$DIR/cafelaescuelita.conf" "$RESPALDO"
    echo "   Respaldo de la conf anterior: $RESPALDO"
  fi
fi
mv /tmp/cafelaescuelita.conf "$DIR/cafelaescuelita.conf"
echo "   Guardada en $DIR/cafelaescuelita.conf"

echo "2) Agregando la línea COPY al Dockerfile (con respaldo)..."
if grep -q cafelaescuelita.conf "$DIR/Dockerfile"; then
  echo "   El Dockerfile ya la tenía."
else
  cp "$DIR/Dockerfile" "$DIR/Dockerfile.bak-before-cafelaescuelita"
  sed -i '/^COPY gabsacademy.conf /a COPY cafelaescuelita.conf /etc/nginx/conf.d/cafelaescuelita.conf' "$DIR/Dockerfile"
  echo "   Listo (respaldo: Dockerfile.bak-before-cafelaescuelita)"
fi

echo "3) Cargando la conf en el servidor web y probándola..."
docker cp "$DIR/cafelaescuelita.conf" invoiceplane-nginx:/etc/nginx/conf.d/cafelaescuelita.conf
if docker exec invoiceplane-nginx nginx -t; then
  docker exec invoiceplane-nginx nginx -s reload
  echo "   Recargado sin reiniciar."
else
  if [ -n "$RESPALDO" ]; then
    echo "   ERROR en la configuración: se restaura la anterior y NO se recarga. Los demás sitios siguen igual."
    cp "$RESPALDO" "$DIR/cafelaescuelita.conf"
    docker cp "$RESPALDO" invoiceplane-nginx:/etc/nginx/conf.d/cafelaescuelita.conf
  else
    echo "   ERROR en la configuración: se quita y NO se recarga. Los demás sitios siguen igual."
    docker exec invoiceplane-nginx rm -f /etc/nginx/conf.d/cafelaescuelita.conf
  fi
  exit 1
fi
EOF

echo "4) Verificando..."
sleep 2
code=$(curl -s -o /dev/null -w "%{http_code}" https://cafelaescuelita.site/)
if curl -s https://cafelaescuelita.site/ | grep -q "Tostando los últimos detalles"; then
  echo "   OK: https://cafelaescuelita.site responde $code con la página del café."
else
  echo "   Atención: respondió $code pero no se encontró el texto de la página."
fi

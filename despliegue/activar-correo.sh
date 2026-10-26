#!/usr/bin/env bash
# Pone en marcha el servidor de la página en el VPS (formulario de contacto por correo y pagos con Bold):
# un contenedor "cafelaescuelita-correo" (Python, sin paquetes extra) en la misma red Docker que invoiceplane-nginx.
# Uso (Git Bash, desde esta carpeta):  bash activar-correo.sh
#
# Pide los secretos una sola vez y los guarda SOLO en el servidor (/opt/cafelaescuelita-correo/correo.env,
# permisos 600): la contraseña del correo que envía y, si las tienes, las llaves de Bold.
# Las siguientes veces solo actualiza el programa. Para cambiar las llaves de Bold: BOLD=cambiar bash activar-correo.sh
# Orden la primera vez: activar-correo.sh  ->  activar-sitio.sh (nginx pasa /api/)  ->  publicar.sh
set -euo pipefail
cd "$(dirname "$0")"

REMOTO=/opt/cafelaescuelita-correo
SITIO=/var/www/sistema-facturacion/cafelaescuelita.site   # el mismo DESTINO de publicar.sh

echo "1) Subiendo el programa..."
ssh hostinger-vps "mkdir -p $REMOTO/pedidos && chmod 700 $REMOTO $REMOTO/pedidos"
scp -q correo/servidor.py correo/logo-correo.jpg hostinger-vps:$REMOTO/

echo "2) Configuración (correo.env)..."
if ssh hostinger-vps "test -f $REMOTO/correo.env"; then
  echo "   Ya existe en el servidor: se conserva."
else
  read -rsp "   Contraseña de proyectos@digitalbrain.click (no se muestra): " CLAVE; echo
  [ -n "$CLAVE" ] || { echo "   ERROR: la contraseña está vacía."; exit 1; }
  { grep -v '^SMTP_CLAVE=' correo/correo.env.example | grep -v '^#'; printf 'SMTP_CLAVE=%s\n' "$CLAVE"; } \
    | ssh hostinger-vps "umask 077 && cat > $REMOTO/correo.env"
  unset CLAVE
  echo "   Guardada en $REMOTO/correo.env (solo root puede leerla)."
fi

echo "3) Llaves de Bold..."
if ssh hostinger-vps "grep -q '^BOLD_LLAVE_SECRETA=.' $REMOTO/correo.env" && [ "${BOLD:-}" != cambiar ]; then
  echo "   Ya están configuradas: se conservan. (Para cambiarlas: BOLD=cambiar bash activar-correo.sh)"
else
  read -rp "   Llave de identidad de Bold (Enter para dejar los pagos en línea apagados): " IDENTIDAD
  if [ -n "$IDENTIDAD" ]; then
    read -rsp "   Llave secreta de Bold (no se muestra): " SECRETA; echo
    [ -n "$SECRETA" ] || { echo "   ERROR: la llave secreta está vacía."; exit 1; }
    read -rp "   ¿Son llaves de PRUEBA? (s/N): " PRUEBA
    [ "$PRUEBA" = s ] || [ "$PRUEBA" = S ] && PRUEBAS=1 || PRUEBAS=0
    printf 'BOLD_LLAVE_IDENTIDAD=%s\nBOLD_LLAVE_SECRETA=%s\nBOLD_PRUEBAS=%s\n' "$IDENTIDAD" "$SECRETA" "$PRUEBAS" \
      | ssh hostinger-vps "umask 077 && sed -i '/^BOLD_/d' $REMOTO/correo.env && cat >> $REMOTO/correo.env"
    unset IDENTIDAD SECRETA
    echo "   Guardadas en $REMOTO/correo.env."
  else
    echo "   Sin llaves: el checkout seguirá cerrando pedidos por WhatsApp."
  fi
fi

echo "4) Arrancando el contenedor..."
ssh hostinger-vps "REMOTO=$REMOTO SITIO=$SITIO bash -s" <<'EOF'
set -euo pipefail
RED=$(docker inspect -f '{{range $k, $v := .NetworkSettings.Networks}}{{$k}} {{end}}' invoiceplane-nginx | awk '{print $1}')
if [ -z "$RED" ] || [ "$RED" = bridge ]; then
  echo "   ERROR: invoiceplane-nginx no está en una red propia de Docker (red: '${RED}'). No se hizo nada."
  exit 1
fi
mkdir -p "$SITIO/assets/datos"
docker rm -f cafelaescuelita-correo >/dev/null 2>&1 || true
# El catálogo publicado (solo lectura) es la fuente de precios; los pedidos se guardan en $REMOTO/pedidos
docker run -d --name cafelaescuelita-correo --restart unless-stopped \
  --network "$RED" --env-file "$REMOTO/correo.env" \
  -v "$REMOTO/servidor.py:/app/servidor.py:ro" -v "$REMOTO/logo-correo.jpg:/app/logo-correo.jpg:ro" \
  -v "$SITIO/assets/datos:/app/datos:ro" -v "$REMOTO/pedidos:/app/pedidos" \
  --memory 64m --read-only --cap-drop ALL --security-opt no-new-privileges \
  python:3.12-alpine python -u /app/servidor.py >/dev/null
sleep 3
docker logs --tail 3 cafelaescuelita-correo
if [ "$(docker inspect -f '{{.State.Running}}' cafelaescuelita-correo)" = true ]; then
  echo "   OK: contenedor en marcha en la red $RED."
else
  echo "   ERROR: el contenedor no quedó en marcha (ver: docker logs cafelaescuelita-correo)."
  exit 1
fi
EOF

echo "5) Verificando (petición de bot de prueba: responde ok y NO envía correo)..."
r=$(curl -s -X POST https://cafelaescuelita.site/api/contacto \
  -H 'Origin: https://cafelaescuelita.site' -H 'Content-Type: application/json' -d '{"botcheck":true}' || true)
if [ "$r" = '{"ok": true}' ]; then
  echo "   OK: https://cafelaescuelita.site/api/ responde."
else
  echo "   Aún no responde ($r). Si es la primera vez, corre: bash activar-sitio.sh"
fi

echo
echo "Recuerda: en el panel de Bold (Integraciones > Webhooks) registra la URL"
echo "   https://cafelaescuelita.site/api/bold/webhook"
echo "y en catalogo.js pon \"bold\": true cuando quieras cobrar en línea."

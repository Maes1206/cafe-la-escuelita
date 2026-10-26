#!/usr/bin/env bash
# Pone en marcha el envío por correo del formulario de contacto en el VPS: un contenedor
# "cafelaescuelita-correo" (Python, sin paquetes extra) en la misma red Docker que invoiceplane-nginx.
# Uso (Git Bash, desde esta carpeta):  bash activar-correo.sh
#
# La primera vez pide la contraseña del correo que envía y la guarda SOLO en el servidor
# (/opt/cafelaescuelita-correo/correo.env, permisos 600). Las siguientes veces solo actualiza el programa.
# Orden la primera vez: activar-correo.sh  ->  activar-sitio.sh (nginx pasa /api/contacto)  ->  publicar.sh
set -euo pipefail
cd "$(dirname "$0")"

REMOTO=/opt/cafelaescuelita-correo

echo "1) Subiendo el programa..."
ssh hostinger-vps "mkdir -p $REMOTO && chmod 700 $REMOTO"
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

echo "3) Arrancando el contenedor..."
ssh hostinger-vps "REMOTO=$REMOTO bash -s" <<'EOF'
set -euo pipefail
RED=$(docker inspect -f '{{range $k, $v := .NetworkSettings.Networks}}{{$k}} {{end}}' invoiceplane-nginx | awk '{print $1}')
if [ -z "$RED" ] || [ "$RED" = bridge ]; then
  echo "   ERROR: invoiceplane-nginx no está en una red propia de Docker (red: '${RED}'). No se hizo nada."
  exit 1
fi
docker rm -f cafelaescuelita-correo >/dev/null 2>&1 || true
docker run -d --name cafelaescuelita-correo --restart unless-stopped \
  --network "$RED" --env-file "$REMOTO/correo.env" \
  -v "$REMOTO/servidor.py:/app/servidor.py:ro" -v "$REMOTO/logo-correo.jpg:/app/logo-correo.jpg:ro" \
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

echo "4) Verificando (petición de bot de prueba: responde ok y NO envía correo)..."
r=$(curl -s -X POST https://cafelaescuelita.site/api/contacto \
  -H 'Origin: https://cafelaescuelita.site' -H 'Content-Type: application/json' -d '{"botcheck":true}' || true)
if [ "$r" = '{"ok": true}' ]; then
  echo "   OK: https://cafelaescuelita.site/api/contacto responde."
else
  echo "   Aún no responde ($r). Si es la primera vez, corre: bash activar-sitio.sh"
fi

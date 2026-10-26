"""
Envía los dos correos de prueba (el que recibe el cliente y la confirmación para el visitante) a una
misma dirección, con la configuración y el formato que usa el servidor.
Sirve para comprobar la cuenta SMTP de Hostinger sin tocar el VPS.

Uso (desde esta carpeta):  python probar_envio.py destino@ejemplo.com
Pide la contraseña sin mostrarla y no la guarda en ningún lado.
"""
import getpass
import os
import sys

if len(sys.argv) != 2:
    sys.exit('Uso: python probar_envio.py destino@ejemplo.com')

destino = sys.argv[1]
os.environ.setdefault('SMTP_USUARIO', 'proyectos@digitalbrain.click')
os.environ['CORREO_DESTINO'] = destino
os.environ['SMTP_CLAVE'] = getpass.getpass(f'Contraseña de {os.environ["SMTP_USUARIO"]} (no se muestra): ')

import servidor  # noqa: E402 — lee la configuración de las variables de arriba

datos = {
    'nombre': 'Prueba de la página',
    'correo': destino,
    'celular': '+57 315 734 3753',
    'motivo': 'Otra consulta',
    'mensaje': 'Este es un correo de prueba del formulario de contacto de cafelaescuelita.site.\n'
               'Si te llegó, el envío por SMTP de Hostinger funciona.',
}
print(f'Conectando a {servidor.SMTP_HOST}:{servidor.SMTP_PUERTO}...')
try:
    servidor.enviar(servidor.armar_correo(datos), servidor.armar_confirmacion(datos))
except Exception as e:  # noqa: BLE001
    sys.exit(f'ERROR: {type(e).__name__}: {e}')
print(f'OK: 2 correos de prueba enviados a {destino} (el del cliente y la confirmación).')
print('Revisa la bandeja de entrada (y la de spam).')

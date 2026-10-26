"""
Recibe el formulario de contacto de cafelaescuelita.site y lo envía por correo con el SMTP de Hostinger.

La página es estática: nginx le pasa a este programa las peticiones POST /api/contacto.
Solo usa la biblioteca estándar de Python (sin paquetes externos).

Configuración por variables de entorno (en el servidor, archivo correo.env; nunca en git):
    SMTP_USUARIO, SMTP_CLAVE      cuenta que envía (proyectos@digitalbrain.click)
    CORREO_DESTINO                a quién le llegan los mensajes (el correo del cliente)
    SMTP_HOST, SMTP_PUERTO        por defecto smtp.hostinger.com:465 (SSL)
    ORIGENES_PERMITIDOS           dominios que pueden enviar, separados por coma
    MODO_PRUEBA=1                 no envía: imprime el correo en la consola

Prueba local:
    MODO_PRUEBA=1 SMTP_USUARIO=x SMTP_CLAVE=x CORREO_DESTINO=x ORIGENES_PERMITIDOS=http://localhost:5500 python servidor.py
"""
import json
import os
import re
import smtplib
import ssl
import sys
import time
from email.message import EmailMessage
from email.utils import formataddr
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Lock

SMTP_HOST = os.environ.get('SMTP_HOST', 'smtp.hostinger.com')
SMTP_PUERTO = int(os.environ.get('SMTP_PUERTO', '465'))
SMTP_USUARIO = os.environ['SMTP_USUARIO']
SMTP_CLAVE = os.environ['SMTP_CLAVE']
CORREO_DESTINO = os.environ['CORREO_DESTINO']
ORIGENES = {o.strip() for o in os.environ.get(
    'ORIGENES_PERMITIDOS', 'https://cafelaescuelita.site,https://www.cafelaescuelita.site').split(',') if o.strip()}
MODO_PRUEBA = os.environ.get('MODO_PRUEBA') == '1'
PUERTO = int(os.environ.get('PUERTO', '8787'))

# Deben coincidir con las opciones del formulario en index.html
MOTIVOS = {
    'Quiero comprar café para mi casa',
    'Quiero café para mi negocio (al por mayor)',
    'Quiero visitar la finca',
    'Otra consulta',
}
LIMITES = {'nombre': 120, 'correo': 200, 'celular': 40, 'mensaje': 4000}
CORREO_VALIDO = re.compile(r'^[^@\s<>"]+@[^@\s<>"]+\.[^@\s<>"]+$')
TAMANO_MAXIMO = 16 * 1024

# Máximo 5 mensajes por IP cada 10 minutos (contra spam y abusos)
VENTANA, MAXIMO = 600, 5
envios: dict[str, list[float]] = {}
candado = Lock()


def permitido(ip: str) -> bool:
    ahora = time.time()
    with candado:
        recientes = [t for t in envios.get(ip, []) if ahora - t < VENTANA]
        if len(recientes) >= MAXIMO:
            envios[ip] = recientes
            return False
        recientes.append(ahora)
        envios[ip] = recientes
        return True


def limpiar(valor, limite: int, multilinea=False) -> str:
    """Texto plano, sin caracteres de control (evita inyectar cabeceras en el correo)."""
    texto = str(valor or '').strip()
    permitidos = '\n' if multilinea else ''
    texto = ''.join(c for c in texto if c >= ' ' or c in permitidos)
    return texto[:limite]


def armar_correo(d: dict) -> EmailMessage:
    msg = EmailMessage()
    msg['Subject'] = f'Nuevo mensaje de {d["nombre"]} — {d["motivo"]}'
    msg['From'] = formataddr(('Página Café la Escuelita', SMTP_USUARIO))
    msg['To'] = CORREO_DESTINO
    if d['correo']:
        msg['Reply-To'] = formataddr((d['nombre'], d['correo']))
    msg.set_content(
        'Nuevo mensaje desde el formulario de cafelaescuelita.site\n\n'
        f'Nombre:   {d["nombre"]}\n'
        f'Celular:  {d["celular"]}\n'
        f'Correo:   {d["correo"] or "(no lo dejó)"}\n'
        f'Motivo:   {d["motivo"]}\n\n'
        f'Mensaje:\n{d["mensaje"]}\n\n'
        '— \n'
        + ('Para responder, usa "Responder" en este correo o escríbele al celular.\n' if d['correo']
           else 'No dejó correo: respóndele al celular.\n')
    )
    return msg


def enviar(msg: EmailMessage):
    if MODO_PRUEBA:
        print('--- MODO_PRUEBA: correo que se habría enviado ---\n' + msg.as_string(), flush=True)
        return
    contexto = ssl.create_default_context()
    with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PUERTO, context=contexto, timeout=20) as smtp:
        smtp.login(SMTP_USUARIO, SMTP_CLAVE)
        smtp.send_message(msg)


class Manejador(BaseHTTPRequestHandler):
    server_version = 'cafelaescuelita-correo'
    sys_version = ''

    def responder(self, codigo: int, datos: dict):
        cuerpo = json.dumps(datos, ensure_ascii=False).encode()
        self.send_response(codigo)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(cuerpo)))
        self.send_header('Cache-Control', 'no-store')
        origen = self.headers.get('Origin')
        if origen in ORIGENES:
            self.send_header('Access-Control-Allow-Origin', origen)
            self.send_header('Vary', 'Origin')
        self.end_headers()
        self.wfile.write(cuerpo)

    def do_OPTIONS(self):
        if self.headers.get('Origin') not in ORIGENES:
            return self.responder(403, {'ok': False})
        self.send_response(204)
        self.send_header('Access-Control-Allow-Origin', self.headers['Origin'])
        self.send_header('Access-Control-Allow-Methods', 'POST')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.send_header('Vary', 'Origin')
        self.end_headers()

    def do_GET(self):
        self.responder(405, {'ok': False, 'error': 'Usa POST.'})

    def do_POST(self):
        if self.path.split('?')[0] != '/api/contacto':
            return self.responder(404, {'ok': False})
        if self.headers.get('Origin') not in ORIGENES:
            return self.responder(403, {'ok': False, 'error': 'Origen no permitido.'})
        largo = int(self.headers.get('Content-Length') or 0)
        if not 0 < largo <= TAMANO_MAXIMO:
            return self.responder(413, {'ok': False, 'error': 'Mensaje demasiado largo.'})
        try:
            datos = json.loads(self.rfile.read(largo))
            assert isinstance(datos, dict)
        except Exception:
            return self.responder(400, {'ok': False, 'error': 'Datos inválidos.'})

        # Trampa para bots: se responde "ok" para no darles pistas, pero no se envía nada
        if datos.get('botcheck'):
            return self.responder(200, {'ok': True})

        d = {
            'nombre': limpiar(datos.get('nombre'), LIMITES['nombre']),
            'correo': limpiar(datos.get('correo'), LIMITES['correo']),
            'celular': limpiar(datos.get('celular'), LIMITES['celular']),
            'motivo': limpiar(datos.get('motivo'), 80),
            'mensaje': limpiar(datos.get('mensaje'), LIMITES['mensaje'], multilinea=True),
        }
        if not (d['nombre'] and d['celular'] and d['mensaje']):
            return self.responder(400, {'ok': False, 'error': 'Faltan datos obligatorios.'})
        if d['motivo'] not in MOTIVOS:
            d['motivo'] = 'Otra consulta'
        if d['correo'] and not CORREO_VALIDO.match(d['correo']):
            return self.responder(400, {'ok': False, 'error': 'El correo no es válido.'})

        ip = self.headers.get('X-Real-IP') or self.client_address[0]
        if not permitido(ip):
            return self.responder(429, {'ok': False, 'error': 'Demasiados mensajes. Intenta más tarde.'})

        try:
            enviar(armar_correo(d))
        except Exception as e:  # noqa: BLE001 — se registra el tipo de error, nunca la clave
            print(f'Error enviando correo: {type(e).__name__}: {e}', file=sys.stderr, flush=True)
            return self.responder(502, {'ok': False, 'error': 'No se pudo enviar el correo.'})
        return self.responder(200, {'ok': True})

    def log_message(self, formato, *args):
        # Sin datos personales en el registro: solo método, ruta y código
        print(f'{self.address_string()} "{self.requestline}" {args[1] if len(args) > 1 else ""}', flush=True)


if __name__ == '__main__':
    print(f'Escuchando en el puerto {PUERTO} · destino {CORREO_DESTINO} · '
          f'{"MODO_PRUEBA (no envía)" if MODO_PRUEBA else f"SMTP {SMTP_HOST}:{SMTP_PUERTO}"}', flush=True)
    ThreadingHTTPServer(('0.0.0.0', PUERTO), Manejador).serve_forever()

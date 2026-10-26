"""
Recibe el formulario de contacto de cafelaescuelita.site y lo envía por correo con el SMTP de Hostinger.

La página es estática: nginx le pasa a este programa las peticiones POST /api/contacto.
Solo usa la biblioteca estándar de Python (sin paquetes externos).

Configuración por variables de entorno (en el servidor, archivo correo.env; nunca en git):
    SMTP_USUARIO, SMTP_CLAVE      cuenta que envía (proyectos@digitalbrain.click)
    CORREO_DESTINO                a quién le llegan los mensajes (el correo del cliente)
    WHATSAPP_CLIENTE              número que se muestra en los correos (por defecto +57 315 734 3753)

Por cada mensaje se envían dos correos con el logo (logo-correo.jpg, junto a este archivo): uno al cliente
y, si la persona dejó su correo, una confirmación de recibido para ella.
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
from email.utils import formataddr, make_msgid
from html import escape
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
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


# Logo incrustado en los correos (va dentro del mensaje: se ve aunque el correo bloquee imágenes externas)
LOGO = Path(__file__).with_name('logo-correo.jpg')
LOGO_BYTES = LOGO.read_bytes() if LOGO.exists() else None
WHATSAPP = os.environ.get('WHATSAPP_CLIENTE', '+57 315 734 3753')

# Colores de la página
CAFE, CAFE_SUAVE, TERRACOTA, MOSTAZA, CREMA = '#1c110b', '#5c4a3f', '#a4502a', '#d9a13a', '#f8f3ea'


def plantilla(titulo: str, cuerpo: str, cid_logo: str | None) -> str:
    """HTML de correo con tablas y estilos en línea (lo que mejor soportan Gmail, Outlook y el celular)."""
    logo = (f'<img src="cid:{cid_logo}" width="96" height="96" alt="Café la Escuelita" '
            f'style="display:block;margin:0 auto;border:0;border-radius:12px">' if cid_logo else '')
    return f'''<!doctype html>
<html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:{CREMA}">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:{CREMA};padding:28px 12px">
<tr><td align="center">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0"
    style="max-width:560px;background:#ffffff;border-radius:16px;overflow:hidden;font-family:Arial,Helvetica,sans-serif;color:{CAFE}">
    <tr><td style="height:5px;background:linear-gradient(90deg,#a05206,#e3a205,#fbbb06);background-color:{MOSTAZA}"></td></tr>
    <tr><td style="padding:28px 32px 4px;text-align:center">{logo}
      <p style="margin:14px 0 0;font-size:11px;letter-spacing:3px;text-transform:uppercase;color:{TERRACOTA};font-weight:bold">Café la Escuelita</p>
      <h1 style="margin:10px 0 0;font-family:Georgia,'Times New Roman',serif;font-weight:normal;font-size:26px;line-height:1.25;color:{CAFE}">{titulo}</h1>
    </td></tr>
    <tr><td style="padding:20px 32px 30px;font-size:15px;line-height:1.6;color:{CAFE_SUAVE}">{cuerpo}</td></tr>
    <tr><td style="padding:18px 32px;background:{CREMA};text-align:center;font-size:12px;line-height:1.6;color:{CAFE_SUAVE}">
      Finca La Escuelita · Iquira, Huila, Colombia<br>
      WhatsApp {WHATSAPP} · <a href="https://cafelaescuelita.site" style="color:{TERRACOTA}">cafelaescuelita.site</a>
    </td></tr>
  </table>
</td></tr></table>
</body></html>'''


def filas(datos: list[tuple[str, str]]) -> str:
    celdas = ''.join(
        f'<tr><td style="padding:9px 0;border-bottom:1px solid #eee3d3;color:#8a7a6f;width:96px;vertical-align:top">{escape(k)}</td>'
        f'<td style="padding:9px 0;border-bottom:1px solid #eee3d3;color:{CAFE};font-weight:bold">{escape(v)}</td></tr>'
        for k, v in datos)
    return f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="font-size:14px">{celdas}</table>'


def con_html(msg: EmailMessage, texto: str, titulo: str, cuerpo: str):
    """Texto plano + HTML con el logo incrustado."""
    msg.set_content(texto)
    cid = make_msgid(domain='cafelaescuelita.site') if LOGO_BYTES else None
    msg.add_alternative(plantilla(titulo, cuerpo, cid[1:-1] if cid else None), subtype='html')
    if cid:
        msg.get_payload()[1].add_related(LOGO_BYTES, 'image', 'jpeg', cid=cid, filename='logo.jpg')


def armar_correo(d: dict) -> EmailMessage:
    """El mensaje que le llega al cliente."""
    msg = EmailMessage()
    msg['Subject'] = f'Nuevo mensaje de {d["nombre"]} — {d["motivo"]}'
    msg['From'] = formataddr(('Página Café la Escuelita', SMTP_USUARIO))
    msg['To'] = CORREO_DESTINO
    if d['correo']:
        msg['Reply-To'] = formataddr((d['nombre'], d['correo']))
    pie = ('Para responder, usa "Responder" en este correo o escríbele al celular.' if d['correo']
           else 'No dejó correo: respóndele al celular.')
    texto = (
        'Nuevo mensaje desde el formulario de cafelaescuelita.site\n\n'
        f'Nombre:   {d["nombre"]}\n'
        f'Celular:  {d["celular"]}\n'
        f'Correo:   {d["correo"] or "(no lo dejó)"}\n'
        f'Motivo:   {d["motivo"]}\n\n'
        f'Mensaje:\n{d["mensaje"]}\n\n— \n{pie}\n'
    )
    cuerpo = (
        f'<p style="margin:0 0 18px">Alguien escribió desde el formulario de la página.</p>'
        + filas([('Nombre', d['nombre']), ('Celular', d['celular']),
                 ('Correo', d['correo'] or '(no lo dejó)'), ('Motivo', d['motivo'])])
        + f'<p style="margin:22px 0 8px;font-size:11px;letter-spacing:2px;text-transform:uppercase;color:{TERRACOTA};font-weight:bold">Mensaje</p>'
        f'<div style="padding:16px 18px;background:{CREMA};border-radius:10px;color:{CAFE};white-space:pre-wrap">{escape(d["mensaje"])}</div>'
        f'<p style="margin:22px 0 0;font-size:13px;color:#8a7a6f">{escape(pie)}</p>'
    )
    con_html(msg, texto, 'Nuevo mensaje desde la página', cuerpo)
    return msg


def armar_confirmacion(d: dict) -> EmailMessage:
    """Acuse de recibo para quien escribió. No repite su mensaje (así nadie puede usar el formulario
    para mandarle texto propio a un tercero) y las respuestas van directo al correo del cliente."""
    nombre = d['nombre'].split(' ')[0][:40]
    msg = EmailMessage()
    msg['Subject'] = 'Recibimos tu mensaje — Café la Escuelita'
    msg['From'] = formataddr(('Café la Escuelita', SMTP_USUARIO))
    msg['To'] = d['correo']
    msg['Reply-To'] = CORREO_DESTINO
    texto = (
        f'Hola, {nombre}:\n\n'
        'Gracias por escribirnos. Recibimos tu mensaje y te responderemos pronto a este correo.\n\n'
        f'Motivo: {d["motivo"]}\n\n'
        f'Si es urgente, escríbenos por WhatsApp al {WHATSAPP}.\n\n'
        'Un abrazo desde la finca,\nFamilia La Escuelita\n'
    )
    cuerpo = (
        f'<p style="margin:0 0 14px">Hola, <strong style="color:{CAFE}">{escape(nombre)}</strong>:</p>'
        '<p style="margin:0 0 14px">Gracias por escribirnos. Recibimos tu mensaje y te responderemos pronto a este correo.</p>'
        + filas([('Motivo', d['motivo'])])
        + f'<p style="margin:22px 0 0">Si es urgente, escríbenos por WhatsApp:</p>'
        f'<p style="margin:14px 0 0;text-align:center"><a href="https://wa.me/{re.sub(r"[^0-9]", "", WHATSAPP)}" '
        f'style="display:inline-block;padding:12px 22px;background:{MOSTAZA};color:{CAFE};text-decoration:none;'
        f'font-weight:bold;border-radius:8px">Escribir por WhatsApp</a></p>'
        f'<p style="margin:26px 0 0;font-family:Georgia,serif;font-style:italic;color:{CAFE}">Un abrazo desde la finca,<br>Familia La Escuelita</p>'
    )
    con_html(msg, texto, '¡Recibimos tu mensaje!', cuerpo)
    return msg


def enviar(*mensajes: EmailMessage):
    """Envía en una sola conexión. Si falla el primero (el del cliente) es un error; si solo falla
    la confirmación, se registra y el envío se da por bueno (el cliente ya tiene el mensaje)."""
    if MODO_PRUEBA:
        for m in mensajes:
            print(f'--- MODO_PRUEBA: se habría enviado a {m["To"]} · {m["Subject"]} ---', flush=True)
        return
    contexto = ssl.create_default_context()
    with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PUERTO, context=contexto, timeout=20) as smtp:
        smtp.login(SMTP_USUARIO, SMTP_CLAVE)
        smtp.send_message(mensajes[0])
        for m in mensajes[1:]:
            try:
                smtp.send_message(m)
            except Exception as e:  # noqa: BLE001
                print(f'No se pudo enviar la confirmación: {type(e).__name__}: {e}', file=sys.stderr, flush=True)


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
            enviar(armar_correo(d), *([armar_confirmacion(d)] if d['correo'] else []))
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

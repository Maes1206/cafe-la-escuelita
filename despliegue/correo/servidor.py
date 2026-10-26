"""
Servidor de cafelaescuelita.site: formulario de contacto (correo) y pagos con Bold.

La página es estática: nginx le pasa a este programa las peticiones /api/...
Solo usa la biblioteca estándar de Python (sin paquetes externos).

    POST /api/contacto      formulario de contacto -> correo al cliente (+ confirmación al visitante)
    POST /api/pedido        carrito del checkout -> recalcula el total con el catálogo, guarda el pedido
                            y devuelve la firma de integridad para abrir el checkout de Bold
    POST /api/bold/webhook  aviso de Bold (pago aprobado, rechazado, anulado) -> actualiza el pedido y,
                            si se aprobó, envía el pedido al cliente y la confirmación al comprador

Configuración por variables de entorno (en el servidor, archivo correo.env; nunca en git):
    SMTP_USUARIO, SMTP_CLAVE      cuenta que envía (proyectos@digitalbrain.click)
    CORREO_DESTINO                a quién le llegan los mensajes y pedidos (el correo del cliente)
    BOLD_LLAVE_IDENTIDAD          llave pública de Bold (va en la página al abrir el checkout)
    BOLD_LLAVE_SECRETA            llave secreta de Bold: firma los pagos y verifica los webhooks
    BOLD_PRUEBAS=1                llaves de prueba: Bold firma los webhooks de prueba con una llave vacía
    WHATSAPP_CLIENTE              número que se muestra en los correos (por defecto +57 315 734 3753)
    CATALOGO_RUTA                 catálogo publicado (por defecto /app/datos/catalogo.js)
    PEDIDOS_DIR                   carpeta donde se guardan los pedidos (por defecto /app/pedidos)
    SMTP_HOST, SMTP_PUERTO        por defecto smtp.hostinger.com:465 (SSL)
    ORIGENES_PERMITIDOS           dominios que pueden usar /api/contacto y /api/pedido, separados por coma
    MODO_PRUEBA=1                 no envía correos: los anuncia en la consola

Los correos llevan el logo (logo-correo.jpg, junto a este archivo).

Prueba local:
    MODO_PRUEBA=1 SMTP_USUARIO=x SMTP_CLAVE=x CORREO_DESTINO=x ORIGENES_PERMITIDOS=http://localhost:5500 python servidor.py
"""
import base64
import hashlib
import hmac
import json
import os
import re
import secrets
import smtplib
import ssl
import sys
import time
from datetime import datetime, timezone
from email.message import EmailMessage
from email.utils import formataddr, make_msgid
from html import escape
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Lock, Thread

SMTP_HOST = os.environ.get('SMTP_HOST', 'smtp.hostinger.com')
SMTP_PUERTO = int(os.environ.get('SMTP_PUERTO', '465'))
SMTP_USUARIO = os.environ['SMTP_USUARIO']
SMTP_CLAVE = os.environ['SMTP_CLAVE']
CORREO_DESTINO = os.environ['CORREO_DESTINO']
ORIGENES = {o.strip() for o in os.environ.get(
    'ORIGENES_PERMITIDOS', 'https://cafelaescuelita.site,https://www.cafelaescuelita.site').split(',') if o.strip()}
MODO_PRUEBA = os.environ.get('MODO_PRUEBA') == '1'
PUERTO = int(os.environ.get('PUERTO', '8787'))

BOLD_LLAVE_IDENTIDAD = os.environ.get('BOLD_LLAVE_IDENTIDAD', '')
BOLD_LLAVE_SECRETA = os.environ.get('BOLD_LLAVE_SECRETA', '')
BOLD_PRUEBAS = os.environ.get('BOLD_PRUEBAS') == '1'
CATALOGO_RUTA = Path(os.environ.get('CATALOGO_RUTA', '/app/datos/catalogo.js'))
PEDIDOS_DIR = Path(os.environ.get('PEDIDOS_DIR', '/app/pedidos'))

# Deben coincidir con las opciones del formulario en index.html
MOTIVOS = {
    'Quiero comprar café para mi casa',
    'Quiero café para mi negocio (al por mayor)',
    'Quiero visitar la finca',
    'Otra consulta',
}
# Deben coincidir con el checkout (assets/js/tienda.js)
MOLIENDAS = {'grano': 'En grano', 'molido': 'Molido'}
DOCUMENTOS = {'CC', 'CE', 'NIT', 'PP'}
LIMITES = {'nombre': 120, 'correo': 200, 'celular': 40, 'mensaje': 4000}
CORREO_VALIDO = re.compile(r'^[^@\s<>"]+@[^@\s<>"]+\.[^@\s<>"]+$')
PEDIDO_VALIDO = re.compile(r'^CLE-[A-Z0-9]{6,30}$')
TAMANO_MAXIMO = 16 * 1024

# Máximo 5 envíos por IP cada 10 minutos en cada formulario (contra spam y abusos)
VENTANA, MAXIMO = 600, 5
envios: dict[str, list[float]] = {}
candado = Lock()
candado_pedidos = Lock()


def permitido(clave: str) -> bool:
    ahora = time.time()
    with candado:
        recientes = [t for t in envios.get(clave, []) if ahora - t < VENTANA]
        if len(recientes) >= MAXIMO:
            envios[clave] = recientes
            return False
        recientes.append(ahora)
        envios[clave] = recientes
        return True


def limpiar(valor, limite: int, multilinea=False) -> str:
    """Texto plano, sin caracteres de control (evita inyectar cabeceras en el correo)."""
    texto = str(valor or '').strip()
    permitidos = '\n' if multilinea else ''
    texto = ''.join(c for c in texto if c >= ' ' or c in permitidos)
    return texto[:limite]


def dinero(n: int) -> str:
    return f'$ {n:,.0f}'.replace(',', '.')


# ---------------------------------------------------------------- correos

# Logo incrustado en los correos (va dentro del mensaje: se ve aunque el correo bloquee imágenes externas)
LOGO = Path(__file__).with_name('logo-correo.jpg')
LOGO_BYTES = LOGO.read_bytes() if LOGO.exists() else None
WHATSAPP = os.environ.get('WHATSAPP_CLIENTE', '+57 315 734 3753')

# Colores de la página
CAFE, CAFE_SUAVE, TERRACOTA, MOSTAZA, CREMA = '#1c110b', '#5c4a3f', '#a4502a', '#d9a13a', '#f8f3ea'
SUBTITULO = f'margin:24px 0 8px;font-size:11px;letter-spacing:2px;text-transform:uppercase;color:{TERRACOTA};font-weight:bold'


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


def boton_whatsapp() -> str:
    return (f'<p style="margin:14px 0 0;text-align:center"><a href="https://wa.me/{re.sub(r"[^0-9]", "", WHATSAPP)}" '
            f'style="display:inline-block;padding:12px 22px;background:{MOSTAZA};color:{CAFE};text-decoration:none;'
            f'font-weight:bold;border-radius:8px">Escribir por WhatsApp</a></p>')


def con_html(msg: EmailMessage, texto: str, titulo: str, cuerpo: str):
    """Texto plano + HTML con el logo incrustado."""
    msg.set_content(texto)
    cid = make_msgid(domain='cafelaescuelita.site') if LOGO_BYTES else None
    msg.add_alternative(plantilla(titulo, cuerpo, cid[1:-1] if cid else None), subtype='html')
    if cid:
        msg.get_payload()[1].add_related(LOGO_BYTES, 'image', 'jpeg', cid=cid, filename='logo.jpg')


def armar_correo(d: dict) -> EmailMessage:
    """El mensaje del formulario de contacto que le llega al cliente."""
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
        + f'<p style="{SUBTITULO}">Mensaje</p>'
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
        + '<p style="margin:22px 0 0">Si es urgente, escríbenos por WhatsApp:</p>'
        + boton_whatsapp()
        + f'<p style="margin:26px 0 0;font-family:Georgia,serif;font-style:italic;color:{CAFE}">Un abrazo desde la finca,<br>Familia La Escuelita</p>'
    )
    con_html(msg, texto, '¡Recibimos tu mensaje!', cuerpo)
    return msg


def tabla_pedido(p: dict) -> tuple[str, str]:
    """Productos y totales del pedido, en texto plano y en HTML."""
    lineas = [f'{i["cantidad"]} × {i["nombre"]} {i["peso"]} · {MOLIENDAS[i["molienda"]]}' for i in p['items']]
    texto = '\n'.join(f'• {l} — {dinero(i["subtotal"])}' for l, i in zip(lineas, p['items']))
    texto += (f'\n\nSubtotal: {dinero(p["subtotal"])}\nEnvío: {dinero(p["envio"]) if p["envio"] else "Gratis"}'
              f'\nTotal: {dinero(p["total"])}')
    celdas = ''.join(
        f'<tr><td style="padding:9px 0;border-bottom:1px solid #eee3d3;color:{CAFE}">{escape(l)}</td>'
        f'<td style="padding:9px 0;border-bottom:1px solid #eee3d3;color:{CAFE};text-align:right;white-space:nowrap">{dinero(i["subtotal"])}</td></tr>'
        for l, i in zip(lineas, p['items']))
    totales = [('Subtotal', dinero(p['subtotal'])), ('Envío', dinero(p['envio']) if p['envio'] else 'Gratis')]
    celdas += ''.join(
        f'<tr><td style="padding:6px 0;color:#8a7a6f">{k}</td><td style="padding:6px 0;text-align:right;color:{CAFE}">{v}</td></tr>'
        for k, v in totales)
    celdas += (f'<tr><td style="padding:10px 0;border-top:1px solid #eee3d3;color:{CAFE};font-weight:bold">Total</td>'
               f'<td style="padding:10px 0;border-top:1px solid #eee3d3;text-align:right;color:{CAFE};font-weight:bold;font-size:17px">{dinero(p["total"])}</td></tr>')
    return texto, f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="font-size:14px">{celdas}</table>'


def direccion(p: dict) -> str:
    e = p['entrega']
    indicaciones = f' ({e["indicaciones"]})' if e['indicaciones'] else ''
    return f'{e["direccion"]}{indicaciones}, {e["ciudad"]}, {e["departamento"]}'


def armar_pedido_cliente(p: dict) -> EmailMessage:
    """Pedido pagado (o para revisar) que le llega al cliente para despacharlo."""
    c = p['cliente']
    revisar = p['estado'] == 'revisar'
    msg = EmailMessage()
    msg['Subject'] = (f'{"REVISAR pago del" if revisar else "Pedido pagado"} {p["id"]} — {dinero(p["total"])} — {c["nombre"]}')
    msg['From'] = formataddr(('Tienda Café la Escuelita', SMTP_USUARIO))
    msg['To'] = CORREO_DESTINO
    msg['Reply-To'] = formataddr((c['nombre'], c['correo']))
    productos_txt, productos_html = tabla_pedido(p)
    aviso = ('OJO: el monto que reportó Bold no coincide con el total del pedido. Revísalo en el panel de Bold '
             'antes de despachar.' if revisar else 'Bold confirmó el pago. Ya puedes preparar y despachar el pedido.')
    texto = (
        f'{aviso}\n\nPedido: {p["id"]}\nPago Bold: {p.get("pago_bold") or "-"}\n\n{productos_txt}\n\n'
        f'Cliente: {c["nombre"]}\n{c["tipoDocumento"]}: {c["documento"]}\nCelular: {c["celular"]}\nCorreo: {c["correo"]}\n'
        f'Enviar a: {direccion(p)}\n' + (f'\nNotas: {p["notas"]}\n' if p['notas'] else '')
    )
    cuerpo = (
        f'<p style="margin:0 0 6px;{"color:#b91c1c;font-weight:bold" if revisar else ""}">{escape(aviso)}</p>'
        + f'<p style="{SUBTITULO}">Productos</p>' + productos_html
        + f'<p style="{SUBTITULO}">Cliente y envío</p>'
        + filas([('Pedido', p['id']), ('Pago Bold', p.get('pago_bold') or '-'), ('Nombre', c['nombre']),
                 (c['tipoDocumento'], c['documento']), ('Celular', c['celular']), ('Correo', c['correo']),
                 ('Enviar a', direccion(p))] + ([('Notas', p['notas'])] if p['notas'] else []))
    )
    con_html(msg, texto, 'Pedido para revisar' if revisar else '¡Nuevo pedido pagado!', cuerpo)
    return msg


def armar_pedido_comprador(p: dict) -> EmailMessage:
    """Confirmación de pago para quien compró; las respuestas van al correo del cliente."""
    nombre = p['cliente']['nombre'].split(' ')[0][:40]
    msg = EmailMessage()
    msg['Subject'] = f'Recibimos tu pago — Pedido {p["id"]} — Café la Escuelita'
    msg['From'] = formataddr(('Café la Escuelita', SMTP_USUARIO))
    msg['To'] = p['cliente']['correo']
    msg['Reply-To'] = CORREO_DESTINO
    productos_txt, productos_html = tabla_pedido(p)
    texto = (
        f'Hola, {nombre}:\n\nRecibimos el pago de tu pedido {p["id"]}. ¡Gracias por elegir nuestro café!\n\n'
        f'{productos_txt}\n\nLo enviaremos a: {direccion(p)}\n\n'
        f'Te avisaremos cuando salga de la finca. Si tienes dudas, escríbenos por WhatsApp al {WHATSAPP}.\n\n'
        'Un abrazo desde la finca,\nFamilia La Escuelita\n'
    )
    cuerpo = (
        f'<p style="margin:0 0 14px">Hola, <strong style="color:{CAFE}">{escape(nombre)}</strong>:</p>'
        f'<p style="margin:0 0 6px">Recibimos el pago de tu pedido <strong style="color:{CAFE}">{escape(p["id"])}</strong>. '
        '¡Gracias por elegir nuestro café!</p>'
        + f'<p style="{SUBTITULO}">Tu pedido</p>' + productos_html
        + f'<p style="{SUBTITULO}">Envío</p>' + filas([('Enviar a', direccion(p))])
        + '<p style="margin:22px 0 0">Te avisaremos cuando salga de la finca. ¿Dudas? Escríbenos:</p>'
        + boton_whatsapp()
        + f'<p style="margin:26px 0 0;font-family:Georgia,serif;font-style:italic;color:{CAFE}">Un abrazo desde la finca,<br>Familia La Escuelita</p>'
    )
    con_html(msg, texto, '¡Recibimos tu pago!', cuerpo)
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


# ---------------------------------------------------------------- pedidos y Bold

def leer_catalogo() -> dict:
    """El mismo catálogo que publica la página (window.CATALOGO = {...};): una sola fuente de precios."""
    texto = CATALOGO_RUTA.read_text(encoding='utf-8')
    inicio = texto.index('{', texto.index('window.CATALOGO'))
    return json.loads(texto[inicio:texto.rindex('}') + 1])


def armar_pedido(datos: dict) -> tuple[dict | None, str]:
    """Valida el carrito y lo valora con los precios del servidor (nunca con los que manda el navegador)."""
    catalogo = leer_catalogo()
    productos = {p['id']: p for p in catalogo['productos']}
    items_in = datos.get('items')
    if not isinstance(items_in, list) or not 0 < len(items_in) <= 20:
        return None, 'El carrito está vacío.'
    items = []
    for it in items_in:
        if not isinstance(it, dict):
            return None, 'Datos inválidos.'
        prod = productos.get(it.get('id'))
        cantidad = it.get('cantidad')
        if not prod or prod.get('agotado') or it.get('molienda') not in MOLIENDAS \
                or not isinstance(cantidad, int) or not 0 < cantidad <= 20:
            return None, 'Algún producto del carrito ya no está disponible. Revisa el carrito.'
        items.append({'id': prod['id'], 'nombre': prod['nombre'], 'peso': prod['peso'], 'molienda': it['molienda'],
                      'cantidad': cantidad, 'precio': prod['precio'], 'subtotal': prod['precio'] * cantidad})

    c_in, e_in = datos.get('cliente') or {}, datos.get('envio') or {}
    cliente = {
        'nombre': limpiar(c_in.get('nombre'), 120), 'correo': limpiar(c_in.get('correo'), 200),
        'celular': limpiar(c_in.get('celular'), 40), 'tipoDocumento': limpiar(c_in.get('tipoDocumento'), 4),
        'documento': limpiar(c_in.get('documento'), 20),
    }
    entrega = {
        'departamento': limpiar(e_in.get('departamento'), 60), 'ciudad': limpiar(e_in.get('ciudad'), 80),
        'direccion': limpiar(e_in.get('direccion'), 160), 'indicaciones': limpiar(e_in.get('indicaciones'), 160),
    }
    if not all(cliente.values()) or not all(v for k, v in entrega.items() if k != 'indicaciones'):
        return None, 'Faltan datos de contacto o de envío.'
    if not CORREO_VALIDO.match(cliente['correo']):
        return None, 'El correo no es válido.'
    if cliente['tipoDocumento'] not in DOCUMENTOS:
        return None, 'El tipo de documento no es válido.'

    subtotal = sum(i['subtotal'] for i in items)
    envio = 0 if subtotal >= catalogo['envio']['gratisDesde'] else catalogo['envio']['costo']
    return {
        'id': f'CLE-{int(time.time()):X}{secrets.token_hex(2).upper()}',
        'creado': datetime.now(timezone.utc).isoformat(timespec='seconds'),
        'estado': 'pendiente', 'moneda': catalogo['moneda'],
        'items': items, 'subtotal': subtotal, 'envio': envio, 'total': subtotal + envio,
        'cliente': cliente, 'entrega': entrega, 'notas': limpiar(datos.get('notas'), 500, multilinea=True),
        'eventos': [],
    }, ''


def ruta_pedido(pedido_id: str) -> Path | None:
    return PEDIDOS_DIR / f'{pedido_id}.json' if PEDIDO_VALIDO.match(pedido_id or '') else None


def guardar_pedido(p: dict):
    ruta = ruta_pedido(p['id'])
    temporal = ruta.with_suffix('.tmp')
    temporal.write_text(json.dumps(p, ensure_ascii=False, indent=2), encoding='utf-8')
    temporal.replace(ruta)  # escritura atómica


def firma_integridad(pedido_id: str, monto: int, moneda: str) -> str:
    """Bold: SHA-256 de {Identificador}{Monto}{Divisa}{LlaveSecreta}."""
    return hashlib.sha256(f'{pedido_id}{monto}{moneda}{BOLD_LLAVE_SECRETA}'.encode()).hexdigest()


def firma_webhook_valida(cuerpo: bytes, firma: str) -> bool:
    """Bold: HMAC-SHA256 (llave secreta; vacía en pruebas) sobre el cuerpo en Base64, en hexadecimal."""
    clave = '' if BOLD_PRUEBAS else BOLD_LLAVE_SECRETA
    esperada = hmac.new(clave.encode(), base64.b64encode(cuerpo), hashlib.sha256).hexdigest()
    return hmac.compare_digest(esperada, (firma or '').strip().lower())


ESTADOS = {'SALE_APPROVED': 'pagado', 'SALE_REJECTED': 'rechazado', 'VOID_APPROVED': 'anulado'}


def procesar_evento(evento: dict):
    """Actualiza el pedido con el aviso de Bold. Bold puede repetir avisos: cada pago y tipo se procesa una vez."""
    tipo = evento.get('type')
    data = evento.get('data') or {}
    referencia = (data.get('metadata') or {}).get('reference') or ''
    pago = str(data.get('payment_id') or evento.get('subject') or '')
    ruta = ruta_pedido(referencia)
    if not ruta or not ruta.exists():
        print(f'Webhook {tipo}: pedido "{referencia}" desconocido (pago {pago})', file=sys.stderr, flush=True)
        return
    with candado_pedidos:
        p = json.loads(ruta.read_text(encoding='utf-8'))
        if any(e['pago'] == pago and e['tipo'] == tipo for e in p['eventos']):
            return  # aviso repetido
        p['eventos'].append({'tipo': tipo, 'pago': pago, 'recibido': datetime.now(timezone.utc).isoformat(timespec='seconds'),
                             'metodo': data.get('payment_method'), 'monto': (data.get('amount') or {}).get('total')})
        anterior = p['estado']
        # Un rechazo tardío no deshace un pago aprobado; una anulación aprobada sí cambia el estado
        if (tipo in ESTADOS and anterior != 'pagado') or tipo == 'VOID_APPROVED':
            p['estado'] = ESTADOS[tipo]
        if tipo == 'SALE_APPROVED':
            p['pago_bold'] = pago
            try:
                pagado = int(float((data.get('amount') or {}).get('total')))
            except (TypeError, ValueError):
                pagado = -1
            if pagado != p['total']:
                p['estado'] = 'revisar'
                print(f'Pedido {p["id"]}: Bold reportó {pagado} y el pedido es {p["total"]}', file=sys.stderr, flush=True)
        guardar_pedido(p)
    print(f'Pedido {p["id"]}: {anterior} -> {p["estado"]} ({tipo})', flush=True)
    if tipo == 'SALE_APPROVED' and anterior not in ('pagado', 'revisar'):
        # Si el monto no cuadra, solo se avisa al cliente: al comprador no se le confirma un pago dudoso
        mensajes = [armar_pedido_cliente(p)] + ([] if p['estado'] == 'revisar' else [armar_pedido_comprador(p)])
        try:
            enviar(*mensajes)
        except Exception as e:  # noqa: BLE001
            print(f'Pedido {p["id"]}: no se pudieron enviar los correos: {type(e).__name__}: {e}', file=sys.stderr, flush=True)


# ---------------------------------------------------------------- HTTP

class Manejador(BaseHTTPRequestHandler):
    server_version = 'cafelaescuelita'
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

    def leer_cuerpo(self) -> bytes | None:
        largo = int(self.headers.get('Content-Length') or 0)
        if not 0 < largo <= TAMANO_MAXIMO:
            self.responder(413, {'ok': False, 'error': 'Mensaje demasiado largo.'})
            return None
        return self.rfile.read(largo)

    def do_POST(self):
        ruta = self.path.split('?')[0]
        if ruta == '/api/bold/webhook':
            return self.webhook()
        if ruta not in ('/api/contacto', '/api/pedido'):
            return self.responder(404, {'ok': False})
        if self.headers.get('Origin') not in ORIGENES:
            return self.responder(403, {'ok': False, 'error': 'Origen no permitido.'})
        cuerpo = self.leer_cuerpo()
        if cuerpo is None:
            return
        try:
            datos = json.loads(cuerpo)
            assert isinstance(datos, dict)
        except Exception:
            return self.responder(400, {'ok': False, 'error': 'Datos inválidos.'})
        ip = self.headers.get('X-Real-IP') or self.client_address[0]
        if ruta == '/api/pedido':
            return self.pedido(datos, ip)
        return self.contacto(datos, ip)

    def contacto(self, datos: dict, ip: str):
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
        if not permitido(f'contacto:{ip}'):
            return self.responder(429, {'ok': False, 'error': 'Demasiados mensajes. Intenta más tarde.'})

        try:
            enviar(armar_correo(d), *([armar_confirmacion(d)] if d['correo'] else []))
        except Exception as e:  # noqa: BLE001 — se registra el tipo de error, nunca la clave
            print(f'Error enviando correo: {type(e).__name__}: {e}', file=sys.stderr, flush=True)
            return self.responder(502, {'ok': False, 'error': 'No se pudo enviar el correo.'})
        return self.responder(200, {'ok': True})

    def pedido(self, datos: dict, ip: str):
        if not (BOLD_LLAVE_IDENTIDAD and BOLD_LLAVE_SECRETA):
            return self.responder(503, {'ok': False, 'error': 'Los pagos en línea no están disponibles.'})
        if not permitido(f'pedido:{ip}'):
            return self.responder(429, {'ok': False, 'error': 'Demasiados intentos. Intenta más tarde.'})
        try:
            p, error = armar_pedido(datos)
        except Exception as e:  # noqa: BLE001 — catálogo ilegible, etc.
            print(f'Error armando el pedido: {type(e).__name__}: {e}', file=sys.stderr, flush=True)
            return self.responder(500, {'ok': False, 'error': 'No se pudo preparar el pago.'})
        if not p:
            return self.responder(400, {'ok': False, 'error': error})
        with candado_pedidos:
            guardar_pedido(p)
        print(f'Pedido {p["id"]}: creado por {p["total"]} {p["moneda"]}', flush=True)
        return self.responder(200, {
            'orderId': p['id'], 'amount': str(p['total']), 'currency': p['moneda'],
            'apiKey': BOLD_LLAVE_IDENTIDAD, 'integritySignature': firma_integridad(p['id'], p['total'], p['moneda']),
        })

    def webhook(self):
        if not (BOLD_PRUEBAS or BOLD_LLAVE_SECRETA):
            return self.responder(503, {'ok': False})
        cuerpo = self.leer_cuerpo()
        if cuerpo is None:
            return
        if not firma_webhook_valida(cuerpo, self.headers.get('x-bold-signature')):
            print('Webhook con firma inválida: descartado', file=sys.stderr, flush=True)
            return self.responder(401, {'ok': False})
        try:
            evento = json.loads(cuerpo)
            assert isinstance(evento, dict)
        except Exception:
            return self.responder(400, {'ok': False})
        # Bold espera la respuesta en menos de 2 s: se responde ya y el pedido se procesa aparte
        self.responder(200, {'ok': True})
        Thread(target=procesar_evento, args=(evento,), daemon=True).start()

    def log_message(self, formato, *args):
        # Sin datos personales en el registro: solo método, ruta y código
        print(f'{self.address_string()} "{self.requestline}" {args[1] if len(args) > 1 else ""}', flush=True)


if __name__ == '__main__':
    PEDIDOS_DIR.mkdir(parents=True, exist_ok=True)
    bold = ('Bold: pruebas' if BOLD_PRUEBAS else 'Bold: producción') if BOLD_LLAVE_SECRETA else 'Bold: sin llaves (pagos apagados)'
    print(f'Escuchando en el puerto {PUERTO} · destino {CORREO_DESTINO} · {bold} · '
          f'{"MODO_PRUEBA (no envía correos)" if MODO_PRUEBA else f"SMTP {SMTP_HOST}:{SMTP_PUERTO}"}', flush=True)
    ThreadingHTTPServer(('0.0.0.0', PUERTO), Manejador).serve_forever()

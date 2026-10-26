"""
Prepara la página para producción.

    python construir.py            -> compila el CSS (minificado) y versiona los archivos
    python construir.py --vigilar  -> recompila el CSS cada vez que cambias index.html o src/estilos.css

Qué hace:
  1. Compila src/estilos.css con Tailwind -> public/assets/css/estilos.css (solo las clases usadas).
  2. Agrega ?v=<huella> a cada ./assets/... de las páginas (*.html) y del catálogo (assets/datos/*.js). Así el servidor puede guardar
     esos archivos en caché un año y, cuando cambies una imagen o el CSS, los navegadores
     descargan la versión nueva (la huella cambia sola).

Corre esto SIEMPRE antes de subir la carpeta public/ al servidor.
"""
import glob
import hashlib
import os
import re
import shutil
import subprocess
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
PUBLIC = os.path.join(AQUI, 'public')
# Páginas y datos (el catálogo también referencia imágenes de ./assets)
PAGINAS = sorted(glob.glob(os.path.join(PUBLIC, '*.html')) + glob.glob(os.path.join(PUBLIC, 'assets', 'datos', '*.js')))
CSS_SALIDA = os.path.join(PUBLIC, 'assets', 'css', 'estilos.css')


def tailwind():
    candidatos = [
        os.environ.get('TAILWIND'),
        os.path.join(AQUI, '..', 'herramientas', 'tailwindcss.exe'),
        os.path.join(AQUI, '..', 'herramientas', 'tailwindcss'),
        shutil.which('tailwindcss'),
    ]
    for c in candidatos:
        if c and os.path.isfile(c):
            return os.path.abspath(c)
    sys.exit('No encontré Tailwind. Descarga "tailwindcss-windows-x64.exe" (v3.4.17) de\n'
             'https://github.com/tailwindlabs/tailwindcss/releases y guárdalo como herramientas/tailwindcss.exe')


def compilar_css(vigilar=False):
    os.makedirs(os.path.dirname(CSS_SALIDA), exist_ok=True)
    cmd = [tailwind(), '-c', 'tailwind.config.js', '-i', os.path.join('src', 'estilos.css'),
           '-o', os.path.relpath(CSS_SALIDA, AQUI)]
    cmd.append('--watch' if vigilar else '--minify')
    subprocess.run(cmd, cwd=AQUI, check=True)


def versionar():
    huellas = {}
    total = 0
    print()
    for pagina in PAGINAS:
        nombre = os.path.basename(pagina)
        html = open(pagina, encoding='utf-8').read()

        def poner_version(m):
            ruta = m.group(1)
            archivo = os.path.join(PUBLIC, ruta.lstrip('./').replace('/', os.sep))
            if not os.path.isfile(archivo):
                sys.exit(f'ERROR: {nombre} usa {ruta} pero el archivo no existe.')
            if ruta not in huellas:
                huellas[ruta] = hashlib.sha256(open(archivo, 'rb').read()).hexdigest()[:10]
            return f'{ruta}?v={huellas[ruta]}'

        # ./assets/... (atributos src, href, srcset) y url(/assets/...) en estilos en línea.
        # Las variables CSS con url() deben usar /assets (desde la raíz): si no, el navegador las
        # resuelve relativas a assets/css/estilos.css y no las encuentra.
        nuevo = re.sub(r'(?<![\w.])(\.?/assets/[^"\'\s)?,]+)(?:\?v=[0-9a-f]+)?', poner_version, html)
        if nuevo != html:
            open(pagina, 'w', encoding='utf-8', newline='').write(nuevo)
        total += os.path.getsize(pagina)
        print(f'  {nombre:44} {os.path.getsize(pagina) / 1024:7.1f} KB')
    for ruta in sorted(set(r.lstrip('./') for r in huellas)):
        tam = os.path.getsize(os.path.join(PUBLIC, ruta))
        total += tam
        print(f'  {ruta[7:]:44} {tam / 1024:7.1f} KB')
    print(f'  {"TOTAL archivos propios":44} {total / 1024:7.1f} KB\n')


if __name__ == '__main__':
    if '--vigilar' in sys.argv:
        compilar_css(vigilar=True)
    else:
        compilar_css()
        versionar()
        print('Listo. Sube el contenido de public/ al servidor (ver ../despliegue/publicar.sh).')

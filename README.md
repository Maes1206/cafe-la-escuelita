# ☕ Café La Escuelita

Sitio web oficial de **Café La Escuelita** — café de origen panameño, cultivado con amor en las alturas de la finca familiar.

## Estructura del proyecto

```
Cafe la Escuelita/
├── plantilla la escuelita/   # Código fuente del sitio web
│   ├── src/                  # CSS fuente (Tailwind)
│   ├── public/               # Sitio compilado listo para publicar
│   │   ├── index.html
│   │   └── assets/
│   │       ├── css/
│   │       ├── images/
│   │       └── icons/
│   ├── originales/           # Imágenes originales en alta resolución
│   ├── construir.py          # Script que compila CSS con Tailwind
│   └── tailwind.config.js    # Configuración de Tailwind CSS
├── despliegue/               # Scripts de despliegue para el servidor
│   ├── activar-sitio.sh
│   ├── cafelaescuelita.conf  # Configuración Apache/Nginx
│   └── publicar.sh
└── herramientas/             # Binarios locales (ignorados por git)
```

## Cómo construir el CSS

```bash
python "plantilla la escuelita/construir.py"
```

## Despliegue

Ver los scripts en la carpeta `despliegue/`.

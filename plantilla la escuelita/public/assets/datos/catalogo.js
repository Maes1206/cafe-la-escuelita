// Catálogo de la tienda: precios, tamaños, envío y si Bold está activo (única fuente de precios del sitio).
// Es un .js (no .json) para que también cargue al abrir las páginas directo desde el disco.
// "porConfirmar": true = precios y envío de ejemplo; publicar.sh no publica hasta cambiarlo a false.
window.CATALOGO = {
    "porConfirmar": true,
    "moneda": "COP",
    "pagos": {
        "bold": false,
        "endpoint": "/api/pedido"
    },
    "envio": {
        "costo": 12000,
        "gratisDesde": 150000
    },
    "productos": [
        {
            "id": "bourbon-rosado-250",
            "nombre": "Bourbon Rosado",
            "peso": "250 g",
            "precio": 28000,
            "nota": "Ideal para probarlo",
            "imagen": "./assets/images/empaque-frente.webp?v=e3cea6c623"
        },
        {
            "id": "bourbon-rosado-500",
            "nombre": "Bourbon Rosado",
            "peso": "500 g",
            "precio": 52000,
            "nota": "Para el mes en casa",
            "imagen": "./assets/images/empaque-frente.webp?v=e3cea6c623",
            "destacado": "Más pedido"
        },
        {
            "id": "bourbon-rosado-1000",
            "nombre": "Bourbon Rosado",
            "peso": "1 kg",
            "precio": 98000,
            "nota": "Para la familia o la oficina",
            "imagen": "./assets/images/empaque-frente.webp?v=e3cea6c623"
        }
    ]
};

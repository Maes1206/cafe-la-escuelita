/** Configuración de Tailwind (antes estaba en el <script> del CDN dentro de index.html). */
module.exports = {
    content: ['./public/**/*.html', './public/assets/js/**/*.js'],
    theme: {
        extend: {
            fontFamily: {
                display: ['Fraunces', 'Georgia', 'serif'],
                texto: ['"Instrument Sans"', 'ui-sans-serif', 'system-ui', 'sans-serif'],
            },
            colors: {
                espresso: { 950: '#120a06', 900: '#1c110b', 800: '#2a1a10' },
                oro: { 300: '#e6c78a', 400: '#d8ae5c', 500: '#c8962e' },
                crema: { 100: '#f8f3ea', 200: '#f1e8da', 300: '#e6d7bf' },
                terracota: { 500: '#c0643a', 600: '#a4502a' },
                mostaza: { 400: '#e2b04a', 500: '#d9a13a', 600: '#c68d27' },
            },
        },
    },
    plugins: [require('@tailwindcss/forms')],
};

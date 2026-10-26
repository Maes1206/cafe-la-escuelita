/*
 * Comportamientos compartidos por todas las páginas: menú en celular, empaque 3D (tocar para ver el
 * reverso) y animación de entrada de los elementos con la clase .revelar.
 */

// Menú en celular: abre y cierra con el botón ☰; se cierra al elegir una sección o con Escape
(() => {
    const boton = document.querySelector('[data-menu]');
    const menu = document.getElementById('menu-movil');
    const poner = abierto => {
        menu.hidden = !abierto;
        boton.setAttribute('aria-expanded', abierto);
        boton.setAttribute('aria-label', abierto ? 'Cerrar menú' : 'Abrir menú');
        boton.querySelector('[data-icono="abrir"]').classList.toggle('hidden', abierto);
        boton.querySelector('[data-icono="cerrar"]').classList.toggle('hidden', !abierto);
    };
    boton.addEventListener('click', () => poner(menu.hidden));
    menu.addEventListener('click', e => { if (e.target.closest('a')) poner(false); });
    document.addEventListener('keydown', e => {
        if (e.key === 'Escape' && !menu.hidden) { poner(false); boton.focus(); }
    });
})();

// Empaque 3D: tocar para ver el reverso
document.querySelectorAll('.bolsa-3d').forEach(btn => {
    btn.addEventListener('click', () => {
        btn.setAttribute('aria-pressed', btn.getAttribute('aria-pressed') !== 'true');
    });
    // Con mouse o dedo no se muestra el marco de foco, aunque luego se presione otra tecla
    // (p. ej. el atajo de captura de pantalla). Tab, Enter o Espacio lo vuelven a mostrar.
    btn.addEventListener('pointerdown', () => { btn.dataset.puntero = ''; });
    btn.addEventListener('keydown', e => {
        if (e.key === 'Tab' || e.key === 'Enter' || e.key === ' ') delete btn.dataset.puntero;
    });
    btn.addEventListener('blur', () => { delete btn.dataset.puntero; });
});

// Entrada al aparecer en pantalla: la clase .listo esconde los elementos solo si hay JS y animaciones
(() => {
    if (!('IntersectionObserver' in window) || matchMedia('(prefers-reduced-motion: reduce)').matches) return;
    const observador = new IntersectionObserver(entradas => entradas.forEach(e => {
        if (!e.isIntersecting) return;
        e.target.classList.add('visible');
        observador.unobserve(e.target);
    }), { threshold: 0.25 });
    document.querySelectorAll('.revelar').forEach(el => {
        el.classList.add('listo');
        observador.observe(el);
    });
})();

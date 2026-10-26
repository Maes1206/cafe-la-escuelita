/*
 * Tienda de Café la Escuelita: tarjetas de producto (tienda.html), carrito deslizable y checkout (todas las páginas).
 * Precios, envío y si Bold está activo vienen de assets/datos/catalogo.js (window.CATALOGO), que se carga antes.
 * El carrito se guarda en el navegador, así que es el mismo en todas las páginas.
 */

// Panel del carrito y checkout (se agrega al final de <body>)
const PANEL = `
<dialog id="carrito" aria-labelledby="carrito-titulo"
    class="carrito m-0 ml-auto h-dvh max-h-dvh w-full max-w-md overflow-hidden bg-white p-0 font-texto text-espresso-900 shadow-2xl">
    <div class="flex h-full flex-col">
        <header class="flex items-center justify-between gap-4 border-b border-espresso-900/10 px-6 py-4">
            <button type="button" data-volver hidden
                class="-ml-2 grid h-10 w-10 place-items-center rounded-full transition-colors hover:bg-crema-100" aria-label="Volver al carrito">
                <svg class="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M15 6l-6 6 6 6" /></svg>
            </button>
            <div class="min-w-0 flex-1">
                <h2 id="carrito-titulo" class="font-display text-2xl" data-titulo>Tu carrito</h2>
                <ol class="mt-1 flex items-center gap-2 text-[0.7rem] font-semibold uppercase tracking-[0.18em] text-espresso-800/40" aria-label="Pasos de la compra">
                    <li data-paso="carrito">Carrito</li><li aria-hidden="true">›</li>
                    <li data-paso="checkout">Datos y pago</li><li aria-hidden="true">›</li>
                    <li data-paso="listo">Listo</li>
                </ol>
            </div>
            <button type="button" data-cerrar autofocus
                class="grid h-10 w-10 place-items-center rounded-full transition-colors hover:bg-crema-100" aria-label="Cerrar carrito">
                <svg class="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><path d="M6 6l12 12M18 6 6 18" /></svg>
            </button>
        </header>

        <!-- Vista 1: carrito -->
        <div data-vista="carrito" class="vista flex min-h-0 flex-1 flex-col">
            <div class="min-h-0 flex-1 overflow-y-auto px-6">
                <div data-vacio hidden class="flex h-full flex-col items-center justify-center py-16 text-center">
                    <span class="grid h-16 w-16 place-items-center rounded-full bg-crema-100 text-oro-500"><svg class="h-8 w-8" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M5 8h14l-1.2 11.1a2 2 0 0 1-2 1.9H8.2a2 2 0 0 1-2-1.9z" /><path d="M9 8V6.5a3 3 0 0 1 6 0V8" /></svg></span>
                    <p class="mt-5 font-display text-xl">Tu carrito está vacío</p>
                    <p class="mt-2 text-sm text-espresso-800/60">Elige tu presentación de Bourbon Rosado.</p>
                    <a href="#comprar" data-cerrar class="mt-6 rounded-lg border border-espresso-900/20 px-5 py-2.5 text-sm font-semibold transition hover:border-espresso-900/40">Ver presentaciones</a>
                </div>
                <ul data-lineas class="divide-y divide-espresso-900/10"></ul>
            </div>
            <footer data-pie class="border-t border-espresso-900/10 bg-crema-100/50 px-6 py-5">
                <div data-barra-envio class="mb-4">
                    <p class="text-xs text-espresso-800/70" data-barra-texto></p>
                    <div class="mt-2 h-1.5 overflow-hidden rounded-full bg-espresso-900/10"><div data-barra class="barra-envio h-full rounded-full bg-mostaza-500"></div></div>
                </div>
                <dl class="space-y-1.5 text-sm">
                    <div class="flex justify-between"><dt class="text-espresso-800/70">Subtotal</dt><dd data-subtotal class="font-medium"></dd></div>
                    <div class="flex justify-between"><dt class="text-espresso-800/70">Envío</dt><dd data-envio class="font-medium"></dd></div>
                    <div class="flex justify-between border-t border-espresso-900/10 pt-2.5 text-base"><dt class="font-semibold">Total</dt><dd data-total class="font-display text-xl"></dd></div>
                </dl>
                <button type="button" data-ir-checkout class="inline-flex w-full items-center justify-center gap-2.5 rounded-lg bg-mostaza-500 py-3.5 text-sm font-semibold text-espresso-900 transition hover:bg-mostaza-400 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-espresso-900 focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 mt-5">Continuar con el pago</button>
            </footer>
        </div>

        <!-- Vista 2: datos de envío y pago -->
        <form data-vista="checkout" id="form-checkout" hidden class="vista flex min-h-0 flex-1 flex-col" novalidate>
            <div class="min-h-0 flex-1 space-y-7 overflow-y-auto px-6 py-6">
                <fieldset class="space-y-4">
                    <legend class="text-[0.7rem] font-semibold uppercase tracking-[0.25em] text-terracota-600">Contacto</legend>
                    <div><label for="ck-nombre" class="mb-1.5 block text-sm text-espresso-800/70">Nombre completo</label>
                        <input id="ck-nombre" name="nombre" required autocomplete="name" class="w-full rounded-lg border-espresso-900/15 px-3.5 py-3 text-sm text-espresso-900 shadow-sm transition-colors placeholder:text-espresso-800/35 focus:border-mostaza-500 focus:ring-2 focus:ring-mostaza-500/25" /></div>
                    <div class="grid gap-4 sm:grid-cols-2">
                        <div><label for="ck-correo" class="mb-1.5 block text-sm text-espresso-800/70">Correo</label>
                            <input id="ck-correo" name="correo" type="email" required autocomplete="email" class="w-full rounded-lg border-espresso-900/15 px-3.5 py-3 text-sm text-espresso-900 shadow-sm transition-colors placeholder:text-espresso-800/35 focus:border-mostaza-500 focus:ring-2 focus:ring-mostaza-500/25" /></div>
                        <div><label for="ck-celular" class="mb-1.5 block text-sm text-espresso-800/70">Celular</label>
                            <input id="ck-celular" name="celular" type="tel" required inputmode="tel" autocomplete="tel-national" placeholder="300 123 4567" class="w-full rounded-lg border-espresso-900/15 px-3.5 py-3 text-sm text-espresso-900 shadow-sm transition-colors placeholder:text-espresso-800/35 focus:border-mostaza-500 focus:ring-2 focus:ring-mostaza-500/25" /></div>
                    </div>
                    <div class="grid grid-cols-[7rem_1fr] gap-4">
                        <div><label for="ck-tipo-doc" class="mb-1.5 block text-sm text-espresso-800/70">Documento</label>
                            <select id="ck-tipo-doc" name="tipoDocumento" class="w-full rounded-lg border-espresso-900/15 px-3.5 py-3 text-sm text-espresso-900 shadow-sm transition-colors placeholder:text-espresso-800/35 focus:border-mostaza-500 focus:ring-2 focus:ring-mostaza-500/25 cursor-pointer">
                                <option value="CC">CC</option><option value="CE">CE</option><option value="NIT">NIT</option><option value="PP">Pasaporte</option>
                            </select></div>
                        <div><label for="ck-documento" class="mb-1.5 block text-sm text-espresso-800/70">Número</label>
                            <input id="ck-documento" name="documento" required inputmode="numeric" class="w-full rounded-lg border-espresso-900/15 px-3.5 py-3 text-sm text-espresso-900 shadow-sm transition-colors placeholder:text-espresso-800/35 focus:border-mostaza-500 focus:ring-2 focus:ring-mostaza-500/25" /></div>
                    </div>
                </fieldset>

                <fieldset class="space-y-4">
                    <legend class="text-[0.7rem] font-semibold uppercase tracking-[0.25em] text-terracota-600">Envío</legend>
                    <div class="grid gap-4 sm:grid-cols-2">
                        <div><label for="ck-departamento" class="mb-1.5 block text-sm text-espresso-800/70">Departamento</label>
                            <select id="ck-departamento" name="departamento" required class="w-full rounded-lg border-espresso-900/15 px-3.5 py-3 text-sm text-espresso-900 shadow-sm transition-colors placeholder:text-espresso-800/35 focus:border-mostaza-500 focus:ring-2 focus:ring-mostaza-500/25 cursor-pointer">
                            <option value="">Elige…</option>
                            <option>Amazonas</option>
                            <option>Antioquia</option>
                            <option>Arauca</option>
                            <option>Atlántico</option>
                            <option>Bogotá D.C.</option>
                            <option>Bolívar</option>
                            <option>Boyacá</option>
                            <option>Caldas</option>
                            <option>Caquetá</option>
                            <option>Casanare</option>
                            <option>Cauca</option>
                            <option>Cesar</option>
                            <option>Chocó</option>
                            <option>Córdoba</option>
                            <option>Cundinamarca</option>
                            <option>Guainía</option>
                            <option>Guaviare</option>
                            <option>Huila</option>
                            <option>La Guajira</option>
                            <option>Magdalena</option>
                            <option>Meta</option>
                            <option>Nariño</option>
                            <option>Norte de Santander</option>
                            <option>Putumayo</option>
                            <option>Quindío</option>
                            <option>Risaralda</option>
                            <option>San Andrés y Providencia</option>
                            <option>Santander</option>
                            <option>Sucre</option>
                            <option>Tolima</option>
                            <option>Valle del Cauca</option>
                            <option>Vaupés</option>
                            <option>Vichada</option>
                            </select></div>
                        <div><label for="ck-ciudad" class="mb-1.5 block text-sm text-espresso-800/70">Ciudad o municipio</label>
                            <input id="ck-ciudad" name="ciudad" required autocomplete="address-level2" class="w-full rounded-lg border-espresso-900/15 px-3.5 py-3 text-sm text-espresso-900 shadow-sm transition-colors placeholder:text-espresso-800/35 focus:border-mostaza-500 focus:ring-2 focus:ring-mostaza-500/25" /></div>
                    </div>
                    <div><label for="ck-direccion" class="mb-1.5 block text-sm text-espresso-800/70">Dirección</label>
                        <input id="ck-direccion" name="direccion" required autocomplete="street-address" placeholder="Calle 10 # 5-20, apto 301" class="w-full rounded-lg border-espresso-900/15 px-3.5 py-3 text-sm text-espresso-900 shadow-sm transition-colors placeholder:text-espresso-800/35 focus:border-mostaza-500 focus:ring-2 focus:ring-mostaza-500/25" /></div>
                    <div><label for="ck-indicaciones" class="mb-1.5 block text-sm text-espresso-800/70">Barrio o indicaciones <span class="text-espresso-800/40">(opcional)</span></label>
                        <input id="ck-indicaciones" name="indicaciones" class="w-full rounded-lg border-espresso-900/15 px-3.5 py-3 text-sm text-espresso-900 shadow-sm transition-colors placeholder:text-espresso-800/35 focus:border-mostaza-500 focus:ring-2 focus:ring-mostaza-500/25" /></div>
                    <div><label for="ck-notas" class="mb-1.5 block text-sm text-espresso-800/70">Notas del pedido <span class="text-espresso-800/40">(opcional)</span></label>
                        <textarea id="ck-notas" name="notas" rows="2" placeholder="Por ejemplo: molienda para prensa francesa" class="w-full rounded-lg border-espresso-900/15 px-3.5 py-3 text-sm text-espresso-900 shadow-sm transition-colors placeholder:text-espresso-800/35 focus:border-mostaza-500 focus:ring-2 focus:ring-mostaza-500/25 resize-y"></textarea></div>
                </fieldset>

                <div class="rounded-xl bg-crema-100/60 p-4">
                    <p class="text-[0.7rem] font-semibold uppercase tracking-[0.25em] text-terracota-600">Resumen</p>
                    <ul data-resumen class="mt-3 space-y-1.5 text-sm"></ul>
                    <dl class="mt-3 space-y-1.5 border-t border-espresso-900/10 pt-3 text-sm">
                        <div class="flex justify-between"><dt class="text-espresso-800/70">Subtotal</dt><dd data-subtotal></dd></div>
                        <div class="flex justify-between"><dt class="text-espresso-800/70">Envío</dt><dd data-envio></dd></div>
                        <div class="flex justify-between text-base font-semibold"><dt>Total</dt><dd data-total></dd></div>
                    </dl>
                </div>

                <div class="flex items-start gap-3">
                    <input id="ck-datos" name="datos" type="checkbox" required
                        class="mt-0.5 h-5 w-5 cursor-pointer rounded-[5px] border-espresso-900/25 text-mostaza-500 focus:ring-mostaza-500/40" />
                    <label for="ck-datos" class="cursor-pointer text-sm leading-relaxed text-espresso-800/70">
                        Autorizo el uso de mis datos para procesar y enviar mi pedido, según la
                        <a href="politica-de-privacidad.html" target="_blank" class="underline underline-offset-2 hover:text-terracota-600">política de tratamiento de datos</a>.
                    </label>
                </div>
            </div>
            <footer class="border-t border-espresso-900/10 px-6 py-5">
                <p data-error role="alert" hidden class="mb-3 rounded-lg bg-red-50 px-4 py-2.5 text-sm text-red-800"></p>
                <button type="submit" data-pagar class="inline-flex w-full items-center justify-center gap-2.5 rounded-lg bg-mostaza-500 py-3.5 text-sm font-semibold text-espresso-900 transition hover:bg-mostaza-400 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-espresso-900 focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50"></button>
                <p data-ayuda-pago class="mt-3 text-center text-xs text-espresso-800/55"></p>
            </footer>
        </form>

        <!-- Vista 3: pedido enviado -->
        <div data-vista="listo" hidden class="vista flex flex-1 flex-col items-center justify-center px-8 text-center">
            <span class="grid h-16 w-16 place-items-center rounded-full bg-emerald-50 text-emerald-700">
                <svg class="h-8 w-8" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M5 12.5l4.5 4.5L19 7.5" /></svg>
            </span>
            <p class="mt-6 font-display text-2xl">¡Pedido <span data-pedido-id></span> listo!</p>
            <p class="mt-3 text-sm leading-relaxed text-espresso-800/70">Te abrimos WhatsApp con el detalle. Envíalo y te
                confirmamos el envío y la forma de pago.</p>
            <a data-reabrir target="_blank" rel="noopener" class="mt-6 text-sm font-semibold text-terracota-600 underline underline-offset-4">¿No se abrió WhatsApp? Toca aquí</a>
            <button type="button" data-cerrar class="mt-8 rounded-lg border border-espresso-900/20 px-5 py-2.5 text-sm font-semibold transition hover:border-espresso-900/40">Seguir en la página</button>
        </div>
    </div>
</dialog>
`;

// Tienda: tarjetas, carrito (se guarda en el navegador) y checkout. Si pagos.bold es true se paga con Bold
// (ver pagarConBold); si no, el pedido se confirma por WhatsApp con todo el detalle.
(() => {
    const datos = window.CATALOGO;
    if (!datos) {
        document.querySelectorAll('[data-abrir-carrito]').forEach(b => { b.hidden = true; });
        return;
    }
    document.body.insertAdjacentHTML('beforeend', PANEL);
    const productos = new Map(datos.productos.map(p => [p.id, p]));
    const formato = new Intl.NumberFormat('es-CO', { style: 'currency', currency: datos.moneda, maximumFractionDigits: 0 });
    const dinero = n => formato.format(n);
    const MOLIENDAS = { grano: 'En grano', molido: 'Molido' };
    const CLAVE = 'cafe-la-escuelita:carrito';
    const sinMovimiento = matchMedia('(prefers-reduced-motion: reduce)').matches;

    let carrito = [];
    try { carrito = JSON.parse(localStorage.getItem(CLAVE)) || []; } catch { carrito = []; }
    carrito = carrito.filter(l => productos.has(l.id) && MOLIENDAS[l.molienda] && l.cantidad > 0);
    const guardar = () => { try { localStorage.setItem(CLAVE, JSON.stringify(carrito)); } catch { /* sin almacenamiento */ } };

    const totales = () => {
        const subtotal = carrito.reduce((s, l) => s + productos.get(l.id).precio * l.cantidad, 0);
        const envio = subtotal === 0 || subtotal >= datos.envio.gratisDesde ? 0 : datos.envio.costo;
        return { subtotal, envio, total: subtotal + envio, unidades: carrito.reduce((s, l) => s + l.cantidad, 0) };
    };

    // ----- Tarjetas de producto -----
    // Las tarjetas solo existen en tienda.html; en las demás páginas se arman en un div suelto
    const lista = document.getElementById('productos') || document.createElement('div');
    lista.innerHTML = datos.productos.map(p => `
        <article class="producto group flex flex-col overflow-hidden rounded-2xl border border-espresso-900/10 bg-white transition duration-300 hover:-translate-y-1 hover:shadow-[0_18px_40px_-18px_rgba(28,17,11,0.35)]" data-producto="${p.id}">
            <div class="relative aspect-[4/3] bg-crema-100">
                <img src="${p.imagen}" alt="Bolsa de Café la Escuelita ${p.nombre} de ${p.peso}" loading="lazy"
                    class="absolute inset-0 m-auto h-[82%] w-auto object-contain drop-shadow-[0_12px_14px_rgba(28,17,11,0.18)] transition duration-500 group-hover:scale-105" />
                <span class="absolute left-4 top-4 rounded-full bg-white px-3 py-1 text-xs font-bold text-espresso-900 shadow-sm">${p.peso}</span>
                ${p.destacado ? `<span class="absolute right-4 top-4 rounded-full bg-terracota-600 px-3 py-1 text-[0.65rem] font-bold uppercase tracking-[0.12em] text-white">${p.destacado}</span>` : ''}
            </div>
            <div class="flex flex-1 flex-col p-6">
                <h3 class="font-display text-xl text-espresso-900">${p.nombre} · ${p.peso}</h3>
                <p class="mt-1 text-sm text-espresso-800/60">${p.nota}</p>
                <p class="mt-4 font-display text-2xl text-espresso-900">${dinero(p.precio)}</p>
                <fieldset class="mt-5">
                    <legend class="sr-only">Molienda</legend>
                    <div class="grid grid-cols-2 gap-2 rounded-lg bg-crema-100 p-1">
                        ${Object.entries(MOLIENDAS).map(([v, t], i) => `
                        <label class="molienda cursor-pointer">
                            <input type="radio" name="molienda-${p.id}" value="${v}" ${i === 0 ? 'checked' : ''} class="peer sr-only" />
                            <span class="block rounded-md py-2 text-center text-sm font-medium text-espresso-800/70 transition peer-checked:bg-white peer-checked:text-espresso-900 peer-checked:shadow-sm peer-focus-visible:ring-2 peer-focus-visible:ring-mostaza-500">${t}</span>
                        </label>`).join('')}
                    </div>
                </fieldset>
                <div class="mt-auto flex items-center gap-3 pt-5">
                    <div class="flex items-center rounded-lg border border-espresso-900/15">
                        <button type="button" data-paso-cantidad="-1" class="grid h-11 w-10 place-items-center text-lg text-espresso-800/70 transition hover:text-espresso-900" aria-label="Quitar una">−</button>
                        <span data-cantidad-tarjeta class="w-6 text-center text-sm font-semibold" aria-live="polite">1</span>
                        <button type="button" data-paso-cantidad="1" class="grid h-11 w-10 place-items-center text-lg text-espresso-800/70 transition hover:text-espresso-900" aria-label="Agregar una">+</button>
                    </div>
                    <button type="button" data-agregar class="flex-1 rounded-lg bg-espresso-900 px-4 py-3 text-sm font-semibold text-white transition hover:bg-espresso-800 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-mostaza-500 focus-visible:ring-offset-2">Agregar al carrito</button>
                </div>
            </div>
        </article>`).join('');

    lista.addEventListener('click', e => {
        const tarjeta = e.target.closest('[data-producto]');
        if (!tarjeta) return;
        const contador = tarjeta.querySelector('[data-cantidad-tarjeta]');
        const paso = e.target.closest('[data-paso-cantidad]');
        if (paso) {
            contador.textContent = Math.min(20, Math.max(1, +contador.textContent + +paso.dataset.pasoCantidad));
            return;
        }
        if (!e.target.closest('[data-agregar]')) return;
        const id = tarjeta.dataset.producto;
        const molienda = tarjeta.querySelector('input[type=radio]:checked').value;
        const linea = carrito.find(l => l.id === id && l.molienda === molienda);
        const cantidad = +contador.textContent;
        if (linea) linea.cantidad = Math.min(20, linea.cantidad + cantidad);
        else carrito.push({ id, molienda, cantidad });
        contador.textContent = 1;
        guardar();
        pintar();
        abrir();
    });

    const textoEnvio = document.querySelector('[data-envio-texto]') || {};
    textoEnvio.textContent = `Envío a toda Colombia por ${dinero(datos.envio.costo)} · Gratis en pedidos desde ${dinero(datos.envio.gratisDesde)}.`;

    // ----- Panel del carrito -----
    const panel = document.getElementById('carrito');
    panel.querySelector('[data-vacio] a').href = document.getElementById('productos') ? '#comprar' : 'tienda.html';
    const $ = s => panel.querySelector(s);
    const $$ = s => panel.querySelectorAll(s);
    const contadores = document.querySelectorAll('[data-contador]');
    const TITULOS = { carrito: 'Tu carrito', checkout: 'Datos y pago', listo: 'Pedido listo' };

    const mostrar = vista => {
        $$('[data-vista]').forEach(v => { v.hidden = v.dataset.vista !== vista; });
        $('[data-titulo]').textContent = TITULOS[vista];
        $('[data-volver]').hidden = vista !== 'checkout';
        $$('[data-paso]').forEach(p => p.classList.toggle('text-terracota-600', p.dataset.paso === vista));
        if (vista === 'checkout') $('#ck-nombre').focus();
    };

    const pintar = () => {
        const t = totales();
        contadores.forEach(c => { c.hidden = t.unidades === 0; c.textContent = t.unidades; });
        $('[data-vacio]').hidden = carrito.length > 0;
        $('[data-pie]').hidden = carrito.length === 0;
        $('[data-lineas]').innerHTML = carrito.map((l, i) => {
            const p = productos.get(l.id);
            return `
            <li class="flex gap-4 py-5">
                <div class="grid h-24 w-20 shrink-0 place-items-center rounded-xl bg-crema-100"><img src="${p.imagen}" alt="" class="h-[82%] w-auto object-contain" /></div>
                <div class="flex min-w-0 flex-1 flex-col">
                    <div class="flex items-start justify-between gap-3">
                        <p class="font-display text-base leading-snug">${p.nombre} · ${p.peso}</p>
                        <p class="shrink-0 text-sm font-semibold">${dinero(p.precio * l.cantidad)}</p>
                    </div>
                    <p class="mt-0.5 text-xs text-espresso-800/60">${MOLIENDAS[l.molienda]} · ${dinero(p.precio)} c/u</p>
                    <div class="mt-auto flex items-center justify-between pt-3">
                        <div class="flex items-center rounded-lg border border-espresso-900/15">
                            <button type="button" data-linea="${i}" data-cambio="-1" class="grid h-8 w-8 place-items-center text-espresso-800/70 hover:text-espresso-900" aria-label="Quitar una">−</button>
                            <span class="w-6 text-center text-sm font-semibold">${l.cantidad}</span>
                            <button type="button" data-linea="${i}" data-cambio="1" class="grid h-8 w-8 place-items-center text-espresso-800/70 hover:text-espresso-900" aria-label="Agregar una">+</button>
                        </div>
                        <button type="button" data-linea="${i}" data-quitar class="text-xs text-espresso-800/55 underline underline-offset-2 hover:text-terracota-600">Quitar</button>
                    </div>
                </div>
            </li>`;
        }).join('');
        $$('[data-subtotal]').forEach(e => { e.textContent = dinero(t.subtotal); });
        $$('[data-envio]').forEach(e => { e.textContent = t.envio ? dinero(t.envio) : 'Gratis'; });
        $$('[data-total]').forEach(e => { e.textContent = dinero(t.total); });
        const falta = datos.envio.gratisDesde - t.subtotal;
        $('[data-barra-texto]').innerHTML = falta > 0
            ? `Te faltan <strong class="text-espresso-900">${dinero(falta)}</strong> para el envío gratis`
            : '<strong class="text-emerald-700">¡Tu pedido tiene envío gratis!</strong>';
        $('[data-barra]').style.width = `${Math.min(100, (t.subtotal / datos.envio.gratisDesde) * 100)}%`;
        $('[data-resumen]').innerHTML = carrito.map(l => {
            const p = productos.get(l.id);
            return `<li class="flex justify-between gap-3"><span class="text-espresso-800/80">${l.cantidad} × ${p.nombre} ${p.peso} · ${MOLIENDAS[l.molienda]}</span><span>${dinero(p.precio * l.cantidad)}</span></li>`;
        }).join('');
        $('[data-pagar]').textContent = datos.pagos.bold ? `Pagar ${dinero(t.total)} con Bold` : 'Confirmar pedido por WhatsApp';
        $('[data-ayuda-pago]').textContent = datos.pagos.bold
            ? 'Te llevamos al pago seguro de Bold: tarjeta, PSE y otros medios.'
            : 'Se abrirá WhatsApp con tu pedido. Allí te confirmamos el envío y la forma de pago.';
    };

    $('[data-lineas]').addEventListener('click', e => {
        const b = e.target.closest('[data-linea]');
        if (!b) return;
        const l = carrito[+b.dataset.linea];
        if (b.hasAttribute('data-quitar')) carrito.splice(+b.dataset.linea, 1);
        else l.cantidad = Math.min(20, l.cantidad + +b.dataset.cambio);
        carrito = carrito.filter(x => x.cantidad > 0);
        guardar();
        pintar();
    });

    // Abrir y cerrar (con animación de salida; sin ella si el dispositivo pide menos movimiento)
    const abrir = () => {
        mostrar(carrito.length || panel.dataset.ultima !== 'listo' ? 'carrito' : 'listo');
        if (!panel.open) panel.showModal();
    };
    const cerrar = () => {
        if (!panel.open || panel.classList.contains('cerrando')) return;
        if (sinMovimiento) { panel.close(); return; }
        panel.classList.add('cerrando');
        const fin = e => {
            if (e && e.target !== panel) return; // animaciones internas (cambio de vista) no cuentan
            if (!panel.classList.contains('cerrando')) return;
            panel.removeEventListener('animationend', fin);
            panel.classList.remove('cerrando');
            panel.close();
        };
        panel.addEventListener('animationend', fin);
        setTimeout(fin, 400); // por si el navegador no avisa el fin de la animación (pestaña en segundo plano)
    };
    document.querySelectorAll('[data-abrir-carrito]').forEach(b => b.addEventListener('click', abrir));
    panel.addEventListener('cancel', e => { e.preventDefault(); cerrar(); });
    panel.addEventListener('click', e => {
        if (e.target === panel || e.target.closest('[data-cerrar]')) cerrar();
    });
    $('[data-ir-checkout]').addEventListener('click', () => mostrar('checkout'));
    $('[data-volver]').addEventListener('click', () => mostrar('carrito'));

    // ----- Checkout -----
    const form = document.getElementById('form-checkout');
    const error = $('[data-error]');
    const armarPedido = () => {
        const f = form.elements;
        const t = totales();
        return {
            id: `CLE-${Date.now().toString(36).toUpperCase()}`,
            items: carrito.map(l => ({ id: l.id, molienda: l.molienda, cantidad: l.cantidad })),
            cliente: {
                nombre: f.nombre.value.trim(), correo: f.correo.value.trim(), celular: f.celular.value.trim(),
                tipoDocumento: f.tipoDocumento.value, documento: f.documento.value.trim(),
            },
            envio: {
                departamento: f.departamento.value, ciudad: f.ciudad.value.trim(), direccion: f.direccion.value.trim(),
                indicaciones: f.indicaciones.value.trim(),
            },
            notas: f.notas.value.trim(),
            totales: t, // solo informativo: el servidor recalcula con sus precios antes de cobrar
        };
    };

    const mensajeWhatsApp = pedido => {
        const c = pedido.cliente, e = pedido.envio, t = pedido.totales;
        return [
            `Hola, quiero hacer este pedido (${pedido.id}):`,
            ...carrito.map(l => {
                const p = productos.get(l.id);
                return `• ${l.cantidad} × ${p.nombre} ${p.peso} (${MOLIENDAS[l.molienda]}) — ${dinero(p.precio * l.cantidad)}`;
            }),
            '',
            `Subtotal: ${dinero(t.subtotal)}`,
            `Envío: ${t.envio ? dinero(t.envio) : 'Gratis'}`,
            `Total: ${dinero(t.total)}`,
            '',
            `Nombre: ${c.nombre}`,
            `${c.tipoDocumento}: ${c.documento}`,
            `Celular: ${c.celular}`,
            `Correo: ${c.correo}`,
            `Dirección: ${e.direccion}${e.indicaciones ? ` (${e.indicaciones})` : ''}`,
            `Ciudad: ${e.ciudad}, ${e.departamento}`,
            ...(pedido.notas ? ['', `Notas: ${pedido.notas}`] : []),
        ].join('\n');
    };

    // Bold: el servidor (datos.pagos.endpoint) recibe el pedido, recalcula el total con SUS precios y firma
    // SHA-256("{orderId}{amount}{currency}{llave secreta}"); la llave secreta nunca va en la página.
    // Respuesta esperada: { orderId, amount, currency, apiKey, integritySignature }.
    // Al integrar, confirmar con la documentación de Bold los nombres de BoldCheckout y sus opciones.
    const cargarScript = src => new Promise((ok, falla) => {
        if (document.querySelector(`script[src="${src}"]`)) return ok();
        const s = Object.assign(document.createElement('script'), { src, onload: ok, onerror: falla });
        document.head.append(s);
    });
    const pagarConBold = async pedido => {
        const r = await fetch(datos.pagos.endpoint, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
            body: JSON.stringify(pedido),
        });
        const firma = await r.json().catch(() => ({}));
        if (!r.ok || !firma.integritySignature) throw new Error(firma.error || 'No se pudo iniciar el pago.');
        await cargarScript('https://checkout.bold.co/library/boldPaymentButton.js');
        const c = pedido.cliente, e = pedido.envio;
        new window.BoldCheckout({
            ...firma,
            description: `Pedido ${firma.orderId} · Café la Escuelita`,
            redirectionUrl: `${location.origin}/?pedido=${encodeURIComponent(firma.orderId)}`,
            customerData: JSON.stringify({
                email: c.correo, fullName: c.nombre, phone: c.celular.replace(/\D/g, ''), dialCode: '+57',
                documentNumber: c.documento, documentType: c.tipoDocumento,
            }),
            billingAddress: JSON.stringify({ address: e.direccion, city: e.ciudad, state: e.departamento, country: 'CO' }),
        }).open();
    };

    form.addEventListener('submit', async e => {
        e.preventDefault();
        error.hidden = true;
        if (!carrito.length) { mostrar('carrito'); return; }
        if (!form.checkValidity()) { form.reportValidity(); return; }
        const pedido = armarPedido();
        const boton = $('[data-pagar]');

        if (datos.pagos.bold) {
            boton.disabled = true;
            boton.textContent = 'Conectando con Bold…';
            try {
                await pagarConBold(pedido);
            } catch (err) {
                error.textContent = `${err.message} Intenta de nuevo o escríbenos por WhatsApp.`;
                error.hidden = false;
            } finally {
                boton.disabled = false;
                pintar();
            }
            return;
        }

        const enlace = `https://wa.me/573157343753?text=${encodeURIComponent(mensajeWhatsApp(pedido))}`;
        window.open(enlace, '_blank', 'noopener');
        $('[data-pedido-id]').textContent = pedido.id;
        $('[data-reabrir]').href = enlace;
        carrito = [];
        guardar();
        pintar();
        form.reset();
        panel.dataset.ultima = 'listo';
        mostrar('listo');
    });

    pintar();
})();

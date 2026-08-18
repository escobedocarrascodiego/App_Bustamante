# Despliegue del Kiosko de turnos

El software corre en el **servidor** (`10.0.0.4:8052`). El kiosko (equipo táctil
21.5" con Windows 11, impresora térmica 80mm y lector QR/barras) solo abre la URL
en un navegador. **La impresión ocurre en el kiosko**, no en el servidor:
`window.print()` se ejecuta en el navegador del kiosko y manda el ticket a su
impresora local por defecto. El servidor nunca imprime.

```
Servidor 10.0.0.4:8052 (Django)  ──HTTP──►  Kiosko (navegador)  ──►  Impresora 80mm LOCAL
```

## 1. Servidor (una sola vez)

- **Escuchar en toda la red**, no solo localhost:
  - Producción (Windows): `waitress-serve --listen=0.0.0.0:8052 config.wsgi:application`
  - Prueba rápida: `python manage.py runserver 0.0.0.0:8052`
- **ALLOWED_HOSTS** ya incluye `10.0.0.4` por defecto. Si la IP del servidor es
  otra, setear la variable de entorno:
  `DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1,10.0.0.4,<otra-ip>`
- Abrir el puerto 8052 en el Firewall de Windows del servidor (entrada TCP).

## 2. Impresora térmica (en el kiosko)

1. Instalar el driver de la ticketera 80mm y dejarla como **impresora por
   defecto de Windows**.
2. En Preferencias de impresión del driver: tamaño de papel **80mm**, y activar
   el **corte automático de papel** (cut después de cada trabajo).
3. El diseño del ticket ya está pensado para 80mm (`@page { size: 80mm auto }`).

## 3. Navegador en modo kiosko (en el kiosko)

Lanzar Chrome o Edge apuntando a la URL, en pantalla completa y con impresión
silenciosa (sin diálogo de "Imprimir"):

**Chrome**
```
chrome.exe --kiosk --kiosk-printing --disable-pinch ^
  --overscroll-history-navigation=0 ^
  --app=http://10.0.0.4:8052/colas/kiosko/
```

**Edge**
```
msedge.exe --kiosk http://10.0.0.4:8052/colas/kiosko/ --edge-kiosk-type=fullscreen ^
  --kiosk-printing --no-first-run
```

- `--kiosk-printing` es la clave: hace que `window.print()` imprima **directo a
  la impresora por defecto** sin ventana de diálogo → ticket automático.
- Para quitar encabezado/URL y márgenes del ticket, el CSS ya usa `@page margin:0`.
  Si aún saliera margen, en el driver poner márgenes en 0.

## 4. Bloqueo del equipo (recomendado)

- **Assigned Access / Acceso asignado** (Win 11 Pro): crear una cuenta de kiosko
  que solo pueda abrir el navegador en modo kiosko, y arrancarlo al iniciar
  sesión. Así el vecino no puede salir del navegador ni tocar Windows.
- Autoarranque: un acceso directo con el comando de arriba en la carpeta
  `shell:startup` de esa cuenta.
- Desactivar el aviso de teclado táctil de Windows (no se necesita: el kiosko
  trae su **propio teclado en pantalla** para el nombre y keypad para el DNI).

## 5. Lector QR / código de barras

- El lector funciona como "teclado" (escribe lo que escanea + Enter). No requiere
  configuración: el kiosko ya escucha la ráfaga y llena el DNI automáticamente.
- Uso: escanear el **código de barras de la BustaCard** (codifica el DNI) o un
  DNI con código de barras → identifica al contribuyente y autocompleta su nombre.

## 6. Prueba rápida antes de la impresora real

- Desde cualquier PC de la red: abrir `http://10.0.0.4:8052/colas/kiosko/`.
- Sacar un turno; al confirmarse debe abrirse el diálogo de impresión (o imprimir
  solo si el navegador se lanzó con `--kiosk-printing`).
- Para validar el diseño del ticket sin ticketera: elegir "Guardar como PDF" en
  el diálogo y revisar que entre en 80mm.

# App Bustamante — Municipalidad Distrital JLBR

App ciudadana de la **Municipalidad Distrital de José Luis Bustamante y Rivero**
(Arequipa, Perú). Permite consultar deudas tributarias, iniciar trámites contra
Mesa de Partes Virtual (SIAP), emitir tarjeta ciudadana digital con beneficios
y mantener al vecino informado.

Incluye además tres módulos **web internos** (server-rendered, sin app móvil):
**gestor de colas/turnos** (kiosko táctil, ventanillero y TV), **emisión de
BustaCard en ventanilla** y **chatbot de consultas frecuentes**.

> **Stack**: Django 5 + DRF + SimpleJWT (backend) · React Native + Expo Router
> + TypeScript (mobile) · SQL Server multi-BD para integración con SIAP.

---

## Componentes

| Carpeta | Stack | Descripción |
| --- | --- | --- |
| [`backend/`](backend) | Django 5 + DRF + SimpleJWT | API REST que expone los recursos municipales y proxy SIAP |
| [`busta-app/`](busta-app) | React Native (Expo SDK 54) + TypeScript | App móvil ciudadana (Android / iOS / Web) |

---

## Requisitos previos

### Backend
- **Python 3.11+** ([python.org](https://www.python.org/downloads/))
- **Microsoft ODBC Driver for SQL Server** (17 ó 18) — para conectarse a SIAP.
  Descargar de [docs.microsoft.com](https://learn.microsoft.com/sql/connect/odbc/download-odbc-driver-for-sql-server).
- Acceso de red a los servidores SIAP de la muni (solo dentro de la red municipal)
  o instancias locales de SQL Server con las tres bases.

### Frontend
- **Node.js 20+** ([nodejs.org](https://nodejs.org/))
- **Expo Go** en el celular (Android/iOS) o emulador.
- (Opcional) **Android Studio** si querés correr en emulador local.

---

## Arquitectura de datos

```
┌────────────────────┐         ┌────────────────────┐
│   Mobile App       │  REST   │   Django Backend   │
│  (busta-app/)      │ ─────▶  │  (backend/)        │
│  Expo + JWT        │         │  3 routers JWT     │
└────────────────────┘         └─────────┬──────────┘
                                          │
                  ┌───────────────────────┼────────────────────────┐
                  ▼                       ▼                        ▼
        ┌──────────────────┐   ┌──────────────────┐    ┌──────────────────┐
        │  default         │   │  muni_db         │    │  tramites_db     │
        │  dbbusta_app     │   │  MuniJLByR       │    │  dbControl       │
        │  R/W             │   │  SOLO LECTURA    │    │  R/W parcial *   │
        │  Ciudadanos,     │   │  CONTRIBUYENTES, │    │  IngresosExt,    │
        │  Tarjetas,       │   │  IMPPREANU,      │    │  Propietarios,   │
        │  Notif, etc.     │   │  CTACTE, etc.    │    │  Solicitudes…    │
        └──────────────────┘   └──────────────────┘    └──────────────────┘
```

\* `tramites_db` es solo-lectura excepto para `IngresosExternos` (registro de
trámites desde el app) donde se escribe via raw SQL bypaseando el router.

El `MultiDBRouter` en `backend/config/db_router.py` enruta cada modelo a su
base según el `app_label` (apps `externos_muni` → `muni_db`, `externos_tramites`
→ `tramites_db`, resto → `default`).

---

## Módulos web internos

Además de la API del app móvil, el backend sirve pantallas HTML propias
(Django templates) para uso dentro de la municipalidad.

### Gestor de colas / turnos (`/colas/`)

Sistema de turnos para las ventanillas de Rentas. Tres pantallas:

| Pantalla | Ruta | Quién la usa |
| --- | --- | --- |
| **Kiosko** | `/colas/kiosko/` | El vecino: saca su turno (táctil, autoservicio) |
| **Ventanillero** | `/colas/ventanilla/` | El operador: llamar, atender, derivar (requiere staff) |
| **TV** | `/colas/tv/` | Pantalla de sala: "Llamando ahora" + siguientes turnos |

Diseño clave:
- El **estado de la ventanilla cambia solo por eventos** del ventanillero
  (llamar / iniciar / finalizar / pausar), nunca por tiempo. Los timestamps se
  guardan únicamente para métricas.
- **Posición justa en la fila**: las reservas desde el app entran a la cola al
  hacer *check-in* ("Ya llegué"), no al reservar — así no le pasan por encima a
  quien ya estaba esperando (`en_cola_desde`).
- Tiempo real por **polling** (2.5 s TV/ventanillero, 4 s app), no WebSockets.
- La TV **anuncia por voz** el turno llamado (dos veces, con cola de anuncios
  para que no se crucen si dos ventanillas llaman a la vez).

El kiosko está pensado para un **equipo táctil de 21.5" sin teclado**, con
impresora térmica de 80 mm y lector QR/código de barras:
- Teclado **numérico y QWERTY en pantalla** (no depende de teclado físico).
- **Ticket térmico automático**: al generar el turno se imprime solo, sin
  diálogo (requiere lanzar el navegador con `--kiosk-printing`).
- El **lector escanea el DNI o la BustaCard** y autocompleta el nombre.

> Puesta en marcha del equipo kiosko (impresora, flags del navegador, arranque
> automático): ver [`backend/apps/colas/DESPLIEGUE_KIOSKO.md`](backend/apps/colas/DESPLIEGUE_KIOSKO.md)
> y el lanzador [`Kiosko_Turnos.bat`](backend/apps/colas/Kiosko_Turnos.bat).

### BustaCard en ventanilla (`/genera_bustacard/`)

Para vecinos que no usan el app. Personal de ventanilla busca al contribuyente
(DNI, nombre o código), el sistema **verifica que no tenga deuda** y genera la
tarjeta imprimible (HTML o PDF) con código de barras Code 128. Lleva historial
de emisiones (`BustaCardVentanilla`), unificado con las emitidas por el app.

> La BustaCard **vence el 31 de diciembre del año de emisión** (certifica estar
> al día en el ejercicio), sin importar el día en que se emitió. Al vencer, el
> app vuelve a mostrar la deuda del nuevo año y permite **renovarla** cuando el
> contribuyente esté al día.

### Chatbot (`/api/chatbot/`)

Responde consultas frecuentes por **menú de gerencias → preguntas**, o por texto
libre usando un **matcher por scoring de tokens** (normaliza tildes, quita
stop-words en español y puntúa coincidencias de palabras clave).

---

## Setup local desde cero

### 1. Clonar el repo

```bash
git clone https://github.com/DiegoEscobedo17/App_Bustamante.git
cd App_Bustamante
```

### 2. Backend Django

#### 2.1 Crear entorno virtual + instalar dependencias

**Windows (PowerShell)**:
```powershell
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

**Windows (cmd)**:
```cmd
cd backend
python -m venv venv
venv\Scripts\activate.bat
pip install -r requirements.txt
```

**Linux/Mac**:
```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

#### 2.2 Configurar variables de entorno

Copia `.env.example` → `.env` y completa los valores:

```bash
# Windows
copy .env.example .env
# Linux/Mac
cp .env.example .env
```

Edita `backend/.env`:

```env
DJANGO_SECRET_KEY=genera-una-clave-aleatoria-larga
DJANGO_DEBUG=True
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1,10.0.2.2

# Driver ODBC (ver "Requisitos previos")
MSSQL_DRIVER=ODBC Driver 17 for SQL Server
MSSQL_USER=tu_usuario_sqlserver
MSSQL_PASSWORD=tu_password_sqlserver
MSSQL_PORT=1433

# Hosts SIAP (consultar al área de TI de la municipalidad)
DB_DEFAULT_HOST=127.0.0.1
DB_DEFAULT_NAME=dbbusta_app
DB_MUNI_HOST=127.0.0.1
DB_MUNI_NAME=MuniJLByR
DB_TRAMITES_HOST=127.0.0.1
DB_TRAMITES_NAME=dbControl
```

> Generar `DJANGO_SECRET_KEY` rápida:
> `python -c "import secrets; print(secrets.token_urlsafe(50))"`

#### 2.3 Crear la base `dbbusta_app` en SQL Server

Solo la BD propia (`default`) necesita ser creada — las otras dos (`MuniJLByR`,
`dbControl`) las administra SIAP. Conectado al SQL Server con SSMS o `sqlcmd`:

```sql
CREATE DATABASE dbbusta_app;
```

#### 2.4 Migrar Django (solo la app `default`)

```bash
python manage.py makemigrations ciudadanos
python manage.py makemigrations deudas tramites tarjetas catalogos chatbot colas
python manage.py migrate
```

> La app `colas` trae un seed inicial en sus migraciones: un servicio
> "Atención general" y las ventanillas 1 a 7. Los demás servicios (
> Fraccionamiento, Licencias, etc.) y qué servicios atiende cada ventanilla se
> configuran desde el **admin de Django**.

> **Importante**: `ciudadanos` migra primero porque define el `AUTH_USER_MODEL`
> del que dependen las demás apps.

El router `MultiDBRouter` bloquea automáticamente migraciones contra `muni_db`
y `tramites_db` (son SIAP, no se tocan).

#### 2.5 (Opcional) Datos demo

```bash
python manage.py seed_demo        # ciudadano demo + admin
python manage.py seed_contactos   # contactos municipales reales
```

Credenciales demo:
- Ciudadano: DNI `12345678` / contraseña `demo1234`
- Admin Django: DNI `00000000` / contraseña `admin1234` (acceder en `/admin/`)

#### 2.6 Levantar el servidor

```bash
python manage.py runserver 0.0.0.0:8000
```

API disponible en `http://localhost:8000/api/v1/`.
Admin en `http://localhost:8000/admin/`.

---

### 3. App móvil (busta-app)

#### 3.1 Instalar dependencias

```bash
cd ../busta-app
npm install
```

#### 3.2 (Opcional) Forzar URL de la API

Por defecto el app detecta automáticamente el IP del Metro bundler (cuando
corres Expo Go en un celular físico) o usa `10.0.2.2` (emulador Android) /
`localhost` (iOS / web).

Si necesitás forzar otra URL editá `busta-app/app.json`:

```json
{
  "expo": {
    "extra": {
      "apiBaseUrl": "http://192.168.1.X:8000/api/v1"
    }
  }
}
```

#### 3.3 Levantar Expo

```bash
npx expo start
```

Te muestra un QR. Opciones:
- **Celular físico**: escaneá el QR con Expo Go (asegurate que el celular y la
  PC estén en la misma red WiFi).
- **Emulador Android**: presioná `a` en la terminal.
- **Emulador iOS** (solo Mac): `i`.
- **Web**: `w`.

#### 3.4 Login

- Si el contribuyente está registrado en **Mesa de Partes Virtual**: ingresá
  DNI → la pantalla detecta y pide contraseña (creá una si es primera vez).
- Si no está en MPV: el app muestra un blocker con link y video tutorial.
- Para demo local (sin BD real): DNI `12345678` / contraseña `demo1234`.

---

## Estructura del proyecto

```
App_Bustamante/
├── README.md                  # Este archivo
├── .gitignore                 # Global (Django + RN)
│
├── backend/                   # Django 5 + DRF
│   ├── .env.example           # Variables de entorno (plantilla)
│   ├── manage.py
│   ├── requirements.txt
│   ├── config/                # settings, urls, db_router, wsgi
│   │   ├── settings.py
│   │   ├── urls.py
│   │   └── db_router.py       # MultiDBRouter (default / muni_db / tramites_db)
│   └── apps/
│       ├── ciudadanos/        # AUTH_USER_MODEL custom (DNI)
│       ├── deudas/            # Predial, arbitrios, serenazgo + amnistía
│       ├── tramites/          # Trámites SIAP + IngresosExternos
│       ├── tarjetas/          # Tarjeta ciudadana + beneficios
│       │   ├── ventanilla.py  # Módulo web: emitir BustaCard en ventanilla
│       │   ├── barcode128.py  # Code 128 en Python (igual al del app)
│       │   └── templates/
│       ├── colas/             # Gestor de turnos (kiosko / ventanillero / TV)
│       │   ├── models.py      # Servicio, Ventanilla, Turno
│       │   ├── services.py    # Toda la lógica de estados del turno
│       │   ├── views.py       # Pantallas HTML + endpoints JSON
│       │   ├── api_app.py     # API JWT para el app móvil
│       │   ├── templates/     # kiosko, ventanilla, tv
│       │   └── DESPLIEGUE_KIOSKO.md
│       ├── chatbot/           # FAQs por gerencia + matcher por scoring
│       │   └── matching.py    # Normalización + scoring de tokens
│       ├── catalogos/         # Noticias, contactos, lugares
│       ├── externos_muni/     # Modelos R/O: MuniJLByR (SIAP)
│       └── externos_tramites/ # Modelos R/O: dbControl (SIAP)
│
└── busta-app/                 # React Native + Expo
    ├── app.json
    ├── package.json
    ├── tsconfig.json
    ├── app/                   # Expo Router (filesystem-based routing)
    │   ├── _layout.tsx
    │   ├── (auth)/login.tsx
    │   ├── (tabs)/
    │   │   ├── index.tsx      # Home
    │   │   ├── deudas.tsx
    │   │   ├── tarjeta.tsx
    │   │   ├── tramites.tsx
    │   │   └── perfil.tsx
    │   ├── turnos.tsx         # Colas: ver estado, pedir turno, "Ya llegué"
    │   ├── chat.tsx           # Chatbot (menús de gerencias + texto libre)
    │   └── tramites/
    │       ├── [id].tsx       # Detalle expediente + línea de vida
    │       └── nuevo.tsx
    ├── components/
    │   ├── muni/              # Botones, cards, header, badge, etc.
    │   │   ├── muni-barcode.tsx       # Code 128 puro JS
    │   │   ├── muni-video-modal.tsx   # Tutoriales YouTube
    │   │   └── ...
    │   └── ui/
    ├── constants/             # theme, config, videos, assets
    ├── hooks/
    ├── services/              # api, endpoints, storage, types
    └── store/                 # auth-context (JWT)
```

---

## Endpoints principales

Prefijo `/api/v1/`. Headers: `Authorization: Bearer <access_token>`.

| Método | Ruta | Descripción |
| --- | --- | --- |
| POST | `/ciudadanos/check-dni/` | Paso 1 del login: chequea registro MPV |
| POST | `/ciudadanos/login/` | Login con DNI + password |
| POST | `/ciudadanos/register/` | Primer set-up de password en el app |
| POST | `/auth/token/refresh/` | Renovar access token |
| GET / PATCH | `/ciudadanos/perfil/` | Perfil del ciudadano autenticado |
| GET | `/deudas/detalle/` | Desglose deuda con amnistía (con selector de condición vía `?prdconcod=X`) |
| GET | `/deudas/muni/` | Estado para emitir BustaCard |
| GET | `/tramites/mis-expedientes-siap/` | Expedientes del contribuyente |
| GET | `/tramites/expediente-siap/<cod_ing>/` | Detalle + línea de vida (proveídos) |
| GET | `/tramites/catalogo-formulario/` | Catálogo (docs, oficinas, solicitudes) |
| POST | `/tramites/registrar-tramite-externo/` | Crear trámite (multipart con PDF) |
| GET / POST | `/tarjetas/mi-tarjeta/` | Obtener o emitir/renovar tarjeta ciudadana |
| GET | `/tarjetas/beneficios/` | Beneficios disponibles |
| GET | `/colas/estado/` | Estado de las colas (servicios y espera) |
| GET | `/colas/mi-turno/` | Turno activo del ciudadano |
| POST | `/colas/pedir-turno/` | Reservar turno desde el app (queda `RESERVADO`) |
| POST | `/colas/ya-llegue/` | Check-in: entra a la fila activa |
| POST | `/colas/cancelar/` | Cancelar turno (solo antes de ser llamado) |
| GET | `/catalogos/{noticias,lugares,contactos}/` | Contenido público |

### Chatbot — prefijo `/api/chatbot/` (fuera de `v1`)

| Método | Ruta | Descripción |
| --- | --- | --- |
| GET | `/gerencias/` | Lista de gerencias (menú nivel 1) |
| GET | `/gerencias/<id>/faqs/` | Preguntas frecuentes de la gerencia (menú nivel 2) |
| POST | `/sesion/nueva/` | Abrir sesión de chat |
| POST | `/mensaje/` | Enviar consulta (texto libre o `faq_id` directo) |
| GET | `/sesion/historial/` | Historial de la sesión |

### Módulos web internos (HTML, no JSON)

| Ruta | Acceso | Descripción |
| --- | --- | --- |
| `/colas/kiosko/` | Público | Sacar turno (kiosko táctil) |
| `/colas/tv/` | Público | Pantalla de turnos en sala |
| `/colas/ventanilla/` | Staff | Módulo del ventanillero |
| `/genera_bustacard/` | Staff | Buscar contribuyente y emitir BustaCard |

---

## Comandos útiles

### Backend

```bash
# Crear superusuario manualmente
python manage.py createsuperuser

# Shell con todos los modelos cargados
python manage.py shell

# Ver SQL de una migración
python manage.py sqlmigrate ciudadanos 0001

# Tests
python manage.py test
```

### Frontend

```bash
# Limpiar cache Metro (si algo se cuelga)
npx expo start --clear

# Build de producción Android
npx expo prebuild
cd android && ./gradlew assembleRelease

# Lint
npm run lint
```

---

## Configuración de producción

Cosas a cambiar antes de desplegar a producción:

1. **`backend/.env`**:
   - `DJANGO_SECRET_KEY` ← clave aleatoria fuerte (50+ caracteres)
   - `DJANGO_DEBUG=False`
   - `DJANGO_ALLOWED_HOSTS` ← dominios reales (ej. `api.munibustamante.gob.pe`)
   - `CORS_ALLOWED_ORIGINS` ← orígenes reales

2. **`backend/config/settings.py`**:
   - `STATIC_ROOT` y `python manage.py collectstatic`
   - `MEDIA_ROOT` apuntando a almacenamiento permanente (S3/Azure)
   - Servidor de WSGI (Gunicorn / uWSGI) + reverse proxy (Nginx)

3. **`busta-app/app.json`**:
   - `extra.apiBaseUrl` ← URL pública del backend
   - `version`, `android.versionCode`, `ios.buildNumber`
   - Configurar certificados de firma

4. **Build**:
   - Android: `eas build -p android` (recomendado) o `expo prebuild` + Gradle
   - iOS: `eas build -p ios` (requiere cuenta Apple Developer)

---

## Troubleshooting

| Problema | Solución |
| --- | --- |
| `Cannot find ODBC Driver` | Instalar Microsoft ODBC Driver for SQL Server (17 ó 18) y actualizar `MSSQL_DRIVER` en `.env` |
| `Login timeout expired` | El servidor SIAP no es accesible. Verificar VPN / firewall / IP en `.env` |
| `Dependency on app with no migrations: ciudadanos` | Corre `python manage.py makemigrations ciudadanos` primero |
| Expo Go no carga el app | Verificar que celular y PC estén en la misma red WiFi |
| `Network request failed` en el app | El backend debe estar en `0.0.0.0:8000` (no `127.0.0.1`) para que el celular físico lo alcance |
| Pantalla en blanco después de login | Verificar token JWT en SecureStore. Limpiar app y reloguear |
| `TemplateDoesNotExist` tras crear templates nuevos | Django cachea los directorios de templates al arrancar: **reiniciar el servidor** |
| El kiosko muestra el diálogo de imprimir en vez de imprimir solo | Chrome ya estaba abierto y descartó el flag. Usar el `.bat` (incluye `--user-data-dir`, que fuerza una instancia nueva con `--kiosk-printing`) |
| El kiosko no conecta al servidor | La URL debe apuntar a la **IP del servidor** (no `localhost`), el servidor escuchar en `0.0.0.0:8052`, esa IP estar en `DJANGO_ALLOWED_HOSTS` y el puerto abierto en el firewall |

---

## Paleta y branding

- Azul institucional `#0B3D91`
- Amarillo (escudo) `#F5B800`
- Blanco `#FFFFFF`

Tipografía sistema. Tema centralizado en `busta-app/constants/theme.ts`.

---

## Roadmap

- [x] Gestor de colas (kiosko, ventanillero, TV) + integración en el app
- [x] Emisión de BustaCard desde ventanilla
- [x] Chatbot con menús de gerencias y matcher por scoring
- [ ] Integración con RENIEC (validación DNI)
- [ ] Pasarela de pagos (Niubiz / Izipay)
- [ ] Notificaciones push (FCM / APNs)
- [ ] Firma electrónica de expedientes
- [ ] Modo offline para tarjeta ciudadana
- [ ] Métricas de atención (tiempos de espera por ventanilla)
- [ ] Tests automatizados (pytest + Detox)

---

## Contacto

Soporte: tecnologiasinformacion@munibustamante.gob.pe

Proyecto desarrollado para la Municipalidad Distrital de José Luis Bustamante
y Rivero, Arequipa, Perú.

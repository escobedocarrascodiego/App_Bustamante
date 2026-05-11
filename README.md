# App Bustamante — Municipalidad Distrital JLBR

App ciudadana de la **Municipalidad Distrital de José Luis Bustamante y Rivero**
(Arequipa, Perú). Permite consultar deudas tributarias, iniciar trámites contra
Mesa de Partes Virtual (SIAP), emitir tarjeta ciudadana digital con beneficios
y mantener al vecino informado.

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
python manage.py makemigrations deudas tramites tarjetas catalogos
python manage.py migrate
```

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
| GET / POST | `/tarjetas/mi-tarjeta/` | Obtener o emitir tarjeta ciudadana |
| GET | `/tarjetas/beneficios/` | Beneficios disponibles |
| GET | `/catalogos/{noticias,lugares,contactos}/` | Contenido público |

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

---

## Paleta y branding

- Azul institucional `#0B3D91`
- Amarillo (escudo) `#F5B800`
- Blanco `#FFFFFF`

Tipografía sistema. Tema centralizado en `busta-app/constants/theme.ts`.

---

## Roadmap

- [ ] Integración con RENIEC (validación DNI)
- [ ] Pasarela de pagos (Niubiz / Izipay)
- [ ] Notificaciones push (FCM / APNs)
- [ ] Firma electrónica de expedientes
- [ ] Modo offline para tarjeta ciudadana
- [ ] Tests automatizados (pytest + Detox)

---

## Contacto

Soporte: tecnologiasinformacion@munibustamante.gob.pe

Proyecto desarrollado para la Municipalidad Distrital de José Luis Bustamante
y Rivero, Arequipa, Perú.

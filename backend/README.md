# Backend Busta-App (Django + DRF)

API REST de la Municipalidad Distrital de Jose Luis Bustamante y Rivero.

## Stack

- Python 3.11+
- Django 5.1
- Django REST Framework + SimpleJWT
- SQLite (desarrollo) / PostgreSQL (produccion)

## Primeros pasos

### PowerShell

```powershell
cd D:\Programación\App_Bustamante\backend
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
python manage.py makemigrations ciudadanos
python manage.py makemigrations deudas tramites tarjetas catalogos
python manage.py migrate
python manage.py seed_demo
python manage.py runserver 0.0.0.0:8000
```

### cmd (Windows)

```cmd
cd D:\Programación\App_Bustamante\backend
python -m venv venv
venv\Scripts\activate.bat
pip install -r requirements.txt
copy .env.example .env
python manage.py makemigrations ciudadanos
python manage.py makemigrations deudas tramites tarjetas catalogos
python manage.py migrate
python manage.py seed_demo
python manage.py runserver 0.0.0.0:8000
```

> **Importante**: `ciudadanos` debe migrar primero porque define el `AUTH_USER_MODEL`
> del que dependen las demas apps via `ForeignKey`. Si corres `migrate` directo sin
> `makemigrations`, Django arroja `Dependency on app with no migrations: ciudadanos`.

Credenciales demo (creadas por `seed_demo`):
- Ciudadano: DNI `12345678` / contrasena `demo1234`
- Admin Django: DNI `00000000` / contrasena `admin1234` (ir a `/admin/`)

## Estructura

```
backend/
├── config/            # settings, urls, wsgi
└── apps/
    ├── ciudadanos/    # usuario ciudadano (DNI + JWT)
    ├── deudas/        # predial, arbitrios, multas, papeletas
    ├── tramites/      # TUPA, expedientes y seguimientos
    ├── tarjetas/      # tarjeta digital ciudadana + beneficios
    └── catalogos/     # noticias, lugares, contactos
```

## Endpoints principales (prefijo `/api/v1/`)

| Metodo | Ruta | Descripcion |
| --- | --- | --- |
| POST | `/ciudadanos/registro/` | Alta de ciudadano |
| POST | `/ciudadanos/login/` | Login con DNI + contrasena, devuelve JWT |
| POST | `/auth/token/refresh/` | Renovar access token |
| GET/PATCH | `/ciudadanos/perfil/` | Perfil del ciudadano autenticado |
| GET | `/deudas/` | Lista deudas propias |
| GET | `/deudas/resumen/` | Totales por tipo |
| POST | `/deudas/{id}/pagar/` | Registra pago (mock desde el app) |
| GET | `/tramites/tipos/` | TUPA disponible |
| GET/POST | `/tramites/expedientes/` | Mis expedientes / iniciar nuevo |
| GET | `/tramites/expedientes/{id}/` | Detalle + seguimientos |
| GET/POST | `/tarjetas/mi-tarjeta/` | Obtener o emitir tarjeta ciudadana |
| GET | `/tarjetas/beneficios/` | Beneficios disponibles |
| GET | `/catalogos/noticias/` | Noticias publicadas |
| GET | `/catalogos/lugares/` | Lugares de interes |
| GET | `/catalogos/contactos/` | Contactos municipales |

## Notas

- La autenticacion se hace con header `Authorization: Bearer <access>`.
- CORS esta abierto en modo `DEBUG=True`. En produccion configurar `CORS_ALLOWED_ORIGINS`.
- La validacion contra RENIEC / padron municipal esta fuera del MVP; el campo `verificado` se marca manualmente.
- Para produccion: cambiar a PostgreSQL, configurar `SECRET_KEY` y servir archivos estaticos/media.

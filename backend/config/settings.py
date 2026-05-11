"""
Configuracion Django para el backend de la Municipalidad Distrital
Jose Luis Bustamante y Rivero.
"""
from datetime import timedelta
from pathlib import Path

from decouple import Csv, config

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = config("DJANGO_SECRET_KEY", default="dev-insecure-key-change-me")
DEBUG = config("DJANGO_DEBUG", default=True, cast=bool)
ALLOWED_HOSTS = config(
    "DJANGO_ALLOWED_HOSTS",
    default="localhost,127.0.0.1,10.0.2.2",
    cast=Csv(),
)

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # terceros
    "rest_framework",
    "rest_framework_simplejwt",
    "corsheaders",
    "django_filters",
    # apps internas (escritura en default)
    "apps.ciudadanos",
    "apps.deudas",
    "apps.tramites",
    "apps.tarjetas",
    "apps.catalogos",
    # apps externas de solo lectura (producción)
    "apps.externos_tramites",
    "apps.externos_muni",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# Credenciales y hosts de SQL Server desde .env (NUNCA hardcodear).
_MSSQL_DRIVER = config("MSSQL_DRIVER", default="ODBC Driver 13 for SQL Server")
_MSSQL_USER = config("MSSQL_USER", default="")
_MSSQL_PASSWORD = config("MSSQL_PASSWORD", default="")
_MSSQL_PORT = config("MSSQL_PORT", default="1433")

DATABASES = {
    "default": {
        "ENGINE": "mssql",
        "NAME": config("DB_DEFAULT_NAME", default="dbbusta_app"),
        "USER": _MSSQL_USER,
        "PASSWORD": _MSSQL_PASSWORD,
        "HOST": config("DB_DEFAULT_HOST", default="localhost"),
        "PORT": _MSSQL_PORT,
        "OPTIONS": {"driver": _MSSQL_DRIVER},
    },
    "muni_db": {
        "ENGINE": "mssql",
        "NAME": config("DB_MUNI_NAME", default="MuniJLByR"),
        "USER": _MSSQL_USER,
        "PASSWORD": _MSSQL_PASSWORD,
        "HOST": config("DB_MUNI_HOST", default="localhost"),
        "PORT": _MSSQL_PORT,
        "OPTIONS": {"driver": _MSSQL_DRIVER},
    },
    "tramites_db": {
        "ENGINE": "mssql",
        "NAME": config("DB_TRAMITES_NAME", default="dbControl"),
        "USER": _MSSQL_USER,
        "PASSWORD": _MSSQL_PASSWORD,
        "HOST": config("DB_TRAMITES_HOST", default="localhost"),
        "PORT": _MSSQL_PORT,
        "OPTIONS": {"driver": _MSSQL_DRIVER},
    },
}

DATABASE_ROUTERS = ["config.db_router.MultiDBRouter"]

AUTH_USER_MODEL = "ciudadanos.Ciudadano"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "es-pe"
TIME_ZONE = "America/Lima"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
    ),
    "DEFAULT_FILTER_BACKENDS": (
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ),
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(hours=12),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=30),
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "user_id",
}

CORS_ALLOWED_ORIGINS = config(
    "CORS_ALLOWED_ORIGINS",
    default="http://localhost:8081,http://localhost:19006",
    cast=Csv(),
)
CORS_ALLOW_ALL_ORIGINS = DEBUG

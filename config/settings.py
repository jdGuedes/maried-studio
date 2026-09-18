from pathlib import Path
import os
import sys

import dj_database_url
from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv

from .cache import build_caches_config
from .storage import build_storages_config
from .web_security import REMOTE_WEB_ENVS, build_web_security_config


# ============================================================
# BASE
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(
    BASE_DIR / ".env"
)


def env_bool(name, default=False):
    value = os.getenv(name)

    if value is None:
        return default

    return value.strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def env_int(name, default):
    value = os.getenv(name)

    if value is None or value.strip() == "":
        return default

    try:
        return int(value)

    except ValueError as exc:
        raise ImproperlyConfigured(
            f"{name} deve ser um número inteiro."
        ) from exc


def env_list(name, default=None):
    value = os.getenv(name)

    if value is None:
        return list(default or [])

    return [
        item.strip()
        for item in value.split(",")
        if item.strip()
    ]


def require_env(name):
    value = os.getenv(name)

    if value is None or value.strip() == "":
        raise ImproperlyConfigured(
            f"{name} precisa estar configurado."
        )

    return value


# ============================================================
# SEGURANÇA / AMBIENTE
# ============================================================

DJANGO_ENV = os.getenv(
    "DJANGO_ENV",
    "development",
).strip().lower()

IS_PRODUCTION = (
    DJANGO_ENV == "production"
)

IS_REMOTE_ENV = (
    DJANGO_ENV in REMOTE_WEB_ENVS
)

SECRET_KEY = os.getenv(
    "DJANGO_SECRET_KEY",
    "",
)

if not SECRET_KEY:
    if IS_REMOTE_ENV:
        raise ImproperlyConfigured(
            "DJANGO_SECRET_KEY precisa estar configurado em staging/produção."
        )

    SECRET_KEY = "dev-only-secret-key"

if (
    IS_REMOTE_ENV
    and SECRET_KEY == "dev-only-secret-key"
):
    raise ImproperlyConfigured(
        "DJANGO_SECRET_KEY de desenvolvimento não pode ser usada "
        "em staging/produção."
    )

DEBUG = env_bool(
    "DJANGO_DEBUG",
    default=not IS_REMOTE_ENV,
)

if IS_REMOTE_ENV and DEBUG:
    raise ImproperlyConfigured(
        "DJANGO_DEBUG deve ser false em staging/produção."
    )

# ============================================================
# APLICAÇÕES
# ============================================================

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    "rest_framework",
    "django_filters",
    "corsheaders",

    "apps.accounts",
    "apps.organizations",
    "apps.credits",
    "apps.products",
    "apps.studio",
    "apps.billing",
    "apps.ai",
    "apps.audit",
    "apps.superadmin",
]


# ============================================================
# MIDDLEWARE
# ============================================================

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",

    "django.contrib.sessions.middleware.SessionMiddleware",

    "corsheaders.middleware.CorsMiddleware",

    "django.middleware.common.CommonMiddleware",

    "django.middleware.csrf.CsrfViewMiddleware",

    "django.contrib.auth.middleware.AuthenticationMiddleware",

    "django.contrib.messages.middleware.MessageMiddleware",

    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]


# ============================================================
# URLS
# ============================================================

ROOT_URLCONF = "config.urls"


# ============================================================
# TEMPLATES
# ============================================================

TEMPLATES = [
    {
        "BACKEND": (
            "django.template.backends."
            "django.DjangoTemplates"
        ),

        "DIRS": [],

        "APP_DIRS": True,

        "OPTIONS": {
            "context_processors": [
                (
                    "django.template.context_processors."
                    "request"
                ),

                (
                    "django.contrib.auth."
                    "context_processors.auth"
                ),

                (
                    "django.contrib.messages."
                    "context_processors.messages"
                ),
            ],
        },
    },
]


# ============================================================
# WSGI / ASGI
# ============================================================

WSGI_APPLICATION = (
    "config.wsgi.application"
)

ASGI_APPLICATION = (
    "config.asgi.application"
)


# ============================================================
# SENHAS
# ============================================================

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "UserAttributeSimilarityValidator"
        ),
    },
    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "MinimumLengthValidator"
        ),
        "OPTIONS": {
            "min_length": 8,
        },
    },
    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "CommonPasswordValidator"
        ),
    },
    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "NumericPasswordValidator"
        ),
    },
]

PASSWORD_RESET_TIMEOUT = env_int(
    "DJANGO_PASSWORD_RESET_TIMEOUT",
    3600,
)

ACCOUNT_RECOVERY_TOKEN_TIMEOUT = env_int(
    "ACCOUNT_RECOVERY_TOKEN_TIMEOUT",
    1800,
)

ACCOUNT_RECOVERY_CHALLENGE_TIMEOUT = env_int(
    "ACCOUNT_RECOVERY_CHALLENGE_TIMEOUT",
    900,
)

ACCOUNT_RECOVERY_FAILED_ATTEMPT_LIMIT = env_int(
    "ACCOUNT_RECOVERY_FAILED_ATTEMPT_LIMIT",
    5,
)

ACCOUNT_RECOVERY_BLOCK_MINUTES = env_int(
    "ACCOUNT_RECOVERY_BLOCK_MINUTES",
    15,
)

ACCOUNT_RECOVERY_ENFORCE_ONBOARDING = env_bool(
    "ACCOUNT_RECOVERY_ENFORCE_ONBOARDING",
    default=not (
        "test"
        in sys.argv
    ),
)


SECURITY_RATE_LIMITS = {
    "login_ip": {
        "limit": 20,
        "window": 600,
    },
    "login_identifier": {
        "limit": 10,
        "window": 900,
    },
    "password_reset_request_ip": {
        "limit": 10,
        "window": 600,
    },
    "password_reset_request_identifier": {
        "limit": 3,
        "window": 900,
    },
    "password_reset_confirm_ip": {
        "limit": 20,
        "window": 600,
    },
    "password_reset_confirm_token": {
        "limit": 5,
        "window": 900,
    },
    "recovery_key_ip": {
        "limit": 10,
        "window": 600,
    },
    "recovery_key_identifier": {
        "limit": 5,
        "window": 900,
    },
    "recovery_questions_request_ip": {
        "limit": 10,
        "window": 600,
    },
    "recovery_questions_request_identifier": {
        "limit": 5,
        "window": 900,
    },
    "recovery_questions_verify_ip": {
        "limit": 10,
        "window": 600,
    },
    "recovery_questions_verify_challenge": {
        "limit": 5,
        "window": 900,
    },
    "recovery_reset_ip": {
        "limit": 10,
        "window": 600,
    },
    "recovery_reset_token": {
        "limit": 5,
        "window": 900,
    },
    "authenticated_password_user": {
        "limit": 8,
        "window": 900,
    },
    "recovery_authenticated_user": {
        "limit": 10,
        "window": 900,
    },
}


# ============================================================
# DATABASE
# ============================================================
#
# IMPORTANTE:
#
# Mantemos a configuração original que já estava funcionando
# com PostgreSQL / Supabase.
#
# NÃO aplicamos aqui nenhuma alteração específica para testes.
#
# O problema observado anteriormente acontecia somente durante
# a destruição do banco temporário test_postgres, depois dos
# testes já terem terminado com OK.
#
# Portanto não devemos alterar a conexão principal para tentar
# resolver aquele problema.
# ============================================================

DATABASES = {
    "default": dj_database_url.config(
        default=(
            require_env("DATABASE_URL")
            if IS_PRODUCTION
            else os.getenv(
                "DATABASE_URL",
                f"sqlite:///{BASE_DIR / 'db.sqlite3'}",
            )
        ),
        conn_max_age=env_int(
            "DATABASE_CONN_MAX_AGE",
            600,
        ),
        ssl_require=env_bool(
            "DATABASE_SSL_REQUIRE",
            default=IS_PRODUCTION,
        ),
    )
}


# ============================================================
# USUÁRIO CUSTOMIZADO
# ============================================================

AUTH_USER_MODEL = (
    "accounts.User"
)


# ============================================================
# INTERNACIONALIZAÇÃO
# ============================================================

LANGUAGE_CODE = (
    "pt-br"
)

TIME_ZONE = (
    "America/Fortaleza"
)

USE_I18N = True

USE_TZ = True


# ============================================================
# ARQUIVOS ESTÁTICOS
# ============================================================

STATIC_URL = (
    os.getenv(
        "DJANGO_STATIC_URL",
        "static/",
    )
)

STATIC_ROOT = (
    BASE_DIR
    / os.getenv(
        "DJANGO_STATIC_ROOT",
        "staticfiles",
    )
)


# ============================================================
# MEDIA
# ============================================================

MEDIA_URL = (
    os.getenv(
        "DJANGO_MEDIA_URL",
        "media/",
    )
)

MEDIA_ROOT = (
    Path(
        os.getenv(
            "DJANGO_MEDIA_ROOT",
            str(BASE_DIR / "media"),
        )
    )
)

PRIVATE_MEDIA_BY_DEFAULT = env_bool(
    "DJANGO_PRIVATE_MEDIA_BY_DEFAULT",
    default=True,
)

DJANGO_MEDIA_STORAGE_BACKEND, STORAGES = build_storages_config(
    django_env=DJANGO_ENV,
    base_dir=BASE_DIR,
    env=os.environ,
)

DJANGO_CACHE_BACKEND, CACHES = build_caches_config(
    django_env=DJANGO_ENV,
    env=os.environ,
)


# ============================================================
# DEFAULT PRIMARY KEY
# ============================================================

DEFAULT_AUTO_FIELD = (
    "django.db.models.BigAutoField"
)


# ============================================================
# DJANGO REST FRAMEWORK
# ============================================================

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        (
            "rest_framework.authentication."
            "SessionAuthentication"
        ),
    ],

    "DEFAULT_PERMISSION_CLASSES": [
        (
            "rest_framework.permissions."
            "IsAuthenticated"
        ),
    ],

    "DEFAULT_FILTER_BACKENDS": [
        (
            "django_filters.rest_framework."
            "DjangoFilterBackend"
        ),
    ],

    "DEFAULT_PAGINATION_CLASS": (
        "rest_framework.pagination."
        "PageNumberPagination"
    ),

    "PAGE_SIZE": 20,
}


# ============================================================
# OPENAI
# ============================================================

OPENAI_API_KEY = (
    require_env("OPENAI_API_KEY")
    if IS_PRODUCTION
    else os.getenv(
        "OPENAI_API_KEY",
        "",
    )
)

OPENAI_IMAGE_MODEL = os.getenv(
    "OPENAI_IMAGE_MODEL",
    "gpt-image-2",
)

OPENAI_IMAGE_SIZE = os.getenv(
    "OPENAI_IMAGE_SIZE",
    "1024x1024",
)


# ============================================================
# STRIPE
# ============================================================

STRIPE_SECRET_KEY = (
    require_env("STRIPE_SECRET_KEY")
    if IS_PRODUCTION
    else os.getenv(
        "STRIPE_SECRET_KEY",
        "",
    )
)

STRIPE_PUBLISHABLE_KEY = os.getenv(
    "STRIPE_PUBLISHABLE_KEY",
    "",
)

STRIPE_WEBHOOK_SECRET = os.getenv(
    "STRIPE_WEBHOOK_SECRET",
    "",
)

STRIPE_CURRENCY = os.getenv(
    "STRIPE_CURRENCY",
    "brl",
).lower()

STRIPE_API_VERSION = os.getenv(
    "STRIPE_API_VERSION",
    "2026-07-29.dahlia",
)

STRIPE_ALLOW_LIVE_MODE = env_bool(
    "STRIPE_ALLOW_LIVE_MODE",
    default=False,
)


# ============================================================
# FRONTEND / WEB SECURITY
# ============================================================

WEB_SECURITY = build_web_security_config(
    django_env=DJANGO_ENV,
    env=os.environ,
)

FRONTEND_URL = WEB_SECURITY["FRONTEND_URL"]
ALLOWED_HOSTS = WEB_SECURITY["ALLOWED_HOSTS"]

EMAIL_PASSWORD_RECOVERY_ENABLED = env_bool(
    "EMAIL_PASSWORD_RECOVERY_ENABLED",
    default=False,
)

RESEND_API_KEY = (
    require_env("RESEND_API_KEY")
    if IS_PRODUCTION and EMAIL_PASSWORD_RECOVERY_ENABLED
    else os.getenv(
        "RESEND_API_KEY",
        "",
    )
)

EMAIL_FROM = (
    require_env("EMAIL_FROM")
    if IS_PRODUCTION and EMAIL_PASSWORD_RECOVERY_ENABLED
    else os.getenv(
        "EMAIL_FROM",
        "MARIED Studio <onboarding@resend.dev>",
    )
)

CORS_ALLOWED_ORIGINS = WEB_SECURITY["CORS_ALLOWED_ORIGINS"]

CORS_ALLOW_CREDENTIALS = WEB_SECURITY["CORS_ALLOW_CREDENTIALS"]


# ============================================================
# CSRF
# ============================================================

CSRF_TRUSTED_ORIGINS = WEB_SECURITY["CSRF_TRUSTED_ORIGINS"]


# ============================================================
# COOKIES / HTTPS
# ============================================================

SESSION_COOKIE_SECURE = WEB_SECURITY["SESSION_COOKIE_SECURE"]

CSRF_COOKIE_SECURE = WEB_SECURITY["CSRF_COOKIE_SECURE"]

SESSION_COOKIE_HTTPONLY = WEB_SECURITY["SESSION_COOKIE_HTTPONLY"]

CSRF_COOKIE_HTTPONLY = WEB_SECURITY["CSRF_COOKIE_HTTPONLY"]

SESSION_COOKIE_SAMESITE = WEB_SECURITY["SESSION_COOKIE_SAMESITE"]

CSRF_COOKIE_SAMESITE = WEB_SECURITY["CSRF_COOKIE_SAMESITE"]

SESSION_COOKIE_DOMAIN = WEB_SECURITY["SESSION_COOKIE_DOMAIN"]

CSRF_COOKIE_DOMAIN = WEB_SECURITY["CSRF_COOKIE_DOMAIN"]

SECURE_SSL_REDIRECT = WEB_SECURITY["SECURE_SSL_REDIRECT"]

SECURE_HSTS_SECONDS = WEB_SECURITY["SECURE_HSTS_SECONDS"]

SECURE_HSTS_INCLUDE_SUBDOMAINS = WEB_SECURITY[
    "SECURE_HSTS_INCLUDE_SUBDOMAINS"
]

SECURE_HSTS_PRELOAD = WEB_SECURITY["SECURE_HSTS_PRELOAD"]

SECURE_CONTENT_TYPE_NOSNIFF = True

SECURE_REFERRER_POLICY = WEB_SECURITY["SECURE_REFERRER_POLICY"]

if WEB_SECURITY["USE_X_FORWARDED_PROTO"]:
    SECURE_PROXY_SSL_HEADER = (
        "HTTP_X_FORWARDED_PROTO",
        "https",
    )


# ============================================================
# CORS — SOMENTE API=

CORS_URLS_REGEX = (
    r"^/api/.*$"
)


# ============================================================
# LOGGING
# ============================================================

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "console": {
            "format": (
                "%(levelname)s "
                "%(name)s "
                "%(message)s"
            ),
        },
    },
    "handlers": {
        "console": {
            "class": (
                "logging.StreamHandler"
            ),
            "formatter": "console",
        },
    },
    "root": {
        "handlers": [
            "console",
        ],
        "level": os.getenv(
            "DJANGO_LOG_LEVEL",
            "INFO",
        ),
    },
}

from urllib.parse import urlparse

from django.core.exceptions import ImproperlyConfigured


REMOTE_STORAGE_ENVS = {
    "staging",
    "production",
}

LOCAL_STORAGE_BACKEND = "local"
SUPABASE_STORAGE_BACKEND = "supabase"


def _get_env(
    env,
    name,
    default="",
):
    value = env.get(
        name,
        default,
    )

    if value is None:
        return ""

    return str(value).strip()


def _require_storage_env(
    env,
    name,
):
    value = _get_env(
        env,
        name,
    )

    if not value:
        raise ImproperlyConfigured(
            f"{name} precisa estar configurado para storage remoto."
        )

    return value


def _validate_remote_endpoint(
    *,
    endpoint_url,
    django_env,
):
    parsed = urlparse(
        endpoint_url
    )

    if not parsed.scheme or not parsed.netloc:
        raise ImproperlyConfigured(
            "SUPABASE_STORAGE_ENDPOINT deve ser uma URL absoluta."
        )

    if (
        django_env in REMOTE_STORAGE_ENVS
        and parsed.scheme != "https"
    ):
        raise ImproperlyConfigured(
            "SUPABASE_STORAGE_ENDPOINT deve usar HTTPS em staging/production."
        )


def build_storages_config(
    *,
    django_env,
    base_dir,
    env,
):
    storage_backend = _get_env(
        env,
        "DJANGO_MEDIA_STORAGE_BACKEND",
        default=(
            SUPABASE_STORAGE_BACKEND
            if django_env in REMOTE_STORAGE_ENVS
            else LOCAL_STORAGE_BACKEND
        ),
    ).lower()

    static_storage = {
        "BACKEND": (
            "django.contrib.staticfiles.storage."
            "StaticFilesStorage"
        ),
    }

    if storage_backend == LOCAL_STORAGE_BACKEND:
        if django_env in REMOTE_STORAGE_ENVS:
            raise ImproperlyConfigured(
                "DJANGO_MEDIA_STORAGE_BACKEND=local nÃ£o Ã© permitido "
                "em staging/production."
            )

        return storage_backend, {
            "default": {
                "BACKEND": (
                    "django.core.files.storage."
                    "FileSystemStorage"
                ),
                "OPTIONS": {
                    "location": _get_env(
                        env,
                        "DJANGO_MEDIA_ROOT",
                        default=str(
                            base_dir / "media"
                        ),
                    ),
                    "base_url": _get_env(
                        env,
                        "DJANGO_MEDIA_URL",
                        default="media/",
                    ),
                },
            },
            "staticfiles": static_storage,
        }

    if storage_backend != SUPABASE_STORAGE_BACKEND:
        raise ImproperlyConfigured(
            "DJANGO_MEDIA_STORAGE_BACKEND deve ser 'local' ou 'supabase'."
        )

    endpoint_url = _require_storage_env(
        env,
        "SUPABASE_STORAGE_ENDPOINT",
    ).rstrip("/")

    _validate_remote_endpoint(
        endpoint_url=endpoint_url,
        django_env=django_env,
    )

    return storage_backend, {
        "default": {
            "BACKEND": (
                "storages.backends.s3.S3Storage"
            ),
            "OPTIONS": {
                "bucket_name": _require_storage_env(
                    env,
                    "SUPABASE_STORAGE_BUCKET",
                ),
                "endpoint_url": endpoint_url,
                "region_name": _require_storage_env(
                    env,
                    "SUPABASE_STORAGE_REGION",
                ),
                "access_key": _require_storage_env(
                    env,
                    "SUPABASE_STORAGE_ACCESS_KEY",
                ),
                "secret_key": _require_storage_env(
                    env,
                    "SUPABASE_STORAGE_SECRET_KEY",
                ),
                "addressing_style": "path",
                "signature_version": "s3v4",
                "default_acl": None,
                "querystring_auth": True,
                "file_overwrite": False,
                "object_parameters": {
                    "CacheControl": "private, no-store",
                },
            },
        },
        "staticfiles": static_storage,
    }

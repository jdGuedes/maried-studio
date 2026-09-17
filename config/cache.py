from urllib.parse import urlparse

from django.core.exceptions import ImproperlyConfigured


REMOTE_CACHE_ENVS = {
    "staging",
    "production",
}

LOCAL_CACHE_BACKEND = "local"
REDIS_CACHE_BACKEND = "redis"


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


def _require_env(
    env,
    name,
):
    value = _get_env(
        env,
        name,
    )

    if not value:
        raise ImproperlyConfigured(
            f"{name} precisa estar configurado para cache Redis."
        )

    return value


def _cache_key_prefix(
    *,
    django_env,
    env,
):
    prefix = _get_env(
        env,
        "DJANGO_CACHE_KEY_PREFIX",
        default=f"maried:{django_env}",
    )

    if not prefix:
        raise ImproperlyConfigured(
            "DJANGO_CACHE_KEY_PREFIX cannot be empty."
        )

    return prefix


def _validate_redis_url(
    *,
    redis_url,
    django_env,
):
    parsed = urlparse(
        redis_url
    )

    if not parsed.scheme or not parsed.netloc:
        raise ImproperlyConfigured(
            "REDIS_URL deve ser uma URL absoluta."
        )

    allowed_schemes = {
        "redis",
        "rediss",
    }

    if parsed.scheme not in allowed_schemes:
        raise ImproperlyConfigured(
            "REDIS_URL deve usar redis:// ou rediss://."
        )

    if (
        django_env in REMOTE_CACHE_ENVS
        and parsed.scheme != "rediss"
    ):
        raise ImproperlyConfigured(
            "REDIS_URL deve usar rediss:// em staging/production."
        )


def build_caches_config(
    *,
    django_env,
    env,
):
    cache_backend = _get_env(
        env,
        "DJANGO_CACHE_BACKEND",
        default=(
            REDIS_CACHE_BACKEND
            if django_env in REMOTE_CACHE_ENVS
            else LOCAL_CACHE_BACKEND
        ),
    ).lower()

    key_prefix = _cache_key_prefix(
        django_env=django_env,
        env=env,
    )

    if cache_backend == LOCAL_CACHE_BACKEND:
        if django_env in REMOTE_CACHE_ENVS:
            raise ImproperlyConfigured(
                "DJANGO_CACHE_BACKEND=local is not allowed "
                "in staging/production."
            )

        return cache_backend, {
            "default": {
                "BACKEND": (
                    "django.core.cache.backends.locmem."
                    "LocMemCache"
                ),
                "LOCATION": (
                    f"maried-{django_env}-cache"
                ),
                "KEY_PREFIX": key_prefix,
            },
        }

    if cache_backend != REDIS_CACHE_BACKEND:
        raise ImproperlyConfigured(
            "DJANGO_CACHE_BACKEND deve ser 'local' ou 'redis'."
        )

    redis_url = _require_env(
        env,
        "REDIS_URL",
    )

    _validate_redis_url(
        redis_url=redis_url,
        django_env=django_env,
    )

    return cache_backend, {
        "default": {
            "BACKEND": (
                "django.core.cache.backends.redis."
                "RedisCache"
            ),
            "LOCATION": redis_url,
            "KEY_PREFIX": key_prefix,
            "OPTIONS": {
                "socket_connect_timeout": 1,
                "socket_timeout": 1,
            },
        },
    }

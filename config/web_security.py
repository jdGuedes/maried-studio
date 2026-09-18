from urllib.parse import urlparse

from django.core.exceptions import ImproperlyConfigured


REMOTE_WEB_ENVS = {
    "staging",
    "production",
}

LOCAL_FRONTEND_URL = "http://localhost:3000"
LOCAL_ALLOWED_HOSTS = [
    "127.0.0.1",
    "localhost",
]
LOCAL_API_ORIGINS = [
    LOCAL_FRONTEND_URL,
]

LOCAL_HOSTS = {
    "localhost",
    "127.0.0.1",
    "::1",
}

VALID_SAMESITE_VALUES = {
    "Lax",
    "Strict",
    "None",
}


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


def _env_bool(
    env,
    name,
    default=False,
):
    value = _get_env(
        env,
        name,
    )

    if not value:
        return default

    return value.lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def _env_int(
    env,
    name,
    default,
):
    value = _get_env(
        env,
        name,
    )

    if not value:
        return default

    try:
        return int(value)
    except ValueError as exc:
        raise ImproperlyConfigured(
            f"{name} must be an integer."
        ) from exc


def _env_list(
    env,
    name,
    default=None,
):
    value = env.get(
        name,
    )

    if value is None:
        return list(
            default or []
        )

    items = []
    seen = set()

    for item in str(value).split(","):
        normalized = item.strip()

        if not normalized:
            continue

        if normalized in seen:
            continue

        seen.add(
            normalized
        )
        items.append(
            normalized
        )

    return items


def _is_remote_env(
    django_env,
):
    return django_env in REMOTE_WEB_ENVS


def _require_non_empty(
    *,
    value,
    name,
    django_env,
):
    if not value and _is_remote_env(
        django_env
    ):
        raise ImproperlyConfigured(
            f"{name} must be configured in staging/production."
        )


def _origin_without_trailing_slash(
    origin,
):
    return origin.rstrip("/")


def _parse_absolute_url(
    *,
    value,
    name,
):
    parsed = urlparse(
        value
    )

    if not parsed.scheme or not parsed.netloc:
        raise ImproperlyConfigured(
            f"{name} must be an absolute URL with scheme and host."
        )

    return parsed


def _validate_remote_url(
    *,
    value,
    name,
    django_env,
    allow_path=False,
):
    parsed = _parse_absolute_url(
        value=value,
        name=name,
    )

    if parsed.hostname in LOCAL_HOSTS:
        raise ImproperlyConfigured(
            f"{name} cannot use localhost in staging/production."
        )

    if parsed.scheme != "https":
        raise ImproperlyConfigured(
            f"{name} must use https:// in staging/production."
        )

    if (
        not allow_path
        and parsed.path
        and parsed.path != "/"
    ):
        raise ImproperlyConfigured(
            f"{name} must be an origin without path."
        )

    if parsed.params or parsed.query or parsed.fragment:
        raise ImproperlyConfigured(
            f"{name} must not include params, query, or fragment."
        )

    return parsed


def _validate_origin_list(
    *,
    origins,
    name,
    django_env,
):
    normalized = []
    seen = set()

    for origin in origins:
        if origin == "*":
            raise ImproperlyConfigured(
                f"{name} cannot contain wildcard origins."
            )

        origin = _origin_without_trailing_slash(
            origin
        )

        if _is_remote_env(
            django_env
        ):
            _validate_remote_url(
                value=origin,
                name=name,
                django_env=django_env,
            )
        else:
            _parse_absolute_url(
                value=origin,
                name=name,
            )

        if origin not in seen:
            seen.add(
                origin
            )
            normalized.append(
                origin
            )

    return normalized


def _validate_allowed_hosts(
    *,
    hosts,
    django_env,
):
    if "*" in hosts:
        raise ImproperlyConfigured(
            "DJANGO_ALLOWED_HOSTS cannot contain wildcard hosts."
        )

    if _is_remote_env(
        django_env
    ):
        for host in hosts:
            hostname = host.split(
                ":",
                1,
            )[0]

            if hostname in LOCAL_HOSTS:
                raise ImproperlyConfigured(
                    "DJANGO_ALLOWED_HOSTS cannot contain localhost "
                    "in staging/production."
                )


def _cookie_samesite(
    *,
    env,
    name,
):
    value = _get_env(
        env,
        name,
        "Lax",
    )

    canonical = value.capitalize()

    if canonical not in VALID_SAMESITE_VALUES:
        raise ImproperlyConfigured(
            f"{name} must be Lax, Strict, or None."
        )

    return canonical


def _cookie_domain(
    *,
    env,
    name,
    django_env,
):
    value = _get_env(
        env,
        name,
    )

    if not value:
        return None

    if "://" in value or "/" in value:
        raise ImproperlyConfigured(
            f"{name} must be a cookie domain, not a URL."
        )

    hostname = value.lstrip(
        "."
    )

    if (
        _is_remote_env(
            django_env
        )
        and hostname in LOCAL_HOSTS
    ):
        raise ImproperlyConfigured(
            f"{name} cannot use localhost in staging/production."
        )

    return value


def build_web_security_config(
    *,
    django_env,
    env,
):
    remote = _is_remote_env(
        django_env
    )

    frontend_url = _get_env(
        env,
        "FRONTEND_URL",
        default="" if remote else LOCAL_FRONTEND_URL,
    ).rstrip("/")

    _require_non_empty(
        value=frontend_url,
        name="FRONTEND_URL",
        django_env=django_env,
    )

    if frontend_url:
        if remote:
            _validate_remote_url(
                value=frontend_url,
                name="FRONTEND_URL",
                django_env=django_env,
                allow_path=True,
            )
        else:
            _parse_absolute_url(
                value=frontend_url,
                name="FRONTEND_URL",
            )

    allowed_hosts = _env_list(
        env,
        "DJANGO_ALLOWED_HOSTS",
        default=[] if remote else LOCAL_ALLOWED_HOSTS,
    )

    _require_non_empty(
        value=allowed_hosts,
        name="DJANGO_ALLOWED_HOSTS",
        django_env=django_env,
    )
    _validate_allowed_hosts(
        hosts=allowed_hosts,
        django_env=django_env,
    )

    cors_allowed_origins = _env_list(
        env,
        "DJANGO_CORS_ALLOWED_ORIGINS",
        default=[] if remote else LOCAL_API_ORIGINS,
    )
    _require_non_empty(
        value=cors_allowed_origins,
        name="DJANGO_CORS_ALLOWED_ORIGINS",
        django_env=django_env,
    )
    cors_allowed_origins = _validate_origin_list(
        origins=cors_allowed_origins,
        name="DJANGO_CORS_ALLOWED_ORIGINS",
        django_env=django_env,
    )

    csrf_trusted_origins = _env_list(
        env,
        "DJANGO_CSRF_TRUSTED_ORIGINS",
        default=[] if remote else LOCAL_API_ORIGINS,
    )
    _require_non_empty(
        value=csrf_trusted_origins,
        name="DJANGO_CSRF_TRUSTED_ORIGINS",
        django_env=django_env,
    )
    csrf_trusted_origins = _validate_origin_list(
        origins=csrf_trusted_origins,
        name="DJANGO_CSRF_TRUSTED_ORIGINS",
        django_env=django_env,
    )

    session_cookie_secure = _env_bool(
        env,
        "DJANGO_SESSION_COOKIE_SECURE",
        default=remote,
    )
    csrf_cookie_secure = _env_bool(
        env,
        "DJANGO_CSRF_COOKIE_SECURE",
        default=remote,
    )

    if remote and not session_cookie_secure:
        raise ImproperlyConfigured(
            "DJANGO_SESSION_COOKIE_SECURE must be true "
            "in staging/production."
        )

    if remote and not csrf_cookie_secure:
        raise ImproperlyConfigured(
            "DJANGO_CSRF_COOKIE_SECURE must be true "
            "in staging/production."
        )

    session_cookie_samesite = _cookie_samesite(
        env=env,
        name="DJANGO_SESSION_COOKIE_SAMESITE",
    )
    csrf_cookie_samesite = _cookie_samesite(
        env=env,
        name="DJANGO_CSRF_COOKIE_SAMESITE",
    )

    if (
        session_cookie_samesite == "None"
        and not session_cookie_secure
    ):
        raise ImproperlyConfigured(
            "DJANGO_SESSION_COOKIE_SAMESITE=None requires "
            "DJANGO_SESSION_COOKIE_SECURE=true."
        )

    if (
        csrf_cookie_samesite == "None"
        and not csrf_cookie_secure
    ):
        raise ImproperlyConfigured(
            "DJANGO_CSRF_COOKIE_SAMESITE=None requires "
            "DJANGO_CSRF_COOKIE_SECURE=true."
        )

    return {
        "FRONTEND_URL": frontend_url,
        "ALLOWED_HOSTS": allowed_hosts,
        "CORS_ALLOWED_ORIGINS": cors_allowed_origins,
        "CORS_ALLOW_CREDENTIALS": True,
        "CSRF_TRUSTED_ORIGINS": csrf_trusted_origins,
        "SESSION_COOKIE_SECURE": session_cookie_secure,
        "CSRF_COOKIE_SECURE": csrf_cookie_secure,
        "SESSION_COOKIE_HTTPONLY": True,
        "CSRF_COOKIE_HTTPONLY": False,
        "SESSION_COOKIE_SAMESITE": session_cookie_samesite,
        "CSRF_COOKIE_SAMESITE": csrf_cookie_samesite,
        "SESSION_COOKIE_DOMAIN": _cookie_domain(
            env=env,
            name="DJANGO_SESSION_COOKIE_DOMAIN",
            django_env=django_env,
        ),
        "CSRF_COOKIE_DOMAIN": _cookie_domain(
            env=env,
            name="DJANGO_CSRF_COOKIE_DOMAIN",
            django_env=django_env,
        ),
        "SECURE_SSL_REDIRECT": _env_bool(
            env,
            "DJANGO_SECURE_SSL_REDIRECT",
            default=remote,
        ),
        "SECURE_HSTS_SECONDS": _env_int(
            env,
            "DJANGO_SECURE_HSTS_SECONDS",
            0,
        ),
        "SECURE_HSTS_INCLUDE_SUBDOMAINS": _env_bool(
            env,
            "DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS",
            default=False,
        ),
        "SECURE_HSTS_PRELOAD": _env_bool(
            env,
            "DJANGO_SECURE_HSTS_PRELOAD",
            default=False,
        ),
        "SECURE_REFERRER_POLICY": _get_env(
            env,
            "DJANGO_SECURE_REFERRER_POLICY",
            "same-origin",
        ),
        "USE_X_FORWARDED_PROTO": _env_bool(
            env,
            "DJANGO_USE_X_FORWARDED_PROTO",
            default=remote,
        ),
    }

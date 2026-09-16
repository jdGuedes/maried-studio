import logging

from django.conf import settings
from django.core.cache import cache
from django.utils.crypto import salted_hmac

from rest_framework import status
from rest_framework.response import Response


logger = logging.getLogger(__name__)


RATE_LIMIT_DETAIL = (
    "Muitas tentativas. Aguarde alguns minutos e tente novamente."
)


def client_ip(
    request,
):
    return (
        request.META.get(
            "REMOTE_ADDR",
            "",
        )
        or "unknown"
    )


def normalize_identifier(
    value,
):
    return str(
        value or ""
    ).strip().casefold()


def user_identifier(
    request,
):
    user = getattr(
        request,
        "user",
        None,
    )

    if (
        user
        and user.is_authenticated
    ):
        return str(
            user.pk
        )

    return "anonymous"


def hash_identifier(
    value,
):
    return salted_hmac(
        "accounts.rate_limit",
        normalize_identifier(
            value
        ),
    ).hexdigest()


def rate_limit_rule(
    name,
    identity,
):
    config = (
        settings
        .SECURITY_RATE_LIMITS[
            name
        ]
    )

    return {
        "name": name,
        "identity": identity,
        "limit": config["limit"],
        "window": config["window"],
    }


def check_rate_limits(
    rules,
):
    wait = None

    for rule in rules:
        key = (
            "maried:security-rate-limit:"
            f"{rule['name']}:"
            f"{hash_identifier(rule['identity'])}"
        )

        try:
            added = cache.add(
                key,
                1,
                timeout=rule["window"],
            )

            count = (
                1
                if added
                else cache.incr(
                    key
                )
            )

        except Exception as exc:
            logger.warning(
                "security_rate_limit_storage_unavailable scope=%s error=%s",
                rule["name"],
                exc.__class__.__name__,
            )
            continue

        if count > rule["limit"]:
            wait = max(
                wait or 0,
                rule["window"],
            )

    if wait is None:
        return None

    response = Response(
        {
            "detail": RATE_LIMIT_DETAIL,
        },
        status=status.HTTP_429_TOO_MANY_REQUESTS,
    )
    response[
        "Retry-After"
    ] = str(
        wait
    )

    return response

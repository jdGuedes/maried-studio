from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path


urlpatterns = [
    # ======================================================
    # ADMIN
    # ======================================================

    path(
        "admin/",
        admin.site.urls,
    ),

    # ======================================================
    # ACCOUNTS / PERFIL
    # ======================================================

    path(
        "api/accounts/",
        include(
            "apps.accounts.urls"
        ),
    ),

    # ======================================================
    # PRODUTOS
    # ======================================================

    path(
        "api/products/",
        include(
            "apps.products.urls"
        ),
    ),

    # ======================================================
    # STUDIO
    # ======================================================

    path(
        "api/studio/",
        include(
            "apps.studio.urls"
        ),
    ),

    # ======================================================
    # CRÉDITOS
    # ======================================================

    path(
        "api/credits/",
        include(
            "apps.credits.urls"
        ),
    ),

    # ======================================================
    # AI / REFERÊNCIAS
    # ======================================================

    path(
        "api/ai/",
        include(
            "apps.ai.urls"
        ),
    ),
]


# ==========================================================
# MEDIA EM DESENVOLVIMENTO
# ==========================================================

if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT,
    )

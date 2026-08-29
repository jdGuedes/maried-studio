from django.urls import path

from rest_framework.routers import (
    DefaultRouter,
)

from .views import (
    ProductAssetDownloadView,
    ProductViewSet,
)


router = DefaultRouter()

router.register(
    "",
    ProductViewSet,
    basename="product",
)


urlpatterns = [
    path(
        "assets/<uuid:pk>/download/",
        ProductAssetDownloadView.as_view(),
        name="product-asset-download",
    ),
]

urlpatterns += router.urls

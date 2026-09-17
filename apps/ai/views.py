import mimetypes

from rest_framework import (
    generics,
    permissions,
)

from django.shortcuts import get_object_or_404

from apps.common.private_media import (
    build_private_image_response,
)

from .models import (
    ModelReference,
)
from .serializers import (
    ModelReferenceSerializer,
)


class ModelReferenceListView(
    generics.ListAPIView
):
    serializer_class = (
        ModelReferenceSerializer
    )

    permission_classes = [
        permissions.IsAuthenticated,
    ]

    def get_queryset(
        self,
    ):
        return (
            ModelReference.objects
            .filter(
                is_active=True
            )
            .order_by(
                "sort_order",
                "name",
            )
        )


class ModelReferencePreviewDownloadView(
    generics.GenericAPIView
):
    permission_classes = [
        permissions.IsAuthenticated,
    ]

    def get(
        self,
        request,
        pk,
    ):
        reference = get_object_or_404(
            ModelReference.objects.filter(
                is_active=True,
            ),
            pk=pk,
        )

        return build_private_image_response(
            reference.preview_image,
            mime_type=(
                mimetypes.guess_type(
                    reference.preview_image.name
                )[0]
                or "application/octet-stream"
            ),
            filename_prefix=(
                "maried-model-reference"
            ),
        )

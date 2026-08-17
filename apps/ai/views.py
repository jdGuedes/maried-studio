from rest_framework import (
    generics,
    permissions,
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

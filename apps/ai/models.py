from django.db import models

from apps.common.models import (
    UUIDTimeStampedModel,
)


class ModelReference(
    UUIDTimeStampedModel
):
    code = models.CharField(
        max_length=30,
        unique=True,
    )

    name = models.CharField(
        max_length=120,
    )

    slug = models.SlugField(
        max_length=140,
        unique=True,
    )

    description = models.TextField()

    prompt_instruction = models.TextField()

    preview_image = models.ImageField(
        upload_to="model-references/previews/",
        null=True,
        blank=True,
    )

    skin_tone = models.CharField(
        max_length=80,
        blank=True,
    )

    hair_color = models.CharField(
        max_length=80,
        blank=True,
    )

    age_range = models.CharField(
        max_length=40,
        blank=True,
    )

    is_active = models.BooleanField(
        default=True,
    )

    sort_order = models.PositiveIntegerField(
        default=0,
    )

    class Meta:
        ordering = [
            "sort_order",
            "name",
        ]

    def __str__(
        self,
    ):
        return f"{self.code} - {self.name}"

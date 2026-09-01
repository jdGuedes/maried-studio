from django.db import models
from apps.common.models import UUIDTimeStampedModel


class Organization(UUIDTimeStampedModel):
    name = models.CharField(max_length=160)
    slug = models.SlugField(max_length=180, unique=True)
    is_active = models.BooleanField(default=True)
    stripe_customer_id = models.CharField(
        max_length=255,
        unique=True,
        null=True,
        blank=True,
    )

    def __str__(self):
        return self.name

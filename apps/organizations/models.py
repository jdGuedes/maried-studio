from django.db import models
from apps.common.models import UUIDTimeStampedModel


class Organization(UUIDTimeStampedModel):
    name = models.CharField(max_length=160)
    slug = models.SlugField(max_length=180, unique=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name

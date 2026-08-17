from django.db import models
from apps.common.models import UUIDTimeStampedModel


class AuditLog(UUIDTimeStampedModel):
    organization = models.ForeignKey("organizations.Organization", null=True, blank=True, on_delete=models.SET_NULL)
    user = models.ForeignKey("accounts.User", null=True, blank=True, on_delete=models.SET_NULL)
    action = models.CharField(max_length=120)
    entity_type = models.CharField(max_length=120, blank=True)
    entity_id = models.CharField(max_length=120, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

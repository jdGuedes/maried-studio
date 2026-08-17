from django.db import models
from apps.common.models import UUIDTimeStampedModel


class ProductCategory(models.TextChoices):
    EARRING = "EARRING", "Brinco"
    NECKLACE = "NECKLACE", "Colar"
    RING = "RING", "Anel"
    BRACELET = "BRACELET", "Pulseira"
    ANKLET = "ANKLET", "Tornozeleira"


class ProductStatus(models.TextChoices):
    ACTIVE = "ACTIVE", "Ativo"
    ARCHIVED = "ARCHIVED", "Arquivado"


class AssetType(models.TextChoices):
    ORIGINAL = "ORIGINAL", "Original"
    REFERENCE = "REFERENCE", "Referência"


class Product(UUIDTimeStampedModel):
    organization = models.ForeignKey("organizations.Organization", on_delete=models.CASCADE, related_name="products")
    created_by = models.ForeignKey("accounts.User", on_delete=models.PROTECT, related_name="created_products")
    name = models.CharField(max_length=160, blank=True)
    category = models.CharField(max_length=20, choices=ProductCategory.choices)
    status = models.CharField(max_length=20, choices=ProductStatus.choices, default=ProductStatus.ACTIVE)


class ProductAsset(UUIDTimeStampedModel):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="assets")
    asset_type = models.CharField(max_length=20, choices=AssetType.choices, default=AssetType.ORIGINAL)
    file = models.ImageField(upload_to="products/originals/%Y/%m/")
    mime_type = models.CharField(max_length=100, blank=True)
    width = models.PositiveIntegerField(null=True, blank=True)
    height = models.PositiveIntegerField(null=True, blank=True)
    file_size = models.PositiveBigIntegerField(null=True, blank=True)

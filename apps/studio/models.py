from django.db import models
from apps.common.models import UUIDTimeStampedModel


class GenerationMode(models.TextChoices):
    INSTAGRAM = "INSTAGRAM", "Instagramável"
    MODEL = "MODEL", "Modelo"
    BODY_DETAIL = "BODY_DETAIL", "Detalhe no Corpo"
    STILL = "STILL", "Still"


class GenerationStatus(models.TextChoices):
    CREATED = "CREATED", "Criada"
    CREDIT_RESERVED = "CREDIT_RESERVED", "Crédito reservado"
    PROCESSING = "PROCESSING", "Processando"
    COMPLETED = "COMPLETED", "Concluída"
    FAILED = "FAILED", "Falhou"
    CANCELLED = "CANCELLED", "Cancelada"


class FailureType(models.TextChoices):
    TECHNICAL = "TECHNICAL", "Técnica"
    VALIDATION = "VALIDATION", "Validação"
    PROVIDER = "PROVIDER", "Provedor"
    CONTENT = "CONTENT", "Conteúdo"
    UNKNOWN = "UNKNOWN", "Desconhecida"


class SceneTemplate(UUIDTimeStampedModel):
    name = models.CharField(max_length=120)
    slug = models.SlugField(max_length=140)
    generation_mode = models.CharField(max_length=20, choices=GenerationMode.choices)
    category = models.CharField(max_length=20)
    preview_image = models.ImageField(upload_to="templates/previews/", null=True, blank=True)
    prompt_template = models.TextField()
    version = models.PositiveIntegerField(default=1)
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["slug", "generation_mode", "category", "version"], name="uniq_template_version")
        ]


class GenerationRule(UUIDTimeStampedModel):
    category = models.CharField(max_length=20)
    generation_mode = models.CharField(max_length=20, choices=GenerationMode.choices)
    body_area = models.CharField(max_length=80, blank=True)
    framing = models.CharField(max_length=80)
    product_priority = models.CharField(max_length=20, default="MAXIMUM")
    body_priority = models.CharField(max_length=20, default="MEDIUM")
    background_priority = models.CharField(max_length=20, default="LOW")
    product_visibility = models.CharField(max_length=20, default="FULL")
    detail_level = models.CharField(max_length=20, default="MAXIMUM")
    placement_instruction = models.TextField(blank=True)
    additional_rules = models.JSONField(default=list, blank=True)
    is_active = models.BooleanField(default=True)   
    def __str__(self):
        return f"{self.category} | {self.generation_mode} | {self.framing}"
    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["category", "generation_mode"], name="uniq_generation_rule")
        ]


class PreservationRule(UUIDTimeStampedModel):
    category = models.CharField(max_length=20, blank=True, help_text="Vazio = regra universal")
    rule_type = models.CharField(max_length=80)
    instruction = models.TextField()
    priority = models.PositiveIntegerField(default=100)
    is_active = models.BooleanField(default=True)


class Generation(UUIDTimeStampedModel):
    organization = models.ForeignKey("organizations.Organization", on_delete=models.CASCADE, related_name="generations")
    user = models.ForeignKey("accounts.User", on_delete=models.PROTECT, related_name="generations")
    product = models.ForeignKey("products.Product", on_delete=models.PROTECT, related_name="generations")
    mode = models.CharField(max_length=20, choices=GenerationMode.choices)
    scene_template = models.ForeignKey(SceneTemplate, null=True, blank=True, on_delete=models.PROTECT, related_name="generations")
    generation_rule = models.ForeignKey(GenerationRule, null=True, blank=True, on_delete=models.PROTECT, related_name="generations")
    status = models.CharField(max_length=24, choices=GenerationStatus.choices, default=GenerationStatus.CREATED)
    failure_type = models.CharField(max_length=20, choices=FailureType.choices, blank=True)
    provider = models.CharField(max_length=40, default="OPENAI")
    model = models.CharField(max_length=80, blank=True)
    final_prompt = models.TextField(blank=True)
    configuration_snapshot = models.JSONField(default=dict, blank=True)
    input_tokens = models.PositiveIntegerField(null=True, blank=True)
    output_tokens = models.PositiveIntegerField(null=True, blank=True)
    api_cost_usd = models.DecimalField(max_digits=12, decimal_places=6, null=True, blank=True)
    credit_cost = models.PositiveIntegerField(default=1)
    retry_count = models.PositiveSmallIntegerField(default=0)
    idempotency_key = models.CharField(max_length=100)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    error_code = models.CharField(max_length=100, blank=True)
    error_message = models.TextField(blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["organization", "idempotency_key"], name="uniq_generation_idempotency")
        ]


class GeneratedImage(UUIDTimeStampedModel):
    generation = models.OneToOneField(Generation, on_delete=models.CASCADE, related_name="result_image")
    file = models.ImageField(upload_to="generations/%Y/%m/")
    mime_type = models.CharField(max_length=100, default="image/png")
    width = models.PositiveIntegerField(null=True, blank=True)
    height = models.PositiveIntegerField(null=True, blank=True)
    file_size = models.PositiveBigIntegerField(null=True, blank=True)

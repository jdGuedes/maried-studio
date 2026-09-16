from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.utils import timezone
from django.utils.crypto import get_random_string


class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError("O e-mail é obrigatório.")

        email = self.normalize_email(email)

        user = self.model(
            email=email,
            **extra_fields,
        )

        user.set_password(password)
        user.save(using=self._db)

        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)

        return self._create_user(
            email=email,
            password=password,
            **extra_fields,
        )

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError(
                "Superusuário precisa ter is_staff=True."
            )

        if extra_fields.get("is_superuser") is not True:
            raise ValueError(
                "Superusuário precisa ter is_superuser=True."
            )

        return self._create_user(
            email=email,
            password=password,
            **extra_fields,
        )


class UserRole(models.TextChoices):
    OWNER = "OWNER", "Proprietário"
    ADMIN = "ADMIN", "Administrador"
    MEMBER = "MEMBER", "Membro"


class User(AbstractUser):
    username = None

    email = models.EmailField(
        unique=True
    )

    name = models.CharField(
        max_length=160
    )

    organization = models.ForeignKey(
        "organizations.Organization",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="users",
    )

    role = models.CharField(
        max_length=20,
        choices=UserRole.choices,
        default=UserRole.MEMBER,
    )

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = UserManager()

    def __str__(self):
        return self.email


class AccountRecoverySecurity(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="recovery_security",
    )

    recovery_key_hash = models.CharField(
        max_length=128,
        blank=True,
    )

    security_question_1 = models.CharField(
        max_length=255,
        blank=True,
    )

    security_answer_1_hash = models.CharField(
        max_length=128,
        blank=True,
    )

    security_question_2 = models.CharField(
        max_length=255,
        blank=True,
    )

    security_answer_2_hash = models.CharField(
        max_length=128,
        blank=True,
    )

    configured_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    key_rotated_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    failed_attempts = models.PositiveIntegerField(
        default=0,
    )

    last_failed_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    blocked_until = models.DateTimeField(
        null=True,
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        verbose_name = "account recovery security"
        verbose_name_plural = "account recovery securities"

    @property
    def recovery_key_configured(self):
        return bool(
            self.recovery_key_hash
        )

    @property
    def security_questions_configured(self):
        return bool(
            self.security_question_1
            and self.security_question_2
            and self.security_answer_1_hash
            and self.security_answer_2_hash
        )

    @property
    def recovery_configured(self):
        return (
            self.recovery_key_configured
            and self.security_questions_configured
        )

    @property
    def temporarily_blocked(self):
        return bool(
            self.blocked_until
            and self.blocked_until > timezone.now()
        )

    def __str__(self):
        return f"Recovery security for {self.user_id}"


class AccountRecoveryQuestionChallenge(models.Model):
    id = models.CharField(
        max_length=40,
        primary_key=True,
        editable=False,
    )

    user = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="recovery_question_challenges",
    )

    question_1_id = models.CharField(
        max_length=32,
    )

    question_2_id = models.CharField(
        max_length=32,
    )

    expires_at = models.DateTimeField()

    used_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    def save(self, *args, **kwargs):
        if not self.id:
            self.id = get_random_string(
                40
            )

        super().save(
            *args,
            **kwargs,
        )

    @property
    def is_expired(self):
        return self.expires_at <= timezone.now()

    @property
    def is_used(self):
        return self.used_at is not None

    def __str__(self):
        return f"Recovery challenge {self.pk}"

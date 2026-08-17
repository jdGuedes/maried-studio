from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models


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
# Generated for PAYMENT-004.

import django.db.models.deletion
import uuid
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("billing", "0005_creditpackage_plan_extra_credit_limit_per_cycle_and_more"),
        ("organizations", "0002_organization_stripe_customer_id"),
    ]

    operations = [
        migrations.CreateModel(
            name="PaymentDispute",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "stripe_dispute_id",
                    models.CharField(
                        max_length=255,
                        unique=True,
                    ),
                ),
                (
                    "stripe_payment_intent_id",
                    models.CharField(
                        blank=True,
                        max_length=255,
                    ),
                ),
                (
                    "stripe_charge_id",
                    models.CharField(
                        blank=True,
                        max_length=255,
                    ),
                ),
                (
                    "stripe_customer_id",
                    models.CharField(
                        blank=True,
                        max_length=255,
                    ),
                ),
                (
                    "origin_type",
                    models.CharField(
                        choices=[
                            ("SUBSCRIPTION", "Assinatura"),
                            ("CREDIT_PURCHASE", "Compra de créditos"),
                            ("UNKNOWN", "Desconhecida"),
                        ],
                        default="UNKNOWN",
                        max_length=30,
                    ),
                ),
                (
                    "amount",
                    models.IntegerField(
                        default=0,
                    ),
                ),
                (
                    "currency",
                    models.CharField(
                        blank=True,
                        max_length=3,
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            (
                                "warning_needs_response",
                                "Alerta exige resposta",
                            ),
                            (
                                "warning_under_review",
                                "Alerta em análise",
                            ),
                            ("warning_closed", "Alerta encerrado"),
                            ("needs_response", "Exige resposta"),
                            ("under_review", "Em análise"),
                            ("won", "Ganha"),
                            ("lost", "Perdida"),
                            ("prevented", "Prevenida"),
                        ],
                        max_length=40,
                    ),
                ),
                (
                    "reason",
                    models.CharField(
                        blank=True,
                        max_length=120,
                    ),
                ),
                (
                    "evidence_due_by",
                    models.DateTimeField(
                        blank=True,
                        null=True,
                    ),
                ),
                (
                    "resolved_at",
                    models.DateTimeField(
                        blank=True,
                        null=True,
                    ),
                ),
                (
                    "last_event_id",
                    models.CharField(
                        blank=True,
                        max_length=255,
                    ),
                ),
                (
                    "organization",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="payment_disputes",
                        to="organizations.organization",
                    ),
                ),
                (
                    "related_credit_purchase",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="payment_disputes",
                        to="billing.creditpurchase",
                    ),
                ),
                (
                    "related_subscription",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="payment_disputes",
                        to="billing.subscription",
                    ),
                ),
            ],
            options={
                "ordering": ["-created_at"],
                "indexes": [
                    models.Index(
                        fields=["organization", "status"],
                        name="billing_dispute_org_status",
                    ),
                    models.Index(
                        fields=["stripe_payment_intent_id"],
                        name="billing_dispute_pi",
                    ),
                    models.Index(
                        fields=["stripe_charge_id"],
                        name="billing_dispute_charge",
                    ),
                ],
            },
        ),
    ]

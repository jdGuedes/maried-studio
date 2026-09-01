from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("billing", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="plan",
            name="stripe_product_id",
            field=models.CharField(
                blank=True,
                max_length=255,
                null=True,
                unique=True,
            ),
        ),
        migrations.AddField(
            model_name="plan",
            name="stripe_price_id",
            field=models.CharField(
                blank=True,
                max_length=255,
                null=True,
                unique=True,
            ),
        ),
        migrations.AddField(
            model_name="plan",
            name="stripe_price_signature",
            field=models.CharField(
                blank=True,
                max_length=80,
            ),
        ),
        migrations.AddField(
            model_name="plan",
            name="stripe_synced_at",
            field=models.DateTimeField(
                blank=True,
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="plan",
            name="stripe_sync_error",
            field=models.TextField(
                blank=True,
            ),
        ),
    ]

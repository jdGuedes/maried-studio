from rest_framework import serializers

from .models import CreditWallet


class CreditWalletSerializer(
    serializers.ModelSerializer
):
    available_balance = (
        serializers.IntegerField(
            read_only=True
        )
    )

    available_plan_balance = (
        serializers.IntegerField(
            read_only=True
        )
    )

    available_purchased_balance = (
        serializers.IntegerField(
            read_only=True
        )
    )

    total_balance = (
        serializers.IntegerField(
            read_only=True
        )
    )

    class Meta:
        model = CreditWallet

        fields = [
            "id",

            # Compatibilidade
            "balance",
            "reserved_balance",

            # Separação real
            "plan_balance",
            "purchased_balance",

            "plan_reserved_balance",
            "purchased_reserved_balance",

            # Disponíveis
            "available_plan_balance",
            "available_purchased_balance",
            "available_balance",
            "total_balance",

            "created_at",
            "updated_at",
        ]

        read_only_fields = fields
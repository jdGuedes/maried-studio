from rest_framework import serializers


class DashboardPeriodSerializer(
    serializers.Serializer
):
    count = serializers.IntegerField()

    start_date = serializers.DateField()

    end_date = serializers.DateField()


class DashboardRecentGenerationSerializer(
    serializers.Serializer
):
    id = serializers.UUIDField()

    product_id = serializers.UUIDField()

    product_name = serializers.CharField()

    category = serializers.CharField()

    mode = serializers.CharField()

    mode_label = serializers.CharField()

    style_name = serializers.CharField(
        allow_null=True
    )

    image_url = serializers.CharField(
        allow_null=True
    )

    created_at = serializers.DateTimeField()


class DashboardSerializer(
    serializers.Serializer
):
    available_credits = (
        serializers.IntegerField()
    )

    products = (
        DashboardPeriodSerializer()
    )

    generations = (
        DashboardPeriodSerializer()
    )

    recent_generations = (
        DashboardRecentGenerationSerializer(
            many=True
        )
    )
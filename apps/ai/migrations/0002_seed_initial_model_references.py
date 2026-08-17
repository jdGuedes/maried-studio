from django.db import migrations


MODEL_REFERENCES = [
    {
        "code": "MODEL_01",
        "name": "Pele clara e cabelo loiro",
        "slug": "light-skin-blonde",
        "description": (
            "Mulher de 25 a 28 anos, pele clara, cabelo loiro."
        ),
        "prompt_instruction": (
            "Use uma mulher de 25 a 28 anos, pele clara e cabelo loiro "
            "como referencia visual controlada da modelo."
        ),
        "skin_tone": "pele clara",
        "hair_color": "cabelo loiro",
        "age_range": "25 a 28 anos",
        "sort_order": 10,
    },
    {
        "code": "MODEL_02",
        "name": "Pele clara e cabelo preto",
        "slug": "light-skin-black-hair",
        "description": (
            "Mulher de 25 a 28 anos, pele clara, cabelo preto."
        ),
        "prompt_instruction": (
            "Use uma mulher de 25 a 28 anos, pele clara e cabelo preto "
            "como referencia visual controlada da modelo."
        ),
        "skin_tone": "pele clara",
        "hair_color": "cabelo preto",
        "age_range": "25 a 28 anos",
        "sort_order": 20,
    },
    {
        "code": "MODEL_03",
        "name": "Pele clara e cabelo ruivo",
        "slug": "light-skin-red-hair",
        "description": (
            "Mulher de 25 a 28 anos, pele clara, cabelo ruivo."
        ),
        "prompt_instruction": (
            "Use uma mulher de 25 a 28 anos, pele clara e cabelo ruivo "
            "como referencia visual controlada da modelo."
        ),
        "skin_tone": "pele clara",
        "hair_color": "cabelo ruivo",
        "age_range": "25 a 28 anos",
        "sort_order": 30,
    },
    {
        "code": "MODEL_04",
        "name": "Pele negra e cabelo escuro",
        "slug": "black-skin-dark-hair",
        "description": (
            "Mulher de 25 a 28 anos, pele negra, cabelo escuro."
        ),
        "prompt_instruction": (
            "Use uma mulher de 25 a 28 anos, pele negra e cabelo escuro "
            "como referencia visual controlada da modelo."
        ),
        "skin_tone": "pele negra",
        "hair_color": "cabelo escuro",
        "age_range": "25 a 28 anos",
        "sort_order": 40,
    },
]


def seed_model_references(
    apps,
    schema_editor,
):
    model_reference = apps.get_model(
        "ai",
        "ModelReference",
    )

    for item in MODEL_REFERENCES:
        model_reference.objects.update_or_create(
            code=item["code"],
            defaults={
                **item,
                "is_active": True,
            },
        )


def unseed_model_references(
    apps,
    schema_editor,
):
    model_reference = apps.get_model(
        "ai",
        "ModelReference",
    )

    model_reference.objects.filter(
        code__in=[
            item["code"]
            for item in MODEL_REFERENCES
        ],
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        (
            "ai",
            "0001_initial",
        ),
    ]

    operations = [
        migrations.RunPython(
            seed_model_references,
            unseed_model_references,
        ),
    ]

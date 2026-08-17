from django.core.management.base import BaseCommand

from apps.ai.models import (
    ModelReference,
)


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


class Command(
    BaseCommand
):
    help = (
        "Cria ou atualiza a biblioteca inicial de ModelReference."
    )

    def handle(
        self,
        *args,
        **options,
    ):
        for item in MODEL_REFERENCES:
            ModelReference.objects.update_or_create(
                code=item["code"],
                defaults={
                    **item,
                    "is_active": True,
                },
            )

        self.stdout.write(
            self.style.SUCCESS(
                "ModelReferences iniciais criadas/atualizadas."
            )
        )

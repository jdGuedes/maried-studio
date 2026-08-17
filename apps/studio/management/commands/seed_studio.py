from django.core.management.base import BaseCommand

from apps.products.models import ProductCategory
from apps.studio.models import GenerationMode, GenerationRule, PreservationRule, SceneTemplate


RULES = {
    ProductCategory.EARRING: {
        GenerationMode.INSTAGRAM: ("PRODUCT_CLOSE_UP", "", "Keep the earrings fully visible in a commercial jewelry composition."),
        GenerationMode.MODEL: ("PORTRAIT_BUST", "ears and face", "Place the earrings naturally on the model's ears and keep them clearly visible."),
        GenerationMode.BODY_DETAIL: ("CLOSE_UP", "ear and side of face", "Hair must not cover the jewelry; preserve natural scale relative to the ear."),
        GenerationMode.STILL: ("CATALOG_PRODUCT", "", "Isolate the product and preserve exact geometry, components and proportions."),
    },
    ProductCategory.NECKLACE: {
        GenerationMode.INSTAGRAM: ("PRODUCT_CLOSE_UP", "", "Show the complete necklace with chain and pendant clearly visible."),
        GenerationMode.MODEL: ("UPPER_BODY", "neck and upper torso", "Place the necklace naturally around the neck as part of a complete styled look."),
        GenerationMode.BODY_DETAIL: ("CLOSE_UP", "neck, clavicle and upper chest", "The necklace must be the visual protagonist; show pendant, chain, finish and realistic drape."),
        GenerationMode.STILL: ("CATALOG_PRODUCT", "", "Show the complete necklace isolated, preserving chain-to-pendant proportions."),
    },
    ProductCategory.RING: {
        GenerationMode.INSTAGRAM: ("MACRO_PRODUCT", "", "Create a premium macro product composition with the ring as the protagonist."),
        GenerationMode.MODEL: ("LIFESTYLE_MODEL", "hand and model", "The ring must be perceptible and naturally worn as part of the model composition."),
        GenerationMode.BODY_DETAIL: ("MACRO_HAND", "hand and fingers", "Use anatomically natural hands and fingers. Show the ring sharply on one finger at realistic scale."),
        GenerationMode.STILL: ("CATALOG_PRODUCT", "", "Isolate the ring and preserve exact setting, stones, band geometry and proportions."),
    },
    ProductCategory.BRACELET: {
        GenerationMode.INSTAGRAM: ("PRODUCT_CLOSE_UP", "", "Create a commercial composition with the bracelet completely readable."),
        GenerationMode.MODEL: ("LIFESTYLE_MODEL", "wrist and upper body", "Place the bracelet naturally on the wrist within a lifestyle/model composition."),
        GenerationMode.BODY_DETAIL: ("CLOSE_UP", "wrist and forearm", "Keep the bracelet fully visible, sharply focused and naturally fitted around the wrist."),
        GenerationMode.STILL: ("CATALOG_PRODUCT", "", "Isolate the bracelet and preserve its shape, clasp, components and proportions."),
    },
    ProductCategory.ANKLET: {
        GenerationMode.INSTAGRAM: ("PRODUCT_CLOSE_UP", "", "Create a refined commercial product composition keeping the anklet recognizable."),
        GenerationMode.MODEL: ("LIFESTYLE_MODEL", "ankle and lower leg", "Show natural use of the anklet within a lifestyle/model composition."),
        GenerationMode.BODY_DETAIL: ("CLOSE_UP", "ankle and lower leg", "Focus on the anklet applied to the ankle with realistic scale, drape and clear component details."),
        GenerationMode.STILL: ("CATALOG_PRODUCT", "", "Isolate the anklet and preserve full length ratio, clasp, charms and construction."),
    },
}

UNIVERSAL_PRESERVATION = [
    (10, "PRESERVE_GEOMETRY", "Preserve the exact geometry and design of the uploaded jewelry."),
    (20, "PRESERVE_METAL_COLOR", "Preserve the original metal color and finish; do not turn gold into silver or silver into gold."),
    (30, "PRESERVE_STONES", "Preserve the exact number, position, shape and colors of stones."),
    (40, "NO_EXTRA_COMPONENTS", "Do not add, remove, duplicate or invent jewelry components."),
    (50, "PRESERVE_PROPORTIONS", "Preserve the product's relative proportions and realistic scale."),
    (60, "NO_TEXT", "Do not add text, labels, logos, watermarks or invented branding."),
]

TEMPLATES = [
    ("Minimal", "minimal", GenerationMode.INSTAGRAM, "A clean premium minimal jewelry scene, restrained props, soft studio light, elegant neutral surface, product in clear focus."),
    ("Mármore Claro", "light-marble", GenerationMode.INSTAGRAM, "A refined light warm marble jewelry scene, soft diffused commercial lighting, controlled reflections and natural contact shadow."),
    ("Veludo", "velvet", GenerationMode.INSTAGRAM, "A premium velvet jewelry setting with restrained composition, rich tactile background and controlled luxury lighting."),
    ("Editorial", "editorial", GenerationMode.INSTAGRAM, "A sophisticated editorial jewelry composition with modern art direction, commercial lighting and strong product readability."),
    ("Lifestyle", "lifestyle", GenerationMode.INSTAGRAM, "A realistic elegant lifestyle setting with natural premium light and subtle contextual elements, keeping the jewelry as protagonist."),
    ("Luxo", "luxury", GenerationMode.INSTAGRAM, "A refined luxury jewelry campaign environment with premium materials, elegant lighting and restrained styling."),
]


class Command(BaseCommand):
    help = "Cria a Matriz Fotográfica V1, regras de preservação e templates iniciais."

    def handle(self, *args, **options):
        for priority, rule_type, instruction in UNIVERSAL_PRESERVATION:
            PreservationRule.objects.update_or_create(
                category="", rule_type=rule_type,
                defaults={"instruction": instruction, "priority": priority, "is_active": True},
            )

        for category, mode_map in RULES.items():
            for mode, (framing, body_area, placement) in mode_map.items():
                GenerationRule.objects.update_or_create(
                    category=category, generation_mode=mode,
                    defaults={
                        "framing": framing,
                        "body_area": body_area,
                        "placement_instruction": placement,
                        "product_priority": "MAXIMUM",
                        "body_priority": "MEDIUM" if body_area else "LOW",
                        "background_priority": "LOW",
                        "product_visibility": "FULL",
                        "detail_level": "MAXIMUM",
                        "additional_rules": [],
                        "is_active": True,
                    },
                )

        categories = [c for c, _ in ProductCategory.choices]
        for name, slug, mode, prompt in TEMPLATES:
            for category in categories:
                SceneTemplate.objects.update_or_create(
                    slug=slug, generation_mode=mode, category=category, version=1,
                    defaults={
                        "name": name,
                        "prompt_template": prompt,
                        "is_active": True,
                        "sort_order": 0,
                    },
                )
        self.stdout.write(self.style.SUCCESS("Matriz Fotográfica V1 criada/atualizada."))

from apps.studio.models import PreservationRule


class PromptEngine:
    """
    Motor central responsável por montar os prompts enviados
    ao modelo de geração/edição de imagens.

    Estrutura:
    BASE
    + MODO
    + CATEGORIA/MODO
    + REGRA FOTOGRÁFICA
    + CENA
    + PRESERVAÇÃO
    + RESTRIÇÕES FINAIS
    """

    BASE_INSTRUCTION = (
        "Use the uploaded original jewelry image as the mandatory, absolute "
        "and authoritative product reference. The jewelry shown in the reference "
        "is the exact physical product that must appear in the final image. "
        "Preserve its identity, geometry, proportions, materials, colors, stones, "
        "settings, textures, finishes, closures, pendants, decorative elements "
        "and all visible manufacturing details. "
        "Create exactly one final commercial image."
    )

    # =========================================================
    # REGRAS GERAIS POR MODO
    # =========================================================

    MODE_INSTRUCTIONS = {
        "STILL": (
            "Create a premium professional still-life product photograph "
            "for luxury jewelry e-commerce.\n\n"

            "ABSOLUTE PRODUCT FIDELITY:\n"
            "Use exclusively the uploaded original jewelry as the absolute "
            "reference. Preserve 100% of the physical product. "
            "The editing must consist only of professional photographic "
            "improvements. The jewelry itself must not be redesigned.\n\n"

            "DO NOT MODIFY:\n"
            "- shape\n"
            "- design\n"
            "- thickness\n"
            "- actual size\n"
            "- proportions\n"
            "- chain\n"
            "- closures\n"
            "- pendants\n"
            "- stone settings\n"
            "- quantity of stones\n"
            "- stone cuts\n"
            "- metal texture\n"
            "- plating color\n"
            "- finish\n"
            "- position of components\n"
            "- original structural details\n"
            "- manufacturing details\n\n"

            "PHOTOGRAPHIC OBJECTIVE:\n"
            "Transform the source photograph into a high-end professional "
            "still image suitable for premium jewelry e-commerce. "
            "Improve only photography, lighting, exposure, clarity, "
            "background and presentation.\n\n"

            "DETAIL AND SHARPNESS:\n"
            "Produce professional sharpness and preserve microdetails. "
            "Every visible stone setting, prong, contour, opening, edge and "
            "manufacturing detail must remain clearly defined. "
            "Maintain a realistic photographic appearance without plastic, "
            "illustrated or artificial AI-rendered surfaces.\n\n"

            "LIGHTING:\n"
            "Correct and improve the lighting using uniform professional "
            "studio illumination. Use soft natural shadows, elegant contrast "
            "and controlled highlights. Avoid blown highlights and excessively "
            "dark areas. Enhance the natural three-dimensional volume of the "
            "piece without changing its geometry.\n\n"

            "STONES:\n"
            "Preserve the exact stones from the reference image. "
            "Use delicate brilliance, natural reflections, realistic "
            "transparency, clear contours and subtle studio-light sparkle. "
            "Never exaggerate brilliance or invent reflections that alter "
            "the appearance of the stones.\n\n"

            "METAL:\n"
            "Preserve the exact original metal and plating color. "
            "For gold-tone jewelry, maintain sophisticated realistic metallic "
            "reflections without excessive saturation, orange coloration or "
            "artificial shine. Do not beautify or reconstruct the metal.\n\n"

            "BACKGROUND:\n"
            "Use a pure white #FFFFFF background. "
            "No texture. No objects. No decoration. "
            "No unwanted reflections. No environmental elements.\n\n"

            "PRODUCT ISOLATION:\n"
            "Remove completely any mannequin, holder, pedestal, hand, body, "
            "fabric, decorative object or support visible around the jewelry. "
            "Keep only the jewelry itself.\n\n"

            "CUTOUT QUALITY:\n"
            "Use an extremely clean product cutout with natural precise edges. "
            "No jagged edges, halos or artificial borders.\n\n"

            "PHOTOGRAPHIC CORRECTIONS:\n"
            "Correct white balance, exposure, contrast, color temperature, "
            "sharpness, noise, microcontrast and stone definition while "
            "preserving the exact appearance of the physical product.\n\n"

            "FINAL RESULT:\n"
            "The final image must look like authentic premium studio jewelry "
            "photography for e-commerce: sophisticated, elegant, highly detailed "
            "and realistic. The jewelry must remain the exact same product "
            "shown in the uploaded reference."
        ),

        "INSTAGRAM": (
            "Create a premium social-media commercial photograph. "
            "The jewelry must remain the main visual subject while being "
            "presented inside the selected commercial scene. "
            "The environment may enhance the composition but must never hide, "
            "distort or visually compete with the product. "
            "Use polished advertising photography, realistic lighting and "
            "professional depth of field."
        ),

        "MODEL": (
            "Create a professional fashion and jewelry advertising photograph "
            "showing a model naturally wearing the exact referenced jewelry. "
            "Respect the correct anatomical placement and realistic scale of "
            "the piece. The model, clothing, pose and environment should create "
            "a commercial composition while keeping the jewelry clearly "
            "identifiable."
        ),

        "BODY_DETAIL": (
            "Create a professional close-up jewelry photograph showing the "
            "exact referenced product correctly applied to the appropriate "
            "body area. The jewelry is the absolute visual protagonist. "
            "Use the body only to demonstrate realistic scale, placement and fit. "
            "The product and immediate body area must be sharply focused. "
            "Do not reinterpret the jewelry while applying it to the body."
        ),
    }

    # =========================================================
    # REGRAS ESPECIALIZADAS:
    # CATEGORIA + MODO
    # =========================================================

    CATEGORY_MODE_INSTRUCTIONS = {
        ("EARRING", "BODY_DETAIL"): (
            "EARRING BODY-DETAIL MASTER REQUIREMENTS:\n\n"

            "ABSOLUTE FIDELITY:\n"
            "Use exclusively the uploaded original earring as the absolute "
            "and authoritative visual reference. "
            "The earring must remain exactly the same physical product.\n\n"

            "Treat the referenced earring as immutable visual geometry. "
            "Do not recreate, reinterpret, redesign, beautify, simplify, "
            "symmetrize or reconstruct the jewelry itself.\n\n"

            "DO NOT MODIFY:\n"
            "- shape\n"
            "- actual size\n"
            "- thickness\n"
            "- width\n"
            "- height\n"
            "- proportions\n"
            "- design\n"
            "- curves\n"
            "- openings and negative spaces\n"
            "- texture\n"
            "- finish\n"
            "- metal plating color\n"
            "- gold tone intensity\n"
            "- original shine characteristics\n"
            "- stones\n"
            "- pearls\n"
            "- zirconia\n"
            "- stone cuts\n"
            "- quantity of stones\n"
            "- stone positions\n"
            "- prongs\n"
            "- settings\n"
            "- closures\n"
            "- relief\n"
            "- polish\n"
            "- manufacturing details\n\n"

            "Do not make the metal thicker or thinner. "
            "Do not make the product more symmetrical. "
            "Do not smooth or simplify structural contours. "
            "Do not create stones. "
            "Do not remove stones. "
            "Do not reposition stones. "
            "Do not create a cleaner or idealized version of the earring. "
            "Preserve natural manufacturing characteristics and imperfections.\n\n"

            "REAL SCALE AND PLACEMENT:\n"
            "Place the exact referenced earring naturally on the model's ear "
            "using realistic physical scale. "
            "Do not enlarge, shrink, stretch, compress or deform the product. "
            "Respect the true relationship between the earring and the earlobe. "
            "The placement must follow natural ear anatomy and look physically "
            "wearable.\n\n"

            "Generate the model, ear, skin, hair, lighting and environment "
            "around the referenced jewelry. "
            "Do not generate a new jewelry design inspired by the reference.\n\n"

            "MODEL:\n"
            "Use an extremely photogenic Brazilian woman approximately "
            "25 to 35 years old with sophisticated, elegant and natural beauty. "
            "Use realistic healthy skin texture, very light makeup and a "
            "delicate natural expression. Avoid artificial or plastic AI-looking "
            "skin.\n\n"

            "HAIR:\n"
            "Use well-groomed medium-brown straight or slightly wavy hair. "
            "Keep the hair behind the ear so that no part of the jewelry is "
            "hidden.\n\n"

            "COMPOSITION:\n"
            "Use a professional close-up showing only the relevant part of "
            "the face, jawline, ear, neck and hair. "
            "The earring must be the absolute visual protagonist.\n\n"

            "LIGHTING:\n"
            "Use premium luxury-jewelry campaign photography with soft diffused "
            "light, extremely delicate shadows, controlled highlights and "
            "realistic reflections. Do not create blown highlights or artificial "
            "reflections on the jewelry.\n\n"

            "BACKGROUND:\n"
            "Use a neutral light beige, off-white or cream background with "
            "natural depth-of-field blur. No objects or visual distractions.\n\n"

            "FINAL QUALITY:\n"
            "The result must look like a real professional luxury-jewelry "
            "advertising photograph, not a render or illustration. "
            "Preserve realistic skin, metal and stone microdetails. "
            "The jewelry must remain faithful to the exact product that would "
            "be delivered to the customer."
        ),
    }

    # =========================================================
    # CONSTRUÇÃO DO PROMPT FINAL
    # =========================================================

    @classmethod
    def build(
        cls,
        *,
        product,
        mode,
        scene_template,
        generation_rule,
    ):
        rules = (
            PreservationRule.objects
            .filter(is_active=True)
            .filter(
                category__in=[
                    "",
                    product.category,
                ]
            )
            .order_by("priority")
        )

        preservation = "\n".join(
            f"- {rule.instruction}"
            for rule in rules
        )

        additional = "\n".join(
            f"- {rule}"
            for rule in (
                generation_rule.additional_rules or []
            )
        )

        mode_instruction = cls.MODE_INSTRUCTIONS.get(
            mode,
            "",
        )

        category_mode_instruction = (
            cls.CATEGORY_MODE_INSTRUCTIONS.get(
                (
                    product.category,
                    mode,
                ),
                "",
            )
        )

        parts = [
            cls.BASE_INSTRUCTION,

            f"PRODUCT CATEGORY: {product.category}",

            f"GENERATION MODE: {mode}",

            (
                "MODE REQUIREMENTS:\n"
                + mode_instruction
                if mode_instruction
                else ""
            ),

            (
                "CATEGORY + MODE REQUIREMENTS:\n"
                + category_mode_instruction
                if category_mode_instruction
                else ""
            ),

            (
                f"FRAMING: "
                f"{generation_rule.framing}"
            ),

            (
                f"BODY AREA: "
                f"{generation_rule.body_area}"
                if generation_rule.body_area
                else ""
            ),

            (
                f"PLACEMENT: "
                f"{generation_rule.placement_instruction}"
                if generation_rule.placement_instruction
                else ""
            ),

            (
                "SCENE REQUIREMENTS:\n"
                + scene_template.prompt_template
                if scene_template
                else
                "Use a clean professional commercial composition."
            ),

            (
                "PRESERVATION RULES:\n"
                + preservation
                if preservation
                else ""
            ),

            (
                "ADDITIONAL RULES:\n"
                + additional
                if additional
                else ""
            ),

            (
                "FINAL RESTRICTIONS:\n"
                "- Return exactly one finished image.\n"
                "- Do not add text.\n"
                "- Do not add logos.\n"
                "- Do not add watermarks.\n"
                "- Do not duplicate the jewelry.\n"
                "- Do not invent additional jewelry components.\n"
                "- Do not remove existing jewelry components.\n"
                "- Do not redesign the referenced product."
            ),
        ]

        return "\n\n".join(
            part
            for part in parts
            if part
        )
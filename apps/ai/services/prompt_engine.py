from apps.studio.models import PreservationRule


class PromptTooLongError(ValueError):
    """
    Erro disparado antes da chamada ao provider quando o prompt
    final ultrapassa o limite máximo aceito pelo provider.
    """
    pass


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

    PROVIDER_MAX_PROMPT_LENGTH = 32000

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
            "Create a premium social-media commercial photograph.\n\n"

            "PRODUCT IDENTITY PRIORITY:\n"
            "The uploaded jewelry is the exact physical product and must remain "
            "visually faithful to the uploaded reference.\n\n"

            "The selected SceneTemplate controls ONLY the environment, surface, "
            "lighting, atmosphere, shadows, depth and photographic composition.\n\n"

            "The SceneTemplate has ZERO authority to modify, reconstruct, "
            "redesign, beautify or reinterpret the jewelry.\n\n"

            "Generate the selected scene AROUND the exact referenced product. "
            "Never regenerate or alter the product merely to make it fit the scene.\n\n"

            "Do not add jewelry components that are not visually confirmed "
            "in the uploaded reference.\n"
            "Do not remove visible jewelry components.\n"
            "Do not infer hidden hardware or complete uncertain product geometry.\n\n"

            "Preserve the jewelry's exact visible design, geometry, proportions, "
            "stones, component sequence, metal, plating color, texture, finish "
            "and manufacturing characteristics.\n\n"

            "The jewelry must remain the main visual subject. "
            "The environment may enhance the composition but must never hide, "
            "distort or visually compete with the product.\n\n"

            "If scene aesthetics conflict with jewelry fidelity, simplify or "
            "adapt the scene and preserve the exact jewelry.\n\n"
            
            "Use polished advertising photography and realistic professional lighting.\n\n"

            "PRODUCT FOCUS:\n"
            "Keep the complete jewelry and all important components optically sharp "
            "and commercially readable. Use sufficient depth of field to keep chains, "
            "links, stones, pendants, clasps and decorative elements in focus. "
            "Apply depth-of-field blur primarily to the environment, never to important "
            "parts of the jewelry."),
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

            "ABSOLUTE PRIORITY — PRODUCT FIDELITY:\n"
            "The uploaded original earring image is the mandatory, absolute "
            "and authoritative product reference.\n"
            "It is NOT a design reference, style reference, approximation "
            "or inspiration.\n"
            "It represents the exact physical product that must appear "
            "in the final photograph.\n\n"

            "Treat the visible jewelry geometry, component relationships "
            "and manufacturing details as IMMUTABLE PRODUCT INFORMATION.\n\n"

            "Generate the model, ear, skin, hair, lighting, background and "
            "photographic environment AROUND the referenced jewelry.\n"
            "Do NOT generate a new earring based on semantic understanding "
            "of the reference.\n\n"

            "If any instruction about beauty, composition, lighting, model, "
            "symmetry or photographic attractiveness conflicts with product "
            "fidelity, PRODUCT FIDELITY ALWAYS HAS ABSOLUTE PRIORITY.\n\n"

            "PRODUCT IDENTITY LOCK:\n"
            "The final earring must remain visually identical to the exact "
            "product shown in the uploaded reference.\n\n"

            "Do not recreate, reinterpret, redesign, beautify, idealize, "
            "simplify, symmetrize, reconstruct or enhance the jewelry design.\n\n"

            "Preserve exactly:\n"
            "- outer silhouette\n"
            "- internal geometry\n"
            "- shape\n"
            "- actual physical size\n"
            "- thickness\n"
            "- width\n"
            "- height\n"
            "- proportions\n"
            "- curves\n"
            "- contours\n"
            "- openings and negative spaces\n"
            "- relief\n"
            "- metal thickness\n"
            "- texture\n"
            "- surface finish\n"
            "- plating color\n"
            "- gold tone\n"
            "- original shine characteristics\n"
            "- stone count\n"
            "- stone positions\n"
            "- relative stone sizes\n"
            "- stone cuts\n"
            "- stone shapes\n"
            "- stone colors\n"
            "- prong count\n"
            "- prong positions\n"
            "- settings\n"
            "- pearls, when present\n"
            "- zirconia, when present\n"
            "- closures\n"
            "- structural connections\n"
            "- manufacturing details\n"
            "- visible natural manufacturing imperfections\n\n"

            "STRICTLY FORBIDDEN:\n"
            "- Do not add stones.\n"
            "- Do not remove stones.\n"
            "- Do not reposition stones.\n"
            "- Do not change stone size relationships.\n"
            "- Do not change stone cuts.\n"
            "- Do not change prongs or settings.\n"
            "- Do not fill openings or negative spaces.\n"
            "- Do not create new openings.\n"
            "- Do not make the metal thicker or thinner.\n"
            "- Do not change the outer silhouette.\n"
            "- Do not make the product more symmetrical.\n"
            "- Do not smooth manufacturing relief.\n"
            "- Do not simplify decorative details.\n"
            "- Do not intensify or alter the plating color.\n"
            "- Do not invent reflections that change the product appearance.\n"
            "- Do not create a cleaner, richer or more luxurious version "
            "of the product.\n\n"

            "Natural manufacturing characteristics visible in the reference "
            "must remain visible. The objective is accurate product "
            "representation, not product redesign.\n\n"

            "REAL PHYSICAL SCALE:\n"
            "Apply the exact referenced earring to the model's ear using "
            "realistic physical scale.\n\n"

            "Do not enlarge the jewelry to make it more prominent.\n"
            "Do not shrink it.\n"
            "Do not stretch it.\n"
            "Do not compress it.\n"
            "Do not deform it to fit the ear.\n\n"

            "Preserve the true width-to-height ratio and the realistic "
            "relationship between the earring and the earlobe.\n\n"

            "A small earring must remain visually small.\n"
            "A large earring must naturally occupy the appropriate area "
            "of the earlobe without changing its dimensions.\n\n"

            "ANATOMICAL PLACEMENT:\n"
            "Position the jewelry naturally according to real human ear "
            "anatomy, as if the exact physical earring had actually been "
            "placed on the model for a professional photoshoot.\n\n"

            "The attachment point must be physically plausible.\n"
            "The earring must not float, merge with the skin, penetrate "
            "incorrectly into the ear or appear pasted onto the photograph.\n\n"

            "Do not alter the jewelry geometry to improve anatomical fit.\n"
            "Adapt the generated ear and photographic composition around "
            "the immutable jewelry instead.\n\n"

            "MODEL:\n"
            "Use the selected ModelReference only to define human visual "
            "characteristics such as skin tone, hair color, age range and "
            "overall model appearance.\n\n"

            "The ModelReference must NEVER override, influence or modify "
            "the jewelry design, geometry, color, stones, scale or details.\n\n"

            "Use a sophisticated, natural and photorealistic female model "
            "with realistic skin texture, subtle makeup and an elegant "
            "commercial appearance.\n\n"

            "HAIR:\n"
            "Keep the hair naturally positioned behind the relevant ear "
            "so the complete earring remains visible.\n"
            "Hair must not cover important product details.\n\n"

            "COMPOSITION:\n"
            "Create a professional close-up luxury jewelry photograph.\n"
            "Show only the relevant portion of the face, ear, jawline, "
            "neck and hair.\n\n"

            "The earring is the absolute visual protagonist.\n"
            "The ear and model exist primarily to demonstrate realistic "
            "scale, placement and use.\n\n"

            "Keep both the jewelry and immediate ear area sharply focused.\n\n"

            "LIGHTING:\n"
            "Use premium luxury-jewelry campaign photography with soft, "
            "diffused professional light.\n"
            "Use delicate natural shadows and controlled highlights.\n\n"

            "Do not use blown highlights.\n"
            "Do not create artificial metallic shine.\n"
            "Do not change stone appearance through excessive sparkle.\n"
            "Do not use lighting to hide or alter product details.\n\n"

            "Metal and stones must retain realistic photographic reflections "
            "consistent with the exact referenced product.\n\n"

            "BACKGROUND:\n"
            "Use a clean neutral light beige, off-white or cream background.\n"
            "Use subtle natural depth-of-field blur.\n"
            "No objects.\n"
            "No text.\n"
            "No distracting visual elements.\n\n"

            "PHOTOREALISM AND QUALITY:\n"
            "The result must look like an authentic professional luxury "
            "jewelry campaign photograph.\n\n"

            "Use realistic skin texture, natural hair, photographic depth, "
            "professional sharpness and preserved jewelry microdetails.\n\n"

            "No illustration appearance.\n"
            "No CGI appearance.\n"
            "No plastic skin.\n"
            "No artificial jewelry rendering.\n\n"

            "FINAL PRODUCT VERIFICATION:\n"
            "Before producing the finished image, visually compare the "
            "earring in the composition against the uploaded original "
            "reference.\n\n"

            "Verify that ALL of the following remain unchanged:\n"
            "- outer silhouette\n"
            "- internal geometry\n"
            "- width-to-height ratio\n"
            "- number of stones\n"
            "- position of every visible stone\n"
            "- relative sizes of stones\n"
            "- stone cuts and shapes\n"
            "- prong positions\n"
            "- openings and negative spaces\n"
            "- metal thickness\n"
            "- relief and decorative contours\n"
            "- plating color\n"
            "- component proportions\n"
            "- manufacturing characteristics\n\n"

            "If any jewelry detail differs from the uploaded reference, "
            "preserve the reference product instead of the generated "
            "interpretation.\n\n"

            "FINAL REQUIREMENT:\n"
            "The final photograph must give the impression that the exact "
            "physical earring from the uploaded reference was genuinely "
            "photographed on the selected model during a professional "
            "luxury-jewelry photoshoot.\n"
            "The model and photography may be generated. "
            "The jewelry identity must not be."
        ),

        ("NECKLACE", "BODY_DETAIL"): (
            "NECKLACE BODY-DETAIL MASTER REQUIREMENTS:\n\n"

            "ABSOLUTE PRIORITY — PRODUCT FIDELITY:\n"
            "Use exclusively the uploaded original necklace image as the "
            "mandatory, absolute and authoritative product reference.\n"
            "It is NOT a design reference, style reference, approximation "
            "or inspiration.\n"
            "It represents the exact physical product that must appear "
            "in the final photograph.\n\n"

            "Treat the necklace, chain, links, pendant, connectors, clasp, "
            "stones and every visible component as IMMUTABLE PRODUCT "
            "INFORMATION.\n\n"

            "Generate the model, neck, collarbone, skin, hair, clothing, "
            "lighting, background and photographic environment AROUND "
            "the referenced necklace.\n"
            "Do NOT generate a new necklace based on semantic understanding "
            "of the reference.\n\n"

            "If beauty, composition, styling, symmetry, lighting or model "
            "appearance conflicts with product fidelity, PRODUCT FIDELITY "
            "ALWAYS HAS ABSOLUTE PRIORITY.\n\n"

            "PRODUCT IDENTITY LOCK:\n"
            "The final necklace must remain visually identical to the exact "
            "physical product shown in the uploaded reference.\n\n"

            "Do not recreate, reinterpret, redesign, beautify, idealize, "
            "simplify, symmetrize or reconstruct the necklace.\n\n"

            "Preserve exactly:\n"
            "- complete necklace design\n"
            "- chain structure\n"
            "- chain thickness\n"
            "- link shape\n"
            "- link size relationships\n"
            "- link spacing\n"
            "- chain texture\n"
            "- visible chain length relationships\n"
            "- outer silhouette\n"
            "- proportions\n"
            "- curves\n"
            "- connectors\n"
            "- attachment points\n"
            "- pendant, when present\n"
            "- pendant shape\n"
            "- pendant dimensions\n"
            "- pendant orientation\n"
            "- pendant-to-chain proportion\n"
            "- pendant attachment structure\n"
            "- stones\n"
            "- stone count\n"
            "- stone positions\n"
            "- relative stone sizes\n"
            "- stone cuts\n"
            "- prongs\n"
            "- settings\n"
            "- pearls, when present\n"
            "- zirconia, when present\n"
            "- decorative elements\n"
            "- clasp structure when visible\n"
            "- metal thickness\n"
            "- relief\n"
            "- texture\n"
            "- surface finish\n"
            "- plating color\n"
            "- gold tone intensity\n"
            "- original shine characteristics\n"
            "- manufacturing details\n"
            "- visible natural manufacturing imperfections\n\n"

            "STRICTLY FORBIDDEN:\n"
            "- Do not replace the chain with another chain style.\n"
            "- Do not make the chain thicker or thinner.\n"
            "- Do not change the link design.\n"
            "- Do not add or remove decorative components.\n"
            "- Do not redesign the pendant.\n"
            "- Do not enlarge the pendant for visual emphasis.\n"
            "- Do not shrink the pendant.\n"
            "- Do not change the pendant-to-chain proportion.\n"
            "- Do not add stones.\n"
            "- Do not remove stones.\n"
            "- Do not reposition stones.\n"
            "- Do not change stone cuts or shapes.\n"
            "- Do not modify prongs or settings.\n"
            "- Do not simplify structural connections.\n"
            "- Do not make the necklace more symmetrical than the product.\n"
            "- Do not smooth manufacturing relief.\n"
            "- Do not intensify or alter the plating color.\n"
            "- Do not create a cleaner, richer or more luxurious version "
            "of the necklace.\n\n"

            "The objective is accurate representation of the product that "
            "will be delivered to the customer, not improvement of its "
            "physical design.\n\n"

            "REAL PHYSICAL SCALE:\n"
            "Apply the exact referenced necklace to the model using "
            "realistic physical scale.\n\n"

            "Do not enlarge or shrink the necklace, chain or pendant.\n"
            "Do not stretch the chain to fill the composition.\n"
            "Do not compress it to fit the neckline.\n"
            "Do not alter component dimensions to improve visibility.\n\n"

            "Preserve the realistic relationship between:\n"
            "- necklace and neck\n"
            "- chain and collarbone\n"
            "- pendant and upper chest\n"
            "- pendant and chain\n"
            "- decorative components and human anatomy\n\n"

            "The jewelry must retain believable real-world dimensions "
            "when worn by the model.\n\n"

            "NATURAL DRAPE AND GRAVITY:\n"
            "The necklace must follow natural gravity and physically "
            "plausible jewelry behavior.\n\n"

            "The chain must rest naturally around the neck and collarbone.\n"
            "When a pendant exists, it must hang naturally from its true "
            "attachment point and remain correctly centered according to "
            "the physical construction of the product.\n\n"

            "Do not reshape the necklace to fit the body.\n"
            "Adapt the generated neck, pose and composition around the "
            "immutable jewelry instead.\n\n"

            "Avoid floating chain sections, impossible bends, broken links, "
            "skin penetration, duplicated links or disconnected components.\n\n"

            "ANATOMICAL PLACEMENT:\n"
            "Place the necklace naturally on the model's neck and upper "
            "chest as if the exact physical product had genuinely been "
            "worn during a professional jewelry photoshoot.\n\n"

            "The chain must follow the natural contour of the neck.\n"
            "The necklace must interact realistically with the collarbone "
            "and upper chest without floating or merging into the skin.\n\n"

            "The pendant, when present, must maintain its natural vertical "
            "orientation and realistic resting position.\n\n"

            "MODEL:\n"
            "Use the selected ModelReference only to define human visual "
            "characteristics such as skin tone, hair color, age range and "
            "overall model appearance.\n\n"

            "The ModelReference must NEVER override, influence or modify "
            "the necklace design, chain, pendant, stones, proportions, "
            "scale, metal color or manufacturing details.\n\n"

            "Use a sophisticated, natural and photorealistic female model "
            "with realistic skin texture, subtle makeup and an elegant "
            "commercial appearance.\n\n"

            "HAIR AND CLOTHING:\n"
            "Keep hair positioned so it does not cover the necklace, "
            "chain, pendant or important product details.\n\n"

            "Use minimal neutral clothing only when necessary for the "
            "composition.\n"
            "Clothing must not cover, overlap or visually compete with "
            "the necklace.\n\n"

            "Prefer an unobstructed neck, collarbone and upper-chest area "
            "appropriate for premium jewelry photography.\n\n"

            "COMPOSITION:\n"
            "Create a professional close-up focused on the neck, "
            "collarbones and upper chest.\n\n"

            "A small portion of the lower face may appear when compositionally "
            "appropriate, but the necklace must remain the visual protagonist.\n\n"

            "The entire visually relevant portion of the necklace must remain "
            "visible and understandable.\n"
            "Do not crop important parts of the jewelry merely to create a "
            "more dramatic photograph.\n\n"

            "Keep the necklace and immediate body area sharply focused.\n\n"

            "LIGHTING:\n"
            "Use premium luxury-jewelry campaign photography with soft, "
            "diffused professional light.\n"
            "Use delicate natural shadows and controlled highlights.\n\n"

            "Do not use blown highlights.\n"
            "Do not create artificial metallic shine.\n"
            "Do not use lighting to hide chain details, links, stones, "
            "pendant geometry or manufacturing characteristics.\n\n"

            "Metal and stones must retain realistic photographic reflections "
            "consistent with the exact referenced product.\n\n"

            "BACKGROUND:\n"
            "Use a clean neutral light beige, off-white or cream background.\n"
            "Use subtle natural depth-of-field blur.\n"
            "No objects.\n"
            "No text.\n"
            "No distracting visual elements.\n\n"

            "PHOTOREALISM AND QUALITY:\n"
            "The result must look like an authentic professional luxury "
            "jewelry campaign photograph.\n\n"

            "Use realistic skin texture, photographic depth, professional "
            "sharpness and preserved jewelry microdetails.\n\n"

            "No illustration appearance.\n"
            "No CGI appearance.\n"
            "No plastic skin.\n"
            "No artificial jewelry rendering.\n\n"

            "FINAL PRODUCT VERIFICATION:\n"
            "Before producing the finished image, visually compare the "
            "necklace against the uploaded original reference.\n\n"

            "Verify that ALL of the following remain unchanged:\n"
            "- chain type\n"
            "- chain thickness\n"
            "- link geometry\n"
            "- link relationships\n"
            "- outer silhouette\n"
            "- pendant geometry\n"
            "- pendant-to-chain proportion\n"
            "- pendant attachment\n"
            "- number of stones\n"
            "- stone positions\n"
            "- relative stone sizes\n"
            "- stone cuts and shapes\n"
            "- prongs and settings\n"
            "- decorative components\n"
            "- metal thickness\n"
            "- relief\n"
            "- plating color\n"
            "- component proportions\n"
            "- manufacturing characteristics\n\n"

            "Also verify that the necklace follows natural gravity without "
            "changing its physical construction.\n\n"

            "If any jewelry detail differs from the uploaded reference, "
            "preserve the reference product instead of the generated "
            "interpretation.\n\n"

            "FINAL REQUIREMENT:\n"
            "The final photograph must give the impression that the exact "
            "physical necklace from the uploaded reference was genuinely "
            "photographed on the selected model during a professional "
            "luxury-jewelry photoshoot.\n"
            "The model and photography may be generated. "
            "The jewelry identity must not be."
        ),

        ("RING", "BODY_DETAIL"): (
            "RING BODY-DETAIL MASTER REQUIREMENTS:\n\n"

            "ABSOLUTE PRIORITY — PRODUCT FIDELITY:\n"
            "Use exclusively the uploaded original ring image as the mandatory, "
            "absolute and authoritative product reference. "
            "It is the exact physical product that must appear in the final photograph. "
            "It is NOT a design reference, approximation or inspiration.\n\n"

            "Treat the complete visible geometry of the ring as IMMUTABLE PRODUCT "
            "INFORMATION. Generate the hand, finger, skin, lighting and photographic "
            "environment around the referenced jewelry. Do NOT generate a new ring "
            "based on semantic understanding of the reference.\n\n"

            "If beauty, composition, hand pose, symmetry, lighting or photographic "
            "attractiveness conflicts with product fidelity, PRODUCT FIDELITY ALWAYS "
            "HAS ABSOLUTE PRIORITY.\n\n"

            "PRODUCT IDENTITY LOCK:\n"
            "Preserve exactly:\n"
            "- complete ring design\n"
            "- outer silhouette\n"
            "- band shape\n"
            "- band thickness\n"
            "- band width\n"
            "- visible inner opening\n"
            "- head or centerpiece geometry\n"
            "- centerpiece-to-band proportion\n"
            "- height relationships visible in the reference\n"
            "- curves\n"
            "- contours\n"
            "- openings and negative spaces\n"
            "- stones\n"
            "- exact stone count\n"
            "- stone positions\n"
            "- relative stone sizes\n"
            "- stone shapes and cuts\n"
            "- prongs\n"
            "- settings\n"
            "- decorative elements\n"
            "- structural connections\n"
            "- metal thickness\n"
            "- relief\n"
            "- texture\n"
            "- surface finish\n"
            "- plating color\n"
            "- original shine characteristics\n"
            "- manufacturing details\n"
            "- visible natural manufacturing imperfections\n\n"

            "STRICTLY FORBIDDEN:\n"
            "- Do not redesign the band.\n"
            "- Do not make the band thicker or thinner.\n"
            "- Do not enlarge the centerpiece.\n"
            "- Do not shrink the centerpiece.\n"
            "- Do not change the centerpiece-to-band proportion.\n"
            "- Do not add stones.\n"
            "- Do not remove stones.\n"
            "- Do not reposition stones.\n"
            "- Do not change stone size relationships.\n"
            "- Do not change stone cuts or shapes.\n"
            "- Do not change prongs or settings.\n"
            "- Do not fill openings or negative spaces.\n"
            "- Do not create new decorative elements.\n"
            "- Do not simplify structural details.\n"
            "- Do not make the ring more symmetrical than the reference.\n"
            "- Do not alter the plating color.\n"
            "- Do not create a cleaner or more luxurious redesign.\n\n"

            "REAL PHYSICAL SCALE:\n"
            "Place the exact referenced ring on a realistic human finger using "
            "believable physical scale. Preserve the real relationship between the "
            "ring, band, centerpiece and finger.\n\n"

            "Do not enlarge the ring to make it more visible. "
            "Do not shrink, stretch, compress or deform it. "
            "Do not alter the band geometry to make it fit the generated finger. "
            "Instead, generate an anatomically compatible finger around the immutable "
            "ring geometry.\n\n"

            "ANATOMICAL PLACEMENT:\n"
            "The ring must be naturally worn around one finger, passing around the "
            "finger in a physically plausible way. The band must not float above the "
            "skin, merge into the skin, penetrate incorrectly through the finger or "
            "appear pasted onto the photograph.\n\n"

            "Use one appropriate finger for the primary ring. "
            "Do not duplicate the referenced ring onto multiple fingers. "
            "Do not add additional rings or jewelry unless they are part of the "
            "uploaded product itself.\n\n"

            "RING ORIENTATION:\n"
            "Keep the main decorative face or centerpiece naturally oriented on the "
            "upper visible side of the finger. Preserve the orientation and geometry "
            "of the original product. Do not rotate individual jewelry components "
            "independently merely to improve visibility.\n\n"

            "HAND:\n"
            "Generate a photorealistic, elegant human hand with natural anatomy, "
            "realistic fingers, healthy skin texture and subtle grooming. "
            "The hand exists only to demonstrate scale, fit and use of the ring.\n\n"

            "Use anatomically correct fingers and joints. Avoid malformed, duplicated, "
            "merged or unnatural fingers. Fingernails should be clean, elegant and "
            "natural, with subtle neutral grooming that does not compete with the ring.\n\n"

            "MODEL REFERENCE:\n"
            "Use the selected ModelReference only for compatible human visual "
            "characteristics such as skin tone and general photographic identity. "
            "The ModelReference must NEVER modify the ring design, stones, scale, "
            "geometry, metal or manufacturing details.\n\n"

            "COMPOSITION:\n"
            "Create a professional macro or close-up luxury-jewelry photograph "
            "focused on the hand and the finger wearing the ring. "
            "The ring must be the absolute visual protagonist.\n\n"

            "Use a natural elegant hand pose that clearly shows the ring without "
            "distorting the finger or jewelry. Avoid excessive perspective distortion. "
            "Keep the complete important geometry of the ring visible whenever "
            "physically possible.\n\n"

            "LIGHTING:\n"
            "Use soft diffused premium jewelry photography lighting with delicate "
            "natural shadows and controlled highlights. Preserve realistic reflections "
            "on metal and stones. Do not use blown highlights, artificial sparkle or "
            "lighting that hides structural product details.\n\n"

            "BACKGROUND:\n"
            "Use a clean neutral light beige, off-white or cream background with "
            "subtle natural depth-of-field blur. No objects, text or distractions.\n\n"

            "PHOTOREALISM AND QUALITY:\n"
            "The final image must look like authentic premium jewelry photography. "
            "Preserve realistic skin, fingernails, metal, stones and jewelry "
            "microdetails. No CGI, illustration, plastic skin or artificial jewelry "
            "rendering appearance.\n\n"

            "FINAL PRODUCT VERIFICATION:\n"
            "Before producing the final image, visually compare the ring against the "
            "uploaded original reference. Verify that the band geometry, band thickness, "
            "centerpiece geometry, centerpiece-to-band proportion, stone count, stone "
            "positions, relative stone sizes, cuts, prongs, settings, openings, metal "
            "thickness, relief, plating color and manufacturing characteristics remain "
            "unchanged.\n\n"

            "Also verify that exactly one copy of the referenced product is being worn "
            "naturally on one anatomically correct finger.\n\n"

            "If any jewelry detail differs from the uploaded reference, preserve the "
            "reference product instead of the generated interpretation.\n\n"

            "FINAL REQUIREMENT:\n"
            "The final photograph must give the impression that the exact physical "
            "ring from the uploaded reference was genuinely placed on the model's "
            "finger and professionally photographed. The hand and photography may be "
            "generated. The jewelry identity must not be."
        ),

        ("BRACELET", "BODY_DETAIL"): (
            "BRACELET BODY-DETAIL MASTER REQUIREMENTS:\n\n"

            "ABSOLUTE PRIORITY — PRODUCT FIDELITY:\n"
            "Use exclusively the uploaded original bracelet image as the "
            "mandatory, absolute and authoritative product reference. "
            "It represents the exact physical product that must appear "
            "in the final photograph.\n\n"

            "The uploaded bracelet is NOT a design reference, style reference, "
            "approximation or inspiration.\n"
            "Treat its visible geometry, construction and component relationships "
            "as IMMUTABLE PRODUCT INFORMATION.\n\n"

            "Generate the wrist, hand, skin, model characteristics, lighting, "
            "background and photographic environment AROUND the exact referenced "
            "bracelet.\n"
            "Do NOT generate a new bracelet based on semantic understanding "
            "of the reference.\n\n"

            "If beauty, composition, pose, symmetry, lighting or photographic "
            "attractiveness conflicts with product fidelity, PRODUCT FIDELITY "
            "ALWAYS HAS ABSOLUTE PRIORITY.\n\n"

            "PRODUCT IDENTITY LOCK:\n"
            "The final bracelet must remain visually identical to the exact "
            "physical product shown in the uploaded reference.\n\n"

            "Preserve exactly:\n"
            "- complete bracelet design\n"
            "- outer silhouette\n"
            "- chain structure, when present\n"
            "- link type\n"
            "- link geometry\n"
            "- link thickness\n"
            "- link spacing\n"
            "- component sequence\n"
            "- bracelet width\n"
            "- bracelet thickness\n"
            "- visible length relationships\n"
            "- curves\n"
            "- contours\n"
            "- openings and negative spaces\n"
            "- connectors\n"
            "- attachment points\n"
            "- clasp or closure\n"
            "- centerpiece, when present\n"
            "- centerpiece geometry\n"
            "- charms or pendants, when present\n"
            "- charm count\n"
            "- charm positions\n"
            "- stones\n"
            "- exact stone count\n"
            "- stone positions\n"
            "- relative stone sizes\n"
            "- stone cuts and shapes\n"
            "- prongs\n"
            "- settings\n"
            "- pearls, when present\n"
            "- zirconia, when present\n"
            "- decorative elements\n"
            "- metal thickness\n"
            "- relief\n"
            "- texture\n"
            "- surface finish\n"
            "- plating color\n"
            "- original shine characteristics\n"
            "- manufacturing details\n"
            "- visible natural manufacturing imperfections\n\n"

            "STRICTLY FORBIDDEN:\n"
            "- Do not redesign the bracelet.\n"
            "- Do not replace the chain or link style.\n"
            "- Do not make links thicker or thinner.\n"
            "- Do not change link spacing.\n"
            "- Do not add links merely to fit the wrist.\n"
            "- Do not remove links merely to fit the wrist.\n"
            "- Do not alter the clasp or closure.\n"
            "- Do not add charms or pendants.\n"
            "- Do not remove charms or pendants.\n"
            "- Do not reposition decorative components.\n"
            "- Do not add stones.\n"
            "- Do not remove stones.\n"
            "- Do not reposition stones.\n"
            "- Do not change stone size relationships.\n"
            "- Do not change stone cuts or shapes.\n"
            "- Do not alter prongs or settings.\n"
            "- Do not simplify structural connections.\n"
            "- Do not change metal thickness.\n"
            "- Do not alter the plating color.\n"
            "- Do not create a cleaner, richer or more luxurious redesign.\n\n"

            "REAL PHYSICAL SCALE:\n"
            "Place the exact referenced bracelet naturally around a realistic "
            "human wrist using believable real-world physical scale.\n\n"

            "Do not enlarge the bracelet to make it more visible.\n"
            "Do not shrink it.\n"
            "Do not stretch it.\n"
            "Do not compress it.\n"
            "Do not deform its components to fit the wrist.\n\n"

            "Preserve the realistic relationship between bracelet width, "
            "component size, chain thickness, charms, stones and the human wrist.\n\n"

            "The generated wrist must accommodate the immutable bracelet geometry. "
            "Do not redesign the bracelet to accommodate the generated wrist.\n\n"

            "WRIST FIT:\n"
            "The bracelet must naturally surround the wrist as a real physical "
            "bracelet would.\n\n"

            "It must not appear excessively tight unless that is inherent to the "
            "original product type.\n"
            "It must not float unrealistically far from the skin.\n"
            "It must not merge into or penetrate the skin.\n\n"

            "Preserve a believable amount of natural space between the bracelet "
            "and wrist according to the construction of the jewelry.\n\n"

            "For rigid bracelets or bangles, preserve their rigid geometry.\n"
            "For flexible chain bracelets, preserve natural flexibility without "
            "changing link geometry or component relationships.\n\n"

            "NATURAL DRAPE AND GRAVITY:\n"
            "Respect real gravity and the physical behavior of the bracelet.\n\n"

            "Flexible components must rest naturally around the wrist.\n"
            "Charms or pendants, when present, must hang naturally from their "
            "true attachment points.\n\n"

            "Do not make charms float.\n"
            "Do not force all decorative elements to face the camera if that would "
            "require physically impossible positioning.\n"
            "Do not distort the bracelet to improve composition.\n\n"

            "Avoid broken chains, disconnected links, impossible bends, duplicated "
            "components or unnatural intersections.\n\n"

            "ANATOMICAL PLACEMENT:\n"
            "Place the bracelet around the wrist in a physically plausible position "
            "as if the exact product had genuinely been worn during a professional "
            "jewelry photoshoot.\n\n"

            "The bracelet must follow the natural wrist contour while preserving "
            "its own construction and geometry.\n\n"

            "Do not place the bracelet around fingers, palm or forearm unless the "
            "physical dimensions of the original product naturally require a "
            "slightly higher wrist position.\n\n"

            "HAND AND MODEL:\n"
            "Generate an elegant, photorealistic hand and wrist with natural "
            "anatomy, realistic skin texture and subtle grooming.\n\n"

            "The hand and wrist exist primarily to demonstrate realistic scale, "
            "fit and use of the bracelet.\n\n"

            "Avoid malformed, duplicated or merged fingers and unnatural wrist "
            "anatomy.\n\n"

            "Use the selected ModelReference only for compatible human visual "
            "characteristics such as skin tone and general photographic identity.\n"
            "The ModelReference must NEVER modify the bracelet design, geometry, "
            "scale, stones, metal, links, charms or manufacturing details.\n\n"

            "COMPOSITION:\n"
            "Create a professional close-up or macro luxury-jewelry photograph "
            "focused on the wrist and bracelet.\n\n"

            "The bracelet must be the absolute visual protagonist.\n"
            "Show enough of the hand and wrist to communicate realistic scale "
            "without allowing the body to dominate the composition.\n\n"

            "Use an elegant, relaxed and anatomically natural wrist pose.\n"
            "Avoid excessive perspective distortion.\n\n"

            "Keep the visually important bracelet components clearly visible "
            "whenever physically possible without changing their real orientation.\n\n"

            "LIGHTING:\n"
            "Use premium luxury-jewelry campaign photography with soft diffused "
            "professional light, delicate natural shadows and controlled highlights.\n\n"

            "Do not use blown highlights.\n"
            "Do not create artificial metallic shine.\n"
            "Do not exaggerate stone sparkle.\n"
            "Do not use lighting to hide links, closures, stones, charms or "
            "structural product details.\n\n"

            "Metal and stones must retain realistic photographic reflections "
            "consistent with the exact referenced product.\n\n"

            "BACKGROUND:\n"
            "Use a clean neutral light beige, off-white or cream background "
            "with subtle natural depth-of-field blur.\n"
            "No objects.\n"
            "No text.\n"
            "No visual distractions.\n\n"

            "PHOTOREALISM AND QUALITY:\n"
            "The final image must look like authentic premium jewelry photography.\n"
            "Preserve realistic skin, metal, stones, links, closures, charms and "
            "jewelry microdetails.\n\n"

            "No illustration appearance.\n"
            "No CGI appearance.\n"
            "No plastic skin.\n"
            "No artificial jewelry rendering.\n\n"

            "FINAL PRODUCT VERIFICATION:\n"
            "Before producing the finished image, visually compare the bracelet "
            "against the uploaded original reference.\n\n"

            "Verify that ALL of the following remain unchanged:\n"
            "- bracelet construction\n"
            "- outer silhouette\n"
            "- chain or link type\n"
            "- link geometry\n"
            "- link thickness\n"
            "- component sequence\n"
            "- bracelet width\n"
            "- bracelet thickness\n"
            "- clasp or closure\n"
            "- centerpiece geometry\n"
            "- charm count and positions\n"
            "- stone count\n"
            "- stone positions\n"
            "- relative stone sizes\n"
            "- stone cuts and shapes\n"
            "- prongs and settings\n"
            "- decorative components\n"
            "- metal thickness\n"
            "- relief\n"
            "- plating color\n"
            "- component proportions\n"
            "- manufacturing characteristics\n\n"

            "Also verify that the bracelet naturally surrounds the wrist and follows "
            "real gravity without changing its physical construction.\n\n"

            "If any jewelry detail differs from the uploaded reference, preserve "
            "the reference product instead of the generated interpretation.\n\n"

            "FINAL REQUIREMENT:\n"
            "The final photograph must give the impression that the exact physical "
            "bracelet from the uploaded reference was genuinely placed on the "
            "model's wrist and professionally photographed.\n"
            "The wrist, hand, model and photography may be generated. "
            "The jewelry identity must not be."
        ),

        ("ANKLET", "BODY_DETAIL"): (
            "ANKLET BODY-DETAIL MASTER REQUIREMENTS:\n\n"

            "ABSOLUTE PRIORITY — PRODUCT FIDELITY:\n"
            "Use exclusively the uploaded original anklet image as the "
            "mandatory, absolute and authoritative product reference. "
            "It represents the exact physical product that must appear "
            "in the final photograph.\n\n"

            "The uploaded anklet is NOT a design reference, style reference, "
            "approximation or inspiration.\n"
            "Treat its visible geometry, construction and component relationships "
            "as IMMUTABLE PRODUCT INFORMATION.\n\n"

            "Generate the ankle, foot, skin, model characteristics, lighting, "
            "background and photographic environment AROUND the exact referenced "
            "anklet.\n"
            "Do NOT generate a new anklet based on semantic understanding "
            "of the reference.\n\n"

            "If beauty, composition, pose, symmetry, lighting or photographic "
            "attractiveness conflicts with product fidelity, PRODUCT FIDELITY "
            "ALWAYS HAS ABSOLUTE PRIORITY.\n\n"

            "PRODUCT IDENTITY LOCK:\n"
            "The final anklet must remain visually identical to the exact "
            "physical product shown in the uploaded reference.\n\n"

            "Preserve exactly:\n"
            "- complete anklet design\n"
            "- outer silhouette\n"
            "- chain structure\n"
            "- chain thickness\n"
            "- link type\n"
            "- link geometry\n"
            "- link spacing\n"
            "- component sequence\n"
            "- visible length relationships\n"
            "- width\n"
            "- thickness\n"
            "- curves\n"
            "- contours\n"
            "- connectors\n"
            "- attachment points\n"
            "- clasp or closure\n"
            "- extension chain, when present\n"
            "- charms or pendants, when present\n"
            "- exact charm count\n"
            "- charm positions\n"
            "- charm shapes\n"
            "- centerpiece, when present\n"
            "- stones\n"
            "- exact stone count\n"
            "- stone positions\n"
            "- relative stone sizes\n"
            "- stone cuts and shapes\n"
            "- prongs\n"
            "- settings\n"
            "- pearls, when present\n"
            "- zirconia, when present\n"
            "- decorative elements\n"
            "- metal thickness\n"
            "- relief\n"
            "- texture\n"
            "- surface finish\n"
            "- plating color\n"
            "- original shine characteristics\n"
            "- manufacturing details\n"
            "- visible natural manufacturing imperfections\n\n"

            "STRICTLY FORBIDDEN:\n"
            "- Do not redesign the anklet.\n"
            "- Do not convert it into a bracelet.\n"
            "- Do not replace the chain or link style.\n"
            "- Do not make the chain thicker or thinner.\n"
            "- Do not change link geometry or spacing.\n"
            "- Do not add links merely to fit the ankle.\n"
            "- Do not remove links merely to fit the ankle.\n"
            "- Do not shorten the product for composition.\n"
            "- Do not visually lengthen the product for composition.\n"
            "- Do not alter the clasp or extension chain.\n"
            "- Do not add charms or pendants.\n"
            "- Do not remove charms or pendants.\n"
            "- Do not reposition decorative components.\n"
            "- Do not add stones.\n"
            "- Do not remove stones.\n"
            "- Do not reposition stones.\n"
            "- Do not change stone size relationships.\n"
            "- Do not change stone cuts or shapes.\n"
            "- Do not alter prongs or settings.\n"
            "- Do not simplify structural connections.\n"
            "- Do not change metal thickness.\n"
            "- Do not alter the plating color.\n"
            "- Do not create a cleaner, richer or more luxurious redesign.\n\n"

            "REAL PHYSICAL SCALE:\n"
            "Place the exact referenced anklet naturally around a realistic "
            "human ankle using believable real-world physical scale.\n\n"

            "Do not enlarge the anklet to make it more visible.\n"
            "Do not shrink it.\n"
            "Do not stretch it.\n"
            "Do not compress it.\n"
            "Do not deform its components to fit the generated ankle.\n\n"

            "Preserve the realistic relationship between chain thickness, "
            "links, charms, stones, decorative components and the human ankle.\n\n"

            "The generated ankle must accommodate the immutable anklet geometry. "
            "Do not redesign the anklet to accommodate the generated anatomy.\n\n"

            "ANKLE PLACEMENT:\n"
            "The anklet must naturally surround the ankle in the anatomically "
            "correct area above the foot.\n\n"

            "Do not place the anklet around the foot arch.\n"
            "Do not place it around the toes.\n"
            "Do not position it excessively high on the lower leg.\n"
            "Do not make it appear like a bracelet transferred onto a leg.\n\n"

            "The jewelry must follow the natural circumference of the ankle "
            "while preserving its exact physical construction.\n\n"

            "The anklet must not float unrealistically far from the skin.\n"
            "It must not merge into the skin.\n"
            "It must not penetrate the ankle.\n"
            "It must not appear painted or pasted onto the body.\n\n"

            "NATURAL FIT:\n"
            "Preserve a realistic amount of natural space between the anklet "
            "and the ankle according to the construction of the original jewelry.\n\n"

            "The anklet should rest naturally without appearing excessively tight "
            "or unrealistically loose.\n\n"

            "Do not alter chain length or component spacing to create a visually "
            "perfect fit. Adapt the generated ankle dimensions and pose around "
            "the immutable jewelry instead.\n\n"

            "NATURAL DRAPE AND GRAVITY:\n"
            "Respect real gravity and physically plausible jewelry behavior.\n\n"

            "Flexible chain sections must rest naturally around the ankle.\n"
            "Charms and pendants, when present, must hang downward naturally "
            "from their true attachment points.\n\n"

            "Do not make charms float upward or sideways without physical reason.\n"
            "Do not force every decorative component to face the camera if doing "
            "so would require physically impossible positioning.\n\n"

            "Do not distort the jewelry merely to improve product visibility.\n\n"

            "Avoid broken chains, disconnected links, impossible bends, duplicated "
            "components, floating sections or unnatural intersections.\n\n"

            "FOOT AND ANKLE ANATOMY:\n"
            "Generate a photorealistic, elegant human ankle and foot with correct "
            "anatomy, realistic skin texture and natural proportions.\n\n"

            "The ankle and foot exist primarily to demonstrate realistic scale, "
            "placement and use of the anklet.\n\n"

            "Avoid malformed feet, duplicated toes, merged toes, excessive toe "
            "count, distorted joints or unnatural ankle anatomy.\n\n"

            "Use an elegant, relaxed and physically plausible foot position.\n\n"

            "MODEL REFERENCE:\n"
            "Use the selected ModelReference only for compatible human visual "
            "characteristics such as skin tone and general photographic identity.\n\n"

            "The ModelReference must NEVER modify the anklet design, geometry, "
            "scale, links, stones, charms, metal, plating or manufacturing details.\n\n"

            "COMPOSITION:\n"
            "Create a professional close-up luxury-jewelry photograph focused "
            "on the ankle and the anklet.\n\n"

            "The anklet must be the absolute visual protagonist.\n"
            "Show enough of the lower leg and foot to communicate realistic "
            "anatomy, scale and placement without allowing the body to dominate "
            "the composition.\n\n"

            "Use an elegant and natural foot pose.\n"
            "Avoid excessive perspective distortion.\n\n"

            "Keep the visually important anklet components clearly visible whenever "
            "physically possible without changing their natural orientation.\n\n"

            "LIGHTING:\n"
            "Use premium luxury-jewelry campaign photography with soft diffused "
            "professional light, delicate natural shadows and controlled highlights.\n\n"

            "Do not use blown highlights.\n"
            "Do not create artificial metallic shine.\n"
            "Do not exaggerate stone sparkle.\n"
            "Do not use lighting to hide links, closures, stones, charms or "
            "structural product details.\n\n"

            "Metal and stones must retain realistic photographic reflections "
            "consistent with the exact referenced product.\n\n"

            "BACKGROUND:\n"
            "Use a clean neutral light beige, off-white or cream background "
            "with subtle natural depth-of-field blur.\n"
            "No objects.\n"
            "No text.\n"
            "No distracting visual elements.\n\n"

            "PHOTOREALISM AND QUALITY:\n"
            "The final image must look like authentic premium jewelry photography.\n"
            "Preserve realistic skin, metal, stones, links, closures, charms and "
            "jewelry microdetails.\n\n"

            "No illustration appearance.\n"
            "No CGI appearance.\n"
            "No plastic skin.\n"
            "No artificial jewelry rendering.\n\n"

            "FINAL PRODUCT VERIFICATION:\n"
            "Before producing the finished image, visually compare the anklet "
            "against the uploaded original reference.\n\n"

            "Verify that ALL of the following remain unchanged:\n"
            "- complete product construction\n"
            "- chain type\n"
            "- chain thickness\n"
            "- link geometry\n"
            "- link spacing\n"
            "- component sequence\n"
            "- clasp or closure\n"
            "- extension chain, when present\n"
            "- charm count\n"
            "- charm positions\n"
            "- charm geometry\n"
            "- centerpiece geometry\n"
            "- stone count\n"
            "- stone positions\n"
            "- relative stone sizes\n"
            "- stone cuts and shapes\n"
            "- prongs and settings\n"
            "- decorative components\n"
            "- metal thickness\n"
            "- relief\n"
            "- plating color\n"
            "- component proportions\n"
            "- manufacturing characteristics\n\n"

            "Also verify that the anklet naturally surrounds the correct ankle "
            "area and follows real gravity without changing its construction.\n\n"

            "If any jewelry detail differs from the uploaded reference, preserve "
            "the reference product instead of the generated interpretation.\n\n"

            "FINAL REQUIREMENT:\n"
            "The final photograph must give the impression that the exact physical "
            "anklet from the uploaded reference was genuinely placed around the "
            "model's ankle and professionally photographed.\n"
            "The ankle, foot, model and photography may be generated. "
            "The jewelry identity must not be."
        ),

        ("RING", "STILL"): (
            "RING STILL — PRODUCT IDENTITY LOCK:\n\n"

            "ABSOLUTE PRIORITY:\n"
            "The uploaded original ring is the exact physical product that "
            "must appear in the final image. It is NOT inspiration, a style "
            "reference, a design suggestion or an approximate reference.\n\n"

            "Do NOT reconstruct the ring from your semantic understanding "
            "of the object. Preserve the visual identity and physical "
            "construction of the uploaded ring and generate only the "
            "professional photographic presentation around it.\n\n"

            "If photographic beauty conflicts with product fidelity, "
            "PRODUCT FIDELITY ALWAYS WINS.\n"
            "A less aesthetically perfect photograph of the exact product "
            "is preferable to a beautiful photograph of a reconstructed "
            "or modified product.\n\n"

            "IMMUTABLE RING GEOMETRY:\n"
            "Preserve exactly:\n"
            "- complete ring design\n"
            "- outer silhouette\n"
            "- band shape\n"
            "- band width\n"
            "- band thickness\n"
            "- visible inner opening\n"
            "- curvature of the band\n"
            "- head or centerpiece geometry\n"
            "- head width and height\n"
            "- head-to-band proportion\n"
            "- connection between head and band\n"
            "- shoulders of the ring\n"
            "- openings and negative spaces\n"
            "- relief\n"
            "- decorative contours\n"
            "- stone count\n"
            "- stone positions\n"
            "- relative stone sizes\n"
            "- stone shapes and cuts\n"
            "- prongs\n"
            "- settings\n"
            "- metal thickness\n"
            "- metal color\n"
            "- plating color\n"
            "- texture\n"
            "- finish\n"
            "- manufacturing characteristics\n"
            "- visible natural manufacturing imperfections\n\n"

            "STRICTLY FORBIDDEN:\n"
            "- Do not redesign the band.\n"
            "- Do not make the band thicker or thinner.\n"
            "- Do not make the band wider or narrower.\n"
            "- Do not change the curvature of the band.\n"
            "- Do not enlarge the head or centerpiece.\n"
            "- Do not shrink the head or centerpiece.\n"
            "- Do not change the head-to-band proportion.\n"
            "- Do not change how the head connects to the band.\n"
            "- Do not add stones.\n"
            "- Do not remove stones.\n"
            "- Do not reposition stones.\n"
            "- Do not regularize the stone pattern.\n"
            "- Do not replace small stones with larger stones.\n"
            "- Do not change stone cuts or shapes.\n"
            "- Do not change prongs or settings.\n"
            "- Do not fill openings.\n"
            "- Do not create new openings.\n"
            "- Do not make the product more symmetrical.\n"
            "- Do not create a cleaner or idealized version of the ring.\n\n"

            "REFERENCE PERSPECTIVE:\n"
            "The source photograph may show the ring from a non-ideal angle. "
            "You may present the exact ring using a professional e-commerce "
            "camera angle, but changing camera perspective must NEVER be used "
            "as permission to redesign hidden or partially visible geometry.\n\n"

            "When product geometry is uncertain because a detail is not clearly "
            "visible in the reference, preserve the safest interpretation "
            "consistent with the visible product. Do not invent decorative "
            "structures or additional product details.\n\n"

            "STILL PRESENTATION:\n"
            "Present one exact ring as a premium e-commerce product photograph "
            "on a pure white #FFFFFF background.\n\n"

            "Use a natural three-quarter or frontal product angle that clearly "
            "communicates the band and centerpiece while preserving their true "
            "relationship.\n\n"

            "Do not use a mannequin, ring holder, pedestal, hand, fingers, "
            "fabric or decorative support.\n\n"

            "Use only a subtle physically plausible contact shadow beneath "
            "the product when necessary to avoid a floating appearance.\n\n"

            "LIGHTING:\n"
            "Use soft professional studio lighting with controlled reflections. "
            "Preserve the original metal color and realistic stone appearance. "
            "Do not use excessive sparkle or highlights that hide product geometry.\n\n"

            "FINAL VISUAL VERIFICATION:\n"
            "Before producing the finished image, compare the generated ring "
            "against the uploaded reference and verify:\n"
            "- same outer silhouette\n"
            "- same band geometry\n"
            "- same band thickness\n"
            "- same centerpiece geometry\n"
            "- same head-to-band proportion\n"
            "- same connection structure\n"
            "- same stone count\n"
            "- same stone layout\n"
            "- same relative stone sizes\n"
            "- same openings and relief\n"
            "- same metal/plating color\n\n"

            "If any of these product characteristics differ, preserve the "
            "uploaded reference instead of the generated interpretation.\n\n"

            "FINAL REQUIREMENT:\n"
            "The final image must look like the exact physical ring from the "
            "uploaded photograph was professionally isolated and photographed "
            "for premium e-commerce. The photographic presentation may improve. "
            "The ring itself must not."
        ),

        ("BRACELET", "STILL"): (
            "BRACELET STILL — STRICT REFERENCE PRESERVATION V3:\n\n"

            "ABSOLUTE PRODUCT AUTHORITY:\n"
            "The uploaded original bracelet image is the only authoritative "
            "visual source for the physical product.\n\n"

            "The final image must represent the exact same physical bracelet "
            "visible in the uploaded reference.\n\n"

            "The reference is NOT inspiration, NOT a design suggestion, "
            "NOT a generic bracelet example and NOT permission to reconstruct "
            "a commercially ideal version of the product.\n\n"

            "Do not reconstruct the bracelet from semantic knowledge of how "
            "bracelets are normally manufactured.\n\n"

            "Generate only the photographic presentation around the product. "
            "The product identity itself is immutable.\n\n"

            "If photographic beauty conflicts with product fidelity, "
            "PRODUCT FIDELITY ALWAYS WINS.\n\n"

            "A less aesthetically perfect image of the exact bracelet is "
            "preferable to a beautiful image of a modified bracelet.\n\n"

            "REFERENCE-ONLY COMPONENT RULE:\n"
            "Use ONLY jewelry components that are clearly and visually confirmed "
            "in the uploaded product reference.\n\n"

            "Never infer, assume or invent a component merely because that "
            "component is common in bracelets.\n\n"

            "Do NOT invent or assume:\n"
            "- clasps\n"
            "- closures\n"
            "- extender chains\n"
            "- regulators\n"
            "- adjustment mechanisms\n"
            "- connectors\n"
            "- terminal pieces\n"
            "- charms\n"
            "- pendants\n"
            "- stones\n"
            "- links\n"
            "- decorative components\n"
            "- structural hardware\n\n"

            "A component may appear in the final image ONLY when its existence "
            "is visually supported by the uploaded reference.\n\n"

            "If a component cannot be confidently confirmed from the reference, "
            "do NOT add it.\n\n"

            "Absence of clear visual evidence means the component must not "
            "be invented.\n\n"

            "NO PRODUCT COMPLETION:\n"
            "Do not attempt to complete hidden, unclear, occluded or partially "
            "visible portions of the bracelet using typical jewelry construction "
            "knowledge.\n\n"

            "Do not make the product more mechanically complete, commercially "
            "standard, symmetrical or technically plausible than what is visually "
            "supported by the reference.\n\n"

            "Never fill missing visual information with invented jewelry hardware.\n\n"

            "When a structural detail is uncertain, choose the most conservative "
            "interpretation that introduces NO new product component.\n\n"

            "IMMUTABLE PRODUCT IDENTITY:\n"
            "Preserve every clearly visible product characteristic exactly as "
            "shown in the reference.\n\n"

            "Preserve exactly when visible:\n"
            "- overall bracelet design\n"
            "- chain type\n"
            "- chain geometry\n"
            "- link shape\n"
            "- link thickness\n"
            "- link proportions\n"
            "- visible link spacing\n"
            "- component sequence\n"
            "- number of visible decorative components\n"
            "- position of visible decorative components\n"
            "- spacing relationships between components\n"
            "- shape of each decorative component\n"
            "- relative component sizes\n"
            "- visible connectors\n"
            "- visible attachment points\n"
            "- visible terminal structures\n"
            "- stones, if visibly present\n"
            "- stone count\n"
            "- stone positions\n"
            "- stone size relationships\n"
            "- prongs and settings\n"
            "- metal thickness\n"
            "- plating color\n"
            "- texture\n"
            "- relief\n"
            "- surface finish\n"
            "- manufacturing characteristics\n"
            "- natural visible imperfections\n\n"

            "STRICTLY FORBIDDEN:\n"
            "- Do not redesign the bracelet.\n"
            "- Do not replace the chain with another chain style.\n"
            "- Do not change link geometry.\n"
            "- Do not make links thicker or thinner.\n"
            "- Do not add links for visual convenience.\n"
            "- Do not remove links for visual convenience.\n"
            "- Do not normalize irregular spacing.\n"
            "- Do not redistribute decorative components.\n"
            "- Do not add decorative components.\n"
            "- Do not remove visible decorative components.\n"
            "- Do not redesign visible decorative components.\n"
            "- Do not enlarge decorative elements for emphasis.\n"
            "- Do not reduce decorative elements.\n"
            "- Do not add stones.\n"
            "- Do not remove stones.\n"
            "- Do not reposition stones.\n"
            "- Do not change metal thickness.\n"
            "- Do not alter plating color.\n"
            "- Do not idealize manufacturing details.\n"
            "- Do not create a cleaner version of the product.\n"
            "- Do not create a more expensive-looking version of the product.\n\n"

            "COMPONENT SEQUENCE LOCK:\n"
            "The sequence and spatial relationships of visible components are "
            "part of the bracelet's product identity.\n\n"

            "Preserve the number, order and relative spacing of the clearly "
            "visible decorative components shown in the reference.\n\n"

            "Do not rearrange components to create visual balance.\n"
            "Do not distribute components at mathematically equal intervals "
            "unless the reference clearly shows that exact arrangement.\n\n"

            "NO GEOMETRIC BEAUTIFICATION:\n"
            "Do not normalize, regularize or beautify the physical layout of "
            "the bracelet for catalog presentation.\n\n"

            "The bracelet does NOT need to form a perfect circle, perfect oval "
            "or mathematically symmetrical composition.\n\n"

            "Natural asymmetry and irregularity are allowed and preferred when "
            "they better preserve the exact physical product.\n\n"

            "Do not rotate decorative components merely to make all visible faces "
            "point uniformly toward the camera.\n\n"

            "REFERENCE LAYOUT PRESERVATION:\n"
            "Preserve the physical arrangement visible in the uploaded reference "
            "as much as reasonably possible.\n\n"

            "For flexible jewelry, changing the entire resting geometry may require "
            "reconstructing chain relationships that are not fully visible.\n\n"

            "Therefore, prefer preserving the reference bracelet's existing physical "
            "layout and component relationships while removing the hand, body, "
            "support and original environment.\n\n"

            "Do not force the bracelet into a new catalog shape if doing so requires "
            "inventing, estimating or reconstructing product structure.\n\n"

            "ALLOWED EDITING SCOPE:\n"
            "The transformation should primarily affect photographic presentation, "
            "not product construction.\n\n"

            "You MAY:\n"
            "- remove the original hand or body\n"
            "- remove the original background\n"
            "- remove non-product supports\n"
            "- use a pure white background\n"
            "- improve exposure\n"
            "- improve white balance\n"
            "- improve controlled studio lighting\n"
            "- improve sharpness carefully\n"
            "- reduce photographic noise\n"
            "- create a subtle realistic contact shadow\n\n"

            "You may NOT use photographic improvement as justification to "
            "reconstruct the bracelet itself.\n\n"

            "STILL PRESENTATION:\n"
            "Present exactly one bracelet on a pure white #FFFFFF background.\n\n"

            "No hand.\n"
            "No wrist.\n"
            "No body.\n"
            "No mannequin.\n"
            "No jewelry display.\n"
            "No fabric.\n"
            "No decorative objects.\n"
            "No text.\n"
            "No logo.\n\n"

            "Use only a subtle physically plausible contact shadow when needed "
            "to prevent a floating appearance.\n\n"

            "LIGHTING:\n"
            "Use soft professional studio illumination with controlled highlights "
            "and realistic metallic reflections.\n\n"

            "Preserve the exact visible plating color.\n"
            "Do not intensify gold saturation.\n"
            "Do not create artificial shine that hides structural details.\n"
            "Do not invent reflections that change the perceived construction "
            "of the product.\n\n"

            "FINAL REFERENCE VERIFICATION:\n"
            "Before producing the final image, compare the bracelet against "
            "the uploaded reference.\n\n"

            "Verify:\n"
            "- no new component was introduced\n"
            "- no visible component was removed\n"
            "- same number of visible decorative elements\n"
            "- same decorative element shapes\n"
            "- same component sequence\n"
            "- same relative component spacing\n"
            "- same chain type\n"
            "- same link geometry\n"
            "- same visible connectors\n"
            "- same visible structural hardware\n"
            "- same stones when present\n"
            "- same metal thickness\n"
            "- same plating color\n"
            "- same manufacturing characteristics\n\n"

            "If the final image contains any product component that cannot be "
            "visually justified by the uploaded reference, REMOVE that invented "
            "component and preserve the reference instead.\n\n"

            "If producing a new product arrangement would require guessing hidden "
            "construction, preserve the reference arrangement rather than guessing.\n\n"

            "FINAL REQUIREMENT:\n"
            "The final result must look like the SAME physical bracelet from the "
            "uploaded photograph was carefully isolated and professionally "
            "re-photographed for e-commerce.\n\n"

            "The background and photography may improve. "
            "The product construction must not change."
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
        model_reference=None,
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
                "MODEL REFERENCE REQUIREMENTS:\n"
                + model_reference.prompt_instruction
                if model_reference
                else ""
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

        final_prompt = "\n\n".join(
            part
            for part in parts
            if part
        )

        prompt_length = len(final_prompt)

        if prompt_length > cls.PROVIDER_MAX_PROMPT_LENGTH:
            raise PromptTooLongError(
                "Generated image prompt exceeds the provider maximum. "
                f"Current length: {prompt_length} characters. "
                f"Provider maximum: {cls.PROVIDER_MAX_PROMPT_LENGTH}. "
                "The validated SceneTemplate and prompt rules were preserved; "
                "reduce only the specific oversized prompt source before retrying."
            )

        return final_prompt

import base64
from dataclasses import dataclass

from django.conf import settings
from openai import OpenAI


@dataclass
class GeneratedAsset:
    content: bytes
    mime_type: str = "image/png"


class OpenAIImageProvider:
    def __init__(self):
        if not settings.OPENAI_API_KEY:
            raise RuntimeError(
                "OPENAI_API_KEY não configurada."
            )

        if not settings.OPENAI_IMAGE_MODEL:
            raise RuntimeError(
                "OPENAI_IMAGE_MODEL não configurado."
            )

        self.client = OpenAI(
            api_key=settings.OPENAI_API_KEY
        )

    def generate(
        self,
        *,
        prompt: str,
        reference_file,
    ) -> GeneratedAsset:
        """
        Gera uma nova imagem usando a imagem original
        da peça como referência.

        Toda configuração específica da OpenAI fica
        concentrada neste provider.
        """

        params = {
            "model": settings.OPENAI_IMAGE_MODEL,
            "image": reference_file,
            "prompt": prompt,
            "size": settings.OPENAI_IMAGE_SIZE,
            "n": 1,
        }

        # ==================================================
        # INPUT FIDELITY
        # ==================================================
        #
        # Não enviamos input_fidelity para gpt-image-2.
        #
        # A API rejeitou explicitamente esse parâmetro:
        #
        # invalid_input_fidelity_model
        #
        # Caso futuramente outro modelo configurado aceite
        # esse recurso, a compatibilidade deve ser adicionada
        # explicitamente aqui.
        # ==================================================

        result = self.client.images.edit(
            **params
        )

        if not result.data:
            raise RuntimeError(
                "A API não retornou nenhuma imagem."
            )

        item = result.data[0]

        image_base64 = getattr(
            item,
            "b64_json",
            None,
        )

        if image_base64:
            return GeneratedAsset(
                content=base64.b64decode(
                    image_base64
                ),
                mime_type="image/png",
            )

        raise RuntimeError(
            "A API não retornou conteúdo "
            "de imagem em base64."
        )
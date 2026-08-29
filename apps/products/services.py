import logging

from django.db import transaction

from apps.products.models import Product, ProductAsset
from apps.studio.models import Generation, GeneratedImage


logger = logging.getLogger(__name__)


class VisualDataDeletionService:
    @classmethod
    def delete_product(
        cls,
        product,
    ):
        files = {}

        with transaction.atomic():
            product = (
                Product.objects
                .select_for_update()
                .get(
                    pk=product.pk
                )
            )

            product_assets = (
                ProductAsset.objects
                .filter(
                    product=product
                )
            )

            generations = (
                Generation.objects
                .filter(
                    product=product
                )
            )

            generated_images = (
                GeneratedImage.objects
                .filter(
                    generation__in=generations
                )
            )

            for asset in product_assets:
                cls._collect_file(
                    files,
                    asset.file,
                )

            for image in generated_images:
                cls._collect_file(
                    files,
                    image.file,
                )

            generated_images.delete()
            generations.delete()
            product_assets.delete()
            product.delete()

            cls._delete_files_on_commit(
                files
            )

    @classmethod
    def delete_generated_image(
        cls,
        generated_image,
    ):
        files = {}

        with transaction.atomic():
            generated_image = (
                GeneratedImage.objects
                .select_for_update()
                .get(
                    pk=generated_image.pk
                )
            )

            cls._collect_file(
                files,
                generated_image.file,
            )

            generated_image.delete()

            cls._delete_files_on_commit(
                files
            )

    @classmethod
    def _collect_file(
        cls,
        files,
        file_field,
    ):
        if (
            not file_field
            or not file_field.name
        ):
            return

        files[
            (
                id(file_field.storage),
                file_field.name,
            )
        ] = (
            file_field.storage,
            file_field.name,
        )

    @classmethod
    def _delete_files_on_commit(
        cls,
        files,
    ):
        file_refs = list(
            files.values()
        )

        def delete_files():
            for storage, name in file_refs:
                try:
                    if cls._file_is_still_referenced(
                        name
                    ):
                        continue

                    storage.delete(
                        name
                    )

                except Exception:
                    logger.exception(
                        "Falha ao remover arquivo privado do storage.",
                        extra={
                            "storage_name": name,
                        },
                    )

        transaction.on_commit(
            delete_files
        )

    @staticmethod
    def _file_is_still_referenced(
        name,
    ):
        return (
            ProductAsset.objects.filter(
                file=name
            ).exists()
            or
            GeneratedImage.objects.filter(
                file=name
            ).exists()
        )

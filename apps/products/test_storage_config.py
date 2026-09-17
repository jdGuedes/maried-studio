from pathlib import Path

from django.core.exceptions import ImproperlyConfigured
from django.test import SimpleTestCase

from config.storage import build_storages_config


class MediaStorageConfigurationTests(SimpleTestCase):
    def test_development_uses_local_filesystem_storage_by_default(self):
        backend, storages = build_storages_config(
            django_env="development",
            base_dir=Path("/app"),
            env={},
        )

        self.assertEqual(
            backend,
            "local",
        )
        self.assertEqual(
            storages["default"]["BACKEND"],
            "django.core.files.storage.FileSystemStorage",
        )

    def test_staging_requires_remote_storage_configuration(self):
        with self.assertRaises(ImproperlyConfigured):
            build_storages_config(
                django_env="staging",
                base_dir=Path("/app"),
                env={},
            )

    def test_production_rejects_local_storage_backend(self):
        with self.assertRaises(ImproperlyConfigured):
            build_storages_config(
                django_env="production",
                base_dir=Path("/app"),
                env={
                    "DJANGO_MEDIA_STORAGE_BACKEND": "local",
                },
            )

    def test_configured_supabase_storage_uses_s3_backend(self):
        backend, storages = build_storages_config(
            django_env="staging",
            base_dir=Path("/app"),
            env={
                "SUPABASE_STORAGE_ENDPOINT": (
                    "https://project-ref.storage.supabase.co/storage/v1/s3"
                ),
                "SUPABASE_STORAGE_REGION": "sa-east-1",
                "SUPABASE_STORAGE_BUCKET": "staging-private-media",
                "SUPABASE_STORAGE_ACCESS_KEY": "test-access-key",
                "SUPABASE_STORAGE_SECRET_KEY": "test-secret-key",
            },
        )

        options = storages["default"]["OPTIONS"]

        self.assertEqual(
            backend,
            "supabase",
        )
        self.assertEqual(
            storages["default"]["BACKEND"],
            "storages.backends.s3.S3Storage",
        )
        self.assertEqual(
            options["addressing_style"],
            "path",
        )
        self.assertEqual(
            options["signature_version"],
            "s3v4",
        )
        self.assertIsNone(
            options["default_acl"]
        )
        self.assertTrue(
            options["querystring_auth"]
        )
        self.assertFalse(
            options["file_overwrite"]
        )

    def test_remote_environment_requires_https_endpoint(self):
        with self.assertRaises(ImproperlyConfigured):
            build_storages_config(
                django_env="production",
                base_dir=Path("/app"),
                env={
                    "SUPABASE_STORAGE_ENDPOINT": (
                        "http://project-ref.storage.supabase.co/storage/v1/s3"
                    ),
                    "SUPABASE_STORAGE_REGION": "sa-east-1",
                    "SUPABASE_STORAGE_BUCKET": "prod-private-media",
                    "SUPABASE_STORAGE_ACCESS_KEY": "test-access-key",
                    "SUPABASE_STORAGE_SECRET_KEY": "test-secret-key",
                },
            )

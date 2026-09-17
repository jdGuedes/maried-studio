from django.core.cache import cache
from django.core.exceptions import ImproperlyConfigured
from django.test import SimpleTestCase, TestCase

from config.cache import build_caches_config


class CacheConfigurationTests(SimpleTestCase):
    def test_development_uses_locmem_cache_by_default(self):
        backend, caches = build_caches_config(
            django_env="development",
            env={},
        )

        self.assertEqual(
            backend,
            "local",
        )
        self.assertEqual(
            caches["default"]["BACKEND"],
            "django.core.cache.backends.locmem.LocMemCache",
        )
        self.assertEqual(
            caches["default"]["KEY_PREFIX"],
            "maried:development",
        )

    def test_staging_requires_redis_url(self):
        with self.assertRaises(ImproperlyConfigured):
            build_caches_config(
                django_env="staging",
                env={},
            )

    def test_production_rejects_local_cache_backend(self):
        with self.assertRaises(ImproperlyConfigured):
            build_caches_config(
                django_env="production",
                env={
                    "DJANGO_CACHE_BACKEND": "local",
                },
            )

    def test_staging_selects_redis_backend_without_network(self):
        backend, caches = build_caches_config(
            django_env="staging",
            env={
                "REDIS_URL": "rediss://user:pass@example.invalid:6379/0",
                "DJANGO_CACHE_KEY_PREFIX": "maried:staging",
            },
        )

        default = caches["default"]

        self.assertEqual(
            backend,
            "redis",
        )
        self.assertEqual(
            default["BACKEND"],
            "django.core.cache.backends.redis.RedisCache",
        )
        self.assertEqual(
            default["LOCATION"],
            "rediss://user:pass@example.invalid:6379/0",
        )
        self.assertEqual(
            default["KEY_PREFIX"],
            "maried:staging",
        )
        self.assertEqual(
            default["OPTIONS"]["socket_connect_timeout"],
            1,
        )
        self.assertEqual(
            default["OPTIONS"]["socket_timeout"],
            1,
        )

    def test_production_selects_redis_backend_without_network(self):
        backend, caches = build_caches_config(
            django_env="production",
            env={
                "REDIS_URL": "rediss://user:pass@example.invalid:6379/0",
                "DJANGO_CACHE_KEY_PREFIX": "maried:production",
            },
        )

        self.assertEqual(
            backend,
            "redis",
        )
        self.assertEqual(
            caches["default"]["KEY_PREFIX"],
            "maried:production",
        )

    def test_remote_environment_requires_rediss_scheme(self):
        with self.assertRaises(ImproperlyConfigured):
            build_caches_config(
                django_env="production",
                env={
                    "REDIS_URL": "redis://user:pass@example.invalid:6379/0",
                },
            )

    def test_error_message_does_not_echo_redis_url(self):
        secret_url = "redis://user:secret-token@example.invalid:6379/0"

        try:
            build_caches_config(
                django_env="production",
                env={
                    "REDIS_URL": secret_url,
                },
            )
        except ImproperlyConfigured as exc:
            self.assertNotIn(
                secret_url,
                str(exc),
            )
            self.assertNotIn(
                "secret-token",
                str(exc),
            )
        else:
            self.fail(
                "Expected ImproperlyConfigured."
            )


class CacheApiRateLimitCounterTests(TestCase):
    def tearDown(self):
        cache.clear()

    def test_counter_uses_django_cache_api_with_timeout(self):
        key = "test:rate-limit-counter"

        added = cache.add(
            key,
            1,
            timeout=60,
        )

        self.assertTrue(
            added
        )
        self.assertEqual(
            cache.incr(key),
            2,
        )
        self.assertEqual(
            cache.get(key),
            2,
        )

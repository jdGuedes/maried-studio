from django.contrib.auth import get_user_model
from django.core.exceptions import ImproperlyConfigured
from django.test import SimpleTestCase, override_settings
from django.urls import reverse
from rest_framework.test import APITestCase, APIClient

from apps.organizations.models import Organization

from .models import UserRole
from config.web_security import build_web_security_config


REMOTE_ENV = {
    "FRONTEND_URL": "https://app.example.com",
    "DJANGO_ALLOWED_HOSTS": "api.example.com",
    "DJANGO_CORS_ALLOWED_ORIGINS": (
        "https://app.example.com"
    ),
    "DJANGO_CSRF_TRUSTED_ORIGINS": (
        "https://app.example.com"
    ),
}


class WebSecurityConfigurationTests(
    SimpleTestCase
):
    def test_local_config_uses_localhost_defaults(self):
        config = build_web_security_config(
            django_env="development",
            env={},
        )

        self.assertEqual(
            config["FRONTEND_URL"],
            "http://localhost:3000",
        )
        self.assertEqual(
            config["ALLOWED_HOSTS"],
            [
                "127.0.0.1",
                "localhost",
            ],
        )
        self.assertEqual(
            config["CORS_ALLOWED_ORIGINS"],
            [
                "http://localhost:3000",
            ],
        )
        self.assertFalse(
            config["SESSION_COOKIE_SECURE"]
        )

    def test_staging_config_requires_explicit_https_values(self):
        config = build_web_security_config(
            django_env="staging",
            env=REMOTE_ENV,
        )

        self.assertEqual(
            config["FRONTEND_URL"],
            "https://app.example.com",
        )
        self.assertEqual(
            config["ALLOWED_HOSTS"],
            [
                "api.example.com",
            ],
        )
        self.assertTrue(
            config["SESSION_COOKIE_SECURE"]
        )
        self.assertTrue(
            config["CSRF_COOKIE_SECURE"]
        )
        self.assertEqual(
            config["SESSION_COOKIE_SAMESITE"],
            "Lax",
        )
        self.assertIsNone(
            config["SESSION_COOKIE_DOMAIN"]
        )

    def test_production_config_requires_explicit_https_values(self):
        config = build_web_security_config(
            django_env="production",
            env=REMOTE_ENV,
        )

        self.assertEqual(
            config["CORS_ALLOWED_ORIGINS"],
            [
                "https://app.example.com",
            ],
        )
        self.assertEqual(
            config["CSRF_TRUSTED_ORIGINS"],
            [
                "https://app.example.com",
            ],
        )
        self.assertTrue(
            config["SECURE_SSL_REDIRECT"]
        )
        self.assertTrue(
            config["USE_X_FORWARDED_PROTO"]
        )

    def test_remote_missing_allowed_hosts_fails_fast(self):
        env = {
            **REMOTE_ENV,
            "DJANGO_ALLOWED_HOSTS": "",
        }

        with self.assertRaises(ImproperlyConfigured):
            build_web_security_config(
                django_env="production",
                env=env,
            )

    def test_remote_missing_cors_fails_fast(self):
        env = {
            **REMOTE_ENV,
            "DJANGO_CORS_ALLOWED_ORIGINS": "",
        }

        with self.assertRaises(ImproperlyConfigured):
            build_web_security_config(
                django_env="production",
                env=env,
            )

    def test_remote_missing_csrf_trusted_origin_fails_fast(self):
        env = {
            **REMOTE_ENV,
            "DJANGO_CSRF_TRUSTED_ORIGINS": "",
        }

        with self.assertRaises(ImproperlyConfigured):
            build_web_security_config(
                django_env="production",
                env=env,
            )

    def test_remote_missing_frontend_url_fails_fast(self):
        env = {
            **REMOTE_ENV,
            "FRONTEND_URL": "",
        }

        with self.assertRaises(ImproperlyConfigured):
            build_web_security_config(
                django_env="production",
                env=env,
            )

    def test_remote_rejects_localhost_frontend_url(self):
        env = {
            **REMOTE_ENV,
            "FRONTEND_URL": "http://localhost:3000",
        }

        with self.assertRaises(ImproperlyConfigured):
            build_web_security_config(
                django_env="production",
                env=env,
            )

    def test_remote_rejects_http_origin(self):
        env = {
            **REMOTE_ENV,
            "DJANGO_CORS_ALLOWED_ORIGINS": (
                "http://app.example.com"
            ),
        }

        with self.assertRaises(ImproperlyConfigured):
            build_web_security_config(
                django_env="production",
                env=env,
            )

    def test_remote_rejects_wildcards(self):
        for key in (
            "DJANGO_ALLOWED_HOSTS",
            "DJANGO_CORS_ALLOWED_ORIGINS",
            "DJANGO_CSRF_TRUSTED_ORIGINS",
        ):
            with self.subTest(
                key=key
            ):
                env = {
                    **REMOTE_ENV,
                    key: "*",
                }

                with self.assertRaises(ImproperlyConfigured):
                    build_web_security_config(
                        django_env="production",
                        env=env,
                    )

    def test_remote_rejects_insecure_cookie_flags(self):
        for key in (
            "DJANGO_SESSION_COOKIE_SECURE",
            "DJANGO_CSRF_COOKIE_SECURE",
        ):
            with self.subTest(
                key=key
            ):
                env = {
                    **REMOTE_ENV,
                    key: "false",
                }

                with self.assertRaises(ImproperlyConfigured):
                    build_web_security_config(
                        django_env="production",
                        env=env,
                    )

    def test_samesite_none_requires_secure_cookie(self):
        env = {
            "DJANGO_SESSION_COOKIE_SECURE": "false",
            "DJANGO_SESSION_COOKIE_SAMESITE": "None",
        }

        with self.assertRaises(ImproperlyConfigured):
            build_web_security_config(
                django_env="development",
                env=env,
            )


@override_settings(
    ALLOWED_HOSTS=[
        "testserver",
        "api.example.com",
    ],
    CORS_ALLOWED_ORIGINS=[
        "https://app.example.com",
    ],
    CORS_ALLOW_CREDENTIALS=True,
    CSRF_TRUSTED_ORIGINS=[
        "https://app.example.com",
    ],
    SESSION_COOKIE_SECURE=True,
    CSRF_COOKIE_SECURE=True,
    SESSION_COOKIE_SAMESITE="Lax",
    CSRF_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_DOMAIN=None,
    CSRF_COOKIE_DOMAIN=None,
)
class CrossOriginSessionSecurityTests(
    APITestCase
):
    origin = "https://app.example.com"

    def setUp(self):
        User = get_user_model()

        self.organization = Organization.objects.create(
            name="Empresa Web Security",
            slug="empresa-web-security",
        )

        self.user = User.objects.create_user(
            email="web-security@example.com",
            password="senha-segura-123",
            name="Web Security",
            organization=self.organization,
            role=UserRole.OWNER,
        )

        self.client = APIClient(
            enforce_csrf_checks=True,
        )

    def csrf_url(self):
        return reverse(
            "accounts:csrf"
        )

    def login_url(self):
        return reverse(
            "accounts:login"
        )

    def logout_url(self):
        return reverse(
            "accounts:logout"
        )

    def me_url(self):
        return reverse(
            "accounts:me"
        )

    def csrf_token(
        self,
        origin=None,
    ):
        response = self.client.get(
            self.csrf_url(),
            HTTP_ORIGIN=origin or self.origin,
            secure=True,
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        return self.client.cookies[
            "csrftoken"
        ].value

    def login_with_csrf(self):
        token = self.csrf_token()

        return self.client.post(
            self.login_url(),
            {
                "email": self.user.email,
                "password": "senha-segura-123",
            },
            format="json",
            HTTP_ORIGIN=self.origin,
            HTTP_X_CSRFTOKEN=token,
            secure=True,
        )

    def test_allowed_origin_receives_cors_credentials_headers(self):
        response = self.client.get(
            self.csrf_url(),
            HTTP_ORIGIN=self.origin,
            secure=True,
        )

        self.assertEqual(
            response["access-control-allow-origin"],
            self.origin,
        )
        self.assertEqual(
            response["access-control-allow-credentials"],
            "true",
        )

    def test_malicious_origin_does_not_receive_cors_credentials(self):
        response = self.client.get(
            self.csrf_url(),
            HTTP_ORIGIN="https://evil.example",
            secure=True,
        )

        self.assertNotIn(
            "access-control-allow-origin",
            response,
        )
        self.assertNotIn(
            "access-control-allow-credentials",
            response,
        )

    def test_preflight_allows_csrf_header_for_allowed_origin(self):
        response = self.client.options(
            self.login_url(),
            HTTP_ORIGIN=self.origin,
            HTTP_ACCESS_CONTROL_REQUEST_METHOD="POST",
            HTTP_ACCESS_CONTROL_REQUEST_HEADERS=(
                "content-type,x-csrftoken"
            ),
            secure=True,
        )

        self.assertEqual(
            response.status_code,
            200,
        )
        self.assertEqual(
            response["access-control-allow-origin"],
            self.origin,
        )
        self.assertIn(
            "x-csrftoken",
            response["access-control-allow-headers"].lower(),
        )

    def test_login_session_and_logout_work_cross_origin(self):
        login_response = self.login_with_csrf()

        self.assertEqual(
            login_response.status_code,
            200,
        )

        self.assertIn(
            "sessionid",
            self.client.cookies,
        )

        session_cookie = self.client.cookies[
            "sessionid"
        ]
        csrf_cookie = self.client.cookies[
            "csrftoken"
        ]

        self.assertTrue(
            session_cookie["secure"]
        )
        self.assertTrue(
            session_cookie["httponly"]
        )
        self.assertEqual(
            session_cookie["samesite"],
            "Lax",
        )
        self.assertEqual(
            session_cookie["domain"],
            "",
        )

        self.assertTrue(
            csrf_cookie["secure"]
        )
        self.assertFalse(
            bool(
                csrf_cookie["httponly"]
            )
        )

        me_response = self.client.get(
            self.me_url(),
            HTTP_ORIGIN=self.origin,
            secure=True,
        )

        self.assertEqual(
            me_response.status_code,
            200,
        )

        logout_response = self.client.post(
            self.logout_url(),
            {},
            format="json",
            HTTP_ORIGIN=self.origin,
            HTTP_X_CSRFTOKEN=csrf_cookie.value,
            secure=True,
        )

        self.assertEqual(
            logout_response.status_code,
            200,
        )

        after_logout = self.client.get(
            self.me_url(),
            HTTP_ORIGIN=self.origin,
            secure=True,
        )

        self.assertIn(
            after_logout.status_code,
            {
                401,
                403,
            },
        )

    def test_login_rejects_missing_csrf(self):
        response = self.client.post(
            self.login_url(),
            {
                "email": self.user.email,
                "password": "senha-segura-123",
            },
            format="json",
            HTTP_ORIGIN=self.origin,
            secure=True,
        )

        self.assertEqual(
            response.status_code,
            403,
        )

    def test_login_rejects_untrusted_origin_even_with_csrf(self):
        token = self.csrf_token()

        response = self.client.post(
            self.login_url(),
            {
                "email": self.user.email,
                "password": "senha-segura-123",
            },
            format="json",
            HTTP_ORIGIN="https://evil.example",
            HTTP_X_CSRFTOKEN=token,
            secure=True,
        )

        self.assertEqual(
            response.status_code,
            403,
        )

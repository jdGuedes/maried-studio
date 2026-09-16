from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from django.utils import timezone
from rest_framework.test import APITestCase, APIClient
from unittest.mock import patch

from apps.billing.models import BillingCycle, Plan, Subscription, SubscriptionStatus
from apps.audit.models import AuditLog
from apps.organizations.models import Organization
from .models import AccountRecoverySecurity, UserRole
from .services import EmailDeliveryError


class UserManagerTests(TestCase):
    def test_create_user_uses_email(self):
        User = get_user_model()
        user = User.objects.create_user(
            email="usuario@example.com",
            password="senha-segura",
            name="Usuário",
        )
        self.assertEqual(user.email, "usuario@example.com")
        self.assertTrue(user.check_password("senha-segura"))
        self.assertFalse(user.is_superuser)
        self.assertFalse(user.is_staff)


class SessionAuthenticationAPITests(APITestCase):
    def setUp(self):
        User = get_user_model()

        self.organization = Organization.objects.create(
            name="Empresa Auth",
            slug="empresa-auth",
        )

        self.inactive_organization = Organization.objects.create(
            name="Empresa Inativa",
            slug="empresa-auth-inativa",
            is_active=False,
        )

        self.owner = User.objects.create_user(
            email="owner-auth@example.com",
            password="senha-segura-123",
            name="Owner Auth",
            organization=self.organization,
            role=UserRole.OWNER,
        )

        self.admin = User.objects.create_user(
            email="admin-auth@example.com",
            password="senha-segura-123",
            name="Admin Auth",
            organization=self.organization,
            role=UserRole.ADMIN,
        )

        self.member = User.objects.create_user(
            email="member-auth@example.com",
            password="senha-segura-123",
            name="Member Auth",
            organization=self.organization,
            role=UserRole.MEMBER,
        )

        self.inactive_user = User.objects.create_user(
            email="inactive-auth@example.com",
            password="senha-segura-123",
            name="Inactive Auth",
            organization=self.organization,
            role=UserRole.MEMBER,
            is_active=False,
        )

        self.inactive_org_user = User.objects.create_user(
            email="inactive-org-auth@example.com",
            password="senha-segura-123",
            name="Inactive Org Auth",
            organization=self.inactive_organization,
            role=UserRole.OWNER,
        )

        self.user_without_organization = User.objects.create_user(
            email="sem-org-auth@example.com",
            password="senha-segura-123",
            name="Sem Org Auth",
            organization=None,
            role=UserRole.MEMBER,
        )

        self.superadmin = User.objects.create_superuser(
            email="superadmin-auth@example.com",
            password="senha-segura-123",
            name="SuperAdmin Auth",
            organization=None,
        )

        self.client = APIClient(
            enforce_csrf_checks=True
        )

    def csrf_url(self):
        return reverse("accounts:csrf")

    def login_url(self):
        return reverse("accounts:login")

    def logout_url(self):
        return reverse("accounts:logout")

    def me_url(self):
        return reverse("accounts:me")

    def get_csrf_token(self):
        response = self.client.get(
            self.csrf_url()
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        return self.client.cookies[
            "csrftoken"
        ].value

    def login_payload(
        self,
        email,
        password="senha-segura-123",
    ):
        token = self.get_csrf_token()

        return self.client.post(
            self.login_url(),
            {
                "email": email,
                "password": password,
            },
            format="json",
            HTTP_X_CSRFTOKEN=token,
        )

    def test_csrf_endpoint_initializes_cookie(self):
        response = self.client.get(
            self.csrf_url()
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertIn(
            "csrftoken",
            self.client.cookies,
        )

    def test_login_with_owner_admin_and_member(self):
        for user in (
            self.owner,
            self.admin,
            self.member,
        ):
            with self.subTest(
                role=user.role
            ):
                self.client = APIClient(
                    enforce_csrf_checks=True
                )

                response = self.login_payload(
                    user.email
                )

                self.assertEqual(
                    response.status_code,
                    200,
                )

                self.assertEqual(
                    response.data["user"]["email"],
                    user.email,
                )

                self.assertEqual(
                    response.data["user"]["role"],
                    user.role,
                )

    def test_invalid_password_and_unknown_email_use_same_message(self):
        wrong_password = self.login_payload(
            self.owner.email,
            password="senha-incorreta",
        )

        self.client = APIClient(
            enforce_csrf_checks=True
        )

        unknown_email = self.login_payload(
            "nao-existe-auth@example.com",
        )

        self.assertEqual(
            wrong_password.status_code,
            400,
        )

        self.assertEqual(
            unknown_email.status_code,
            400,
        )

        self.assertEqual(
            wrong_password.data["detail"],
            "E-mail ou senha inválidos.",
        )

        self.assertEqual(
            unknown_email.data["detail"],
            wrong_password.data["detail"],
        )

    def test_inactive_user_cannot_login(self):
        response = self.login_payload(
            self.inactive_user.email
        )

        self.assertEqual(
            response.status_code,
            400,
        )

    def test_inactive_organization_blocks_common_user_login(self):
        response = self.login_payload(
            self.inactive_org_user.email
        )

        self.assertEqual(
            response.status_code,
            403,
        )

    def test_common_user_without_organization_cannot_login(self):
        response = self.login_payload(
            self.user_without_organization.email
        )

        self.assertEqual(
            response.status_code,
            403,
        )

    def test_superadmin_without_organization_can_login(self):
        response = self.login_payload(
            self.superadmin.email
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertTrue(
            response.data["user"]["is_superuser"]
        )

        self.assertIsNone(
            response.data["user"]["organization"]
        )

    def test_me_works_after_login(self):
        login_response = self.login_payload(
            self.member.email
        )

        self.assertEqual(
            login_response.status_code,
            200,
        )

        response = self.client.get(
            self.me_url()
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertEqual(
            response.data["email"],
            self.member.email,
        )

    def test_blocked_subscription_does_not_block_login_or_me(self):
        plan = Plan.objects.create(
            name="Plano Auth",
            slug="plano-auth-blocked-subscription",
            description="Plano de teste.",
            price="99.90",
            billing_cycle=BillingCycle.MONTHLY,
            credits_per_cycle=50,
            is_active=True,
        )

        period_end = timezone.make_aware(
            timezone.datetime(
                2026,
                8,
                25,
                10,
                0,
                0,
            )
        )

        Subscription.objects.create(
            organization=self.organization,
            plan=plan,
            status=SubscriptionStatus.PAST_DUE,
            price_snapshot=plan.price,
            credits_snapshot=plan.credits_per_cycle,
            started_at=period_end - timezone.timedelta(days=30),
            current_period_start=period_end - timezone.timedelta(days=30),
            current_period_end=period_end,
            next_billing_at=period_end,
        )

        login_response = self.login_payload(
            self.member.email
        )

        self.assertEqual(
            login_response.status_code,
            200,
        )

        response = self.client.get(
            self.me_url()
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertEqual(
            response.data["email"],
            self.member.email,
        )

    def test_logout_invalidates_session(self):
        self.assertEqual(
            self.login_payload(
                self.member.email
            ).status_code,
            200,
        )

        token = self.client.cookies[
            "csrftoken"
        ].value

        logout_response = self.client.post(
            self.logout_url(),
            {},
            format="json",
            HTTP_X_CSRFTOKEN=token,
        )

        self.assertEqual(
            logout_response.status_code,
            200,
        )

        response = self.client.get(
            self.me_url()
        )

        self.assertIn(
            response.status_code,
            {
                401,
                403,
            },
        )

    def test_logout_without_authentication_is_rejected(self):
        token = self.get_csrf_token()

        response = self.client.post(
            self.logout_url(),
            {},
            format="json",
            HTTP_X_CSRFTOKEN=token,
        )

        self.assertIn(
            response.status_code,
            {
                401,
                403,
            },
        )

    def test_login_requires_csrf(self):
        response = self.client.post(
            self.login_url(),
            {
                "email": self.owner.email,
                "password": "senha-segura-123",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            403,
        )

    def test_logout_requires_csrf(self):
        self.assertEqual(
            self.login_payload(
                self.owner.email
            ).status_code,
            200,
        )

        self.client.cookies.pop(
            "csrftoken",
            None,
        )

        response = self.client.post(
            self.logout_url(),
            {},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            403,
        )

    def test_members_endpoint_is_blocked_for_v1_individual_after_session_login(self):
        response = self.login_payload(
            self.owner.email
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        response = self.client.get(
            "/api/accounts/members/"
        )

        self.assertEqual(
            response.status_code,
            404,
        )


class PasswordResetAPITests(APITestCase):
    def setUp(self):
        User = get_user_model()

        self.organization = Organization.objects.create(
            name="Empresa Reset",
            slug="empresa-reset",
        )

        self.user = User.objects.create_user(
            email="reset@example.com",
            password="senha-antiga-123",
            name="Cliente Reset",
            organization=self.organization,
            role=UserRole.OWNER,
        )

        self.inactive_user = User.objects.create_user(
            email="reset-inativo@example.com",
            password="senha-antiga-123",
            name="Cliente Inativo",
            organization=self.organization,
            role=UserRole.MEMBER,
            is_active=False,
        )

        self.client = APIClient(
            enforce_csrf_checks=True
        )

    def csrf_url(self):
        return reverse("accounts:csrf")

    def request_url(self):
        return reverse("accounts:password-reset-request")

    def confirm_url(self):
        return reverse("accounts:password-reset-confirm")

    def me_url(self):
        return reverse("accounts:me")

    def get_csrf_token(self):
        response = self.client.get(
            self.csrf_url()
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        return self.client.cookies[
            "csrftoken"
        ].value

    def post_request(
        self,
        email,
    ):
        return self.client.post(
            self.request_url(),
            {
                "email": email,
            },
            format="json",
            HTTP_X_CSRFTOKEN=self.get_csrf_token(),
        )

    def reset_credentials(
        self,
        user=None,
    ):
        target = user or self.user

        uid = urlsafe_base64_encode(
            force_bytes(
                target.pk
            )
        )

        token = (
            default_token_generator
            .make_token(
                target
            )
        )

        return uid, token

    def post_confirm(
        self,
        *,
        uid=None,
        token=None,
        new_password="nova-senha-segura-123",
        new_password_confirm="nova-senha-segura-123",
    ):
        generated_uid, generated_token = (
            self.reset_credentials()
        )

        return self.client.post(
            self.confirm_url(),
            {
                "uid": uid or generated_uid,
                "token": token or generated_token,
                "new_password": new_password,
                "new_password_confirm": new_password_confirm,
            },
            format="json",
            HTTP_X_CSRFTOKEN=self.get_csrf_token(),
        )

    @override_settings(
        FRONTEND_URL="http://localhost:3000",
        RESEND_API_KEY="re_test_key",
        EMAIL_FROM="MARIED Studio <onboarding@resend.dev>",
    )
    @patch(
        "apps.accounts.services.ResendEmailService.send_password_reset_email"
    )
    def test_request_existing_email_returns_neutral_response_and_sends_email(
        self,
        send_email,
    ):
        response = self.post_request(
            "RESET@example.com"
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertEqual(
            response.data,
            {
                "detail": (
                    "Se existir uma conta com este e-mail, "
                    "enviaremos as instruções de recuperação."
                )
            },
        )

        send_email.assert_called_once()

        call_kwargs = send_email.call_args.kwargs

        self.assertEqual(
            call_kwargs["to_email"],
            self.user.email,
        )

        self.assertIn(
            "http://localhost:3000/redefinir-senha/",
            call_kwargs["reset_url"],
        )

        self.assertNotIn(
            "uid",
            response.data,
        )

        self.assertNotIn(
            "token",
            response.data,
        )

    @patch(
        "apps.accounts.services.ResendEmailService.send_password_reset_email"
    )
    def test_request_unknown_email_returns_same_response_without_email(
        self,
        send_email,
    ):
        existing = self.post_request(
            self.user.email
        )

        self.client = APIClient(
            enforce_csrf_checks=True
        )

        unknown = self.post_request(
            "nao-existe-reset@example.com"
        )

        self.assertEqual(
            existing.status_code,
            200,
        )

        self.assertEqual(
            unknown.status_code,
            200,
        )

        self.assertEqual(
            existing.data,
            unknown.data,
        )

        self.assertEqual(
            send_email.call_count,
            1,
        )

    @patch(
        "apps.accounts.services.ResendEmailService.send_password_reset_email"
    )
    def test_request_inactive_user_is_neutral_and_does_not_send_email(
        self,
        send_email,
    ):
        response = self.post_request(
            self.inactive_user.email
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        send_email.assert_not_called()

    def test_request_requires_csrf(self):
        response = self.client.post(
            self.request_url(),
            {
                "email": self.user.email,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            403,
        )

    def test_confirm_valid_token_changes_password(self):
        response = self.post_confirm()

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertEqual(
            response.data["detail"],
            "Senha alterada com sucesso.",
        )

        self.user.refresh_from_db()

        self.assertTrue(
            self.user.check_password(
                "nova-senha-segura-123"
            )
        )

    def test_existing_session_is_invalidated_after_password_reset(self):
        session_client = APIClient(
            enforce_csrf_checks=True
        )

        session_client.force_login(
            self.user
        )

        before = session_client.get(
            self.me_url()
        )

        self.assertEqual(
            before.status_code,
            200,
        )

        response = self.post_confirm()

        self.assertEqual(
            response.status_code,
            200,
        )

        after = session_client.get(
            self.me_url()
        )

        self.assertIn(
            after.status_code,
            [
                401,
                403,
            ],
        )

    def test_confirm_invalid_token_fails_safely(self):
        response = self.post_confirm(
            token="invalid-token",
        )

        self.assertEqual(
            response.status_code,
            400,
        )

        self.assertEqual(
            response.data["detail"],
            "Link de recuperação inválido ou expirado.",
        )

        self.user.refresh_from_db()

        self.assertTrue(
            self.user.check_password(
                "senha-antiga-123"
            )
        )

    def test_confirm_expired_token_fails_safely(self):
        old_now = timezone.datetime(
            2026,
            1,
            1,
            10,
            0,
            0,
        )

        new_now = timezone.datetime(
            2026,
            1,
            1,
            12,
            0,
            1,
        )

        uid = urlsafe_base64_encode(
            force_bytes(
                self.user.pk
            )
        )

        with patch.object(
            default_token_generator,
            "_now",
            return_value=old_now,
        ):
            token = (
                default_token_generator
                .make_token(
                    self.user
                )
            )

        with override_settings(
            PASSWORD_RESET_TIMEOUT=3600
        ), patch.object(
            default_token_generator,
            "_now",
            return_value=new_now,
        ):
            response = self.post_confirm(
                uid=uid,
                token=token,
            )

        self.assertEqual(
            response.status_code,
            400,
        )

        self.assertEqual(
            response.data["detail"],
            "Link de recuperação inválido ou expirado.",
        )

    def test_confirm_reused_token_fails_after_password_change(self):
        uid, token = self.reset_credentials()

        first = self.post_confirm(
            uid=uid,
            token=token,
        )

        self.assertEqual(
            first.status_code,
            200,
        )

        second = self.post_confirm(
            uid=uid,
            token=token,
            new_password="outra-senha-segura-123",
            new_password_confirm="outra-senha-segura-123",
        )

        self.assertEqual(
            second.status_code,
            400,
        )

        self.assertEqual(
            second.data["detail"],
            "Link de recuperação inválido ou expirado.",
        )

    def test_confirm_wrong_uid_fails_safely(self):
        response = self.post_confirm(
            uid="invalid-uid",
        )

        self.assertEqual(
            response.status_code,
            400,
        )

        self.assertEqual(
            response.data["detail"],
            "Link de recuperação inválido ou expirado.",
        )

    def test_confirm_weak_password_uses_django_validators(self):
        response = self.post_confirm(
            new_password="123",
            new_password_confirm="123",
        )

        self.assertEqual(
            response.status_code,
            400,
        )

        self.assertIn(
            "new_password",
            response.data,
        )

        self.user.refresh_from_db()

        self.assertTrue(
            self.user.check_password(
                "senha-antiga-123"
            )
        )

    def test_confirm_password_mismatch_is_rejected(self):
        response = self.post_confirm(
            new_password="nova-senha-segura-123",
            new_password_confirm="senha-diferente-123",
        )

        self.assertEqual(
            response.status_code,
            400,
        )

        self.assertIn(
            "new_password_confirm",
            response.data,
        )

    def test_confirm_requires_csrf(self):
        uid, token = self.reset_credentials()

        response = self.client.post(
            self.confirm_url(),
            {
                "uid": uid,
                "token": token,
                "new_password": "nova-senha-segura-123",
                "new_password_confirm": "nova-senha-segura-123",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            403,
        )

    @override_settings(
        RESEND_API_KEY="re_test_key",
        EMAIL_FROM="MARIED Studio <onboarding@resend.dev>",
    )
    @patch(
        "apps.accounts.services.ResendEmailService.send_password_reset_email",
        side_effect=EmailDeliveryError("provider failed"),
    )
    def test_resend_failure_is_logged_without_secret_token_or_password(
        self,
        send_email,
    ):
        with self.assertLogs(
            "apps.accounts.services",
            level="WARNING",
        ) as logs:
            response = self.post_request(
                self.user.email
            )

        self.assertEqual(
            response.status_code,
            200,
        )

        send_email.assert_called_once()

        output = "\n".join(
            logs.output
        )

        self.assertNotIn(
            "re_test_key",
            output,
        )

        self.assertNotIn(
            "senha",
            output.lower(),
        )

        self.assertNotIn(
            "/redefinir-senha/",
            output,
        )


class OrganizationMemberApiUnavailableV1Tests(APITestCase):
    def setUp(self):
        User = get_user_model()

        self.organization = Organization.objects.create(
            name="Empresa V1",
            slug="empresa-v1-accounts",
        )

        self.owner = User.objects.create_user(
            email="owner-v1@example.com",
            password="senha-teste",
            name="Owner V1",
            organization=self.organization,
            role=UserRole.OWNER,
        )

        self.admin = User.objects.create_user(
            email="admin-v1@example.com",
            password="senha-teste",
            name="Admin V1",
            organization=self.organization,
            role=UserRole.ADMIN,
        )

        self.member = User.objects.create_user(
            email="member-v1@example.com",
            password="senha-teste",
            name="Member V1",
            organization=self.organization,
            role=UserRole.MEMBER,
        )

    def list_url(self):
        return "/api/accounts/members/"

    def detail_url(self, user):
        return f"/api/accounts/members/{user.pk}/"

    def test_owner_cannot_access_members_api_in_v1(self):
        self.client.force_authenticate(self.owner)

        self.assertEqual(
            self.client.get(self.list_url()).status_code,
            404,
        )

        self.assertEqual(
            self.client.post(
                self.list_url(),
                {
                    "name": "Novo Admin",
                    "email": "novo-admin-v1@example.com",
                    "password": "senha-segura-123",
                    "role": UserRole.ADMIN,
                },
                format="json",
            ).status_code,
            404,
        )

        self.assertEqual(
            self.client.get(self.detail_url(self.admin)).status_code,
            404,
        )

        self.assertEqual(
            self.client.patch(
                self.detail_url(self.member),
                {
                    "name": "Alterado",
                },
                format="json",
            ).status_code,
            404,
        )

    def test_admin_cannot_access_members_api_in_v1(self):
        self.client.force_authenticate(self.admin)

        self.assertEqual(
            self.client.get(self.list_url()).status_code,
            404,
        )

        self.assertEqual(
            self.client.post(
                self.list_url(),
                {
                    "name": "Novo Member",
                    "email": "novo-member-v1@example.com",
                    "password": "senha-segura-123",
                    "role": UserRole.MEMBER,
                },
                format="json",
            ).status_code,
            404,
        )

    def test_member_cannot_access_members_api_in_v1(self):
        self.client.force_authenticate(self.member)

        self.assertEqual(
            self.client.get(self.list_url()).status_code,
            404,
        )


class CurrentUserProfileAPITests(APITestCase):
    def setUp(self):
        User = get_user_model()
        self.organization = Organization.objects.create(
            name="Empresa Perfil",
            slug="empresa-perfil",
        )
        self.owner = User.objects.create_user(
            email="owner-perfil@example.com",
            password="senha-teste",
            name="Owner Perfil",
            organization=self.organization,
            role=UserRole.OWNER,
        )
        self.member = User.objects.create_user(
            email="member-perfil@example.com",
            password="senha-teste",
            name="Member Perfil",
            organization=self.organization,
            role=UserRole.MEMBER,
        )

    def me_url(self):
        return reverse("accounts:me")

    def test_me_get_continues_working(self):
        self.client.force_authenticate(self.member)
        response = self.client.get(self.me_url())
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["email"], self.member.email)
        self.assertEqual(response.data["role"], UserRole.MEMBER)

    def test_member_can_update_own_name(self):
        self.client.force_authenticate(self.member)
        response = self.client.patch(
            self.me_url(),
            {"name": "Novo Nome"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.member.refresh_from_db()
        self.assertEqual(self.member.name, "Novo Nome")

    def test_member_cannot_update_organization_name(self):
        original = self.organization.name
        self.client.force_authenticate(self.member)

        response = self.client.patch(
            self.me_url(),
            {"organization_name": "Empresa Inválida"},
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.organization.refresh_from_db()
        self.assertEqual(self.organization.name, original)

    def test_owner_can_update_organization_name(self):
        self.client.force_authenticate(self.owner)

        response = self.client.patch(
            self.me_url(),
            {"organization_name": "Empresa Atualizada"},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.organization.refresh_from_db()
        self.assertEqual(
            self.organization.name,
            "Empresa Atualizada",
        )


class AccountRecoveryAPITests(APITestCase):
    password = "senha-antiga-123"

    def setUp(self):
        User = get_user_model()

        self.organization = Organization.objects.create(
            name="Empresa Recovery",
            slug="empresa-recovery",
        )

        self.user = User.objects.create_user(
            email="recovery@example.com",
            password=self.password,
            name="Cliente Recovery",
            organization=self.organization,
            role=UserRole.OWNER,
        )

        self.superadmin = User.objects.create_superuser(
            email="super-recovery@example.com",
            password=self.password,
            name="Super Recovery",
            organization=None,
        )

        self.client = APIClient(
            enforce_csrf_checks=True
        )

    def csrf_token(self):
        response = self.client.get(
            reverse("accounts:csrf")
        )
        self.assertEqual(response.status_code, 200)
        return self.client.cookies["csrftoken"].value

    def auth_login(self, user=None):
        self.client.force_authenticate(
            user=user or self.user
        )

    def post_with_csrf(self, url_name, payload):
        return self.client.post(
            reverse(url_name),
            payload,
            format="json",
            HTTP_X_CSRFTOKEN=self.csrf_token(),
        )

    def password_change_payload(
        self,
        **overrides,
    ):
        payload = {
            "current_password": self.password,
            "new_password": "nova-senha-segura-789",
            "new_password_confirm": "nova-senha-segura-789",
        }

        payload.update(
            overrides
        )

        return payload

    def setup_recovery(self, user=None):
        self.auth_login(user or self.user)

        response = self.post_with_csrf(
            "accounts:recovery-setup",
            {
                "question_1": "Cidade favorita?",
                "answer_1": "Fortaleza",
                "question_2": "Primeira vitrine?",
                "answer_2": "Centro",
            },
        )

        self.assertEqual(response.status_code, 201)

        self.client.force_authenticate(user=None)

        return response.data["recovery_key"]

    def test_status_starts_unconfigured_for_existing_user(self):
        self.auth_login()

        response = self.client.get(
            reverse("accounts:recovery-status")
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data["recovery_configured"])
        self.assertIsNone(response.data["configured_at"])

    def test_setup_generates_plaintext_once_and_stores_only_hashes(self):
        recovery_key = self.setup_recovery()

        security = AccountRecoverySecurity.objects.get(
            user=self.user
        )

        self.assertTrue(security.recovery_configured)
        self.assertNotEqual(security.recovery_key_hash, recovery_key)
        self.assertNotIn("Fortaleza", security.security_answer_1_hash)
        self.assertNotIn("Centro", security.security_answer_2_hash)

    def test_recovery_key_accepts_normalized_format(self):
        recovery_key = self.setup_recovery()
        compact = recovery_key.replace("-", "").lower()

        response = self.post_with_csrf(
            "accounts:recovery-verify-key",
            {
                "email": "RECOVERY@example.com",
                "recovery_key": compact,
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("recovery_token", response.data)

    def test_questions_challenge_is_anti_enumeration_for_unknown_email(self):
        self.setup_recovery()

        known = self.post_with_csrf(
            "accounts:recovery-questions",
            {"email": self.user.email},
        )
        unknown = self.post_with_csrf(
            "accounts:recovery-questions",
            {"email": "unknown-recovery@example.com"},
        )

        self.assertEqual(known.status_code, 200)
        self.assertEqual(unknown.status_code, 200)
        self.assertIn("challenge_id", unknown.data)
        self.assertEqual(len(unknown.data["questions"]), 2)

    def test_questions_require_both_correct_answers(self):
        self.setup_recovery()

        challenge = self.post_with_csrf(
            "accounts:recovery-questions",
            {"email": self.user.email},
        )
        questions = challenge.data["questions"]

        wrong = self.post_with_csrf(
            "accounts:recovery-questions-verify",
            {
                "challenge_id": challenge.data["challenge_id"],
                "answers": [
                    {
                        "question_id": questions[0]["id"],
                        "answer": "Fortaleza",
                    },
                    {
                        "question_id": questions[1]["id"],
                        "answer": "errada",
                    },
                ],
            },
        )

        self.assertEqual(wrong.status_code, 400)

        right = self.post_with_csrf(
            "accounts:recovery-questions-verify",
            {
                "challenge_id": challenge.data["challenge_id"],
                "answers": [
                    {
                        "question_id": questions[0]["id"],
                        "answer": "  fortaleza ",
                    },
                    {
                        "question_id": questions[1]["id"],
                        "answer": "CENTRO",
                    },
                ],
            },
        )

        self.assertEqual(right.status_code, 200)
        self.assertIn("recovery_token", right.data)

    def test_reset_changes_password_and_rotates_recovery_key(self):
        old_key = self.setup_recovery()

        token_response = self.post_with_csrf(
            "accounts:recovery-verify-key",
            {
                "email": self.user.email,
                "recovery_key": old_key,
            },
        )

        response = self.post_with_csrf(
            "accounts:recovery-reset-password",
            {
                "recovery_token": token_response.data["recovery_token"],
                "new_password": "nova-senha-segura-456",
                "new_password_confirm": "nova-senha-segura-456",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("recovery_key", response.data)
        self.assertNotEqual(response.data["recovery_key"], old_key)

        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("nova-senha-segura-456"))
        self.assertFalse(self.user.check_password(self.password))

        old_key_response = self.post_with_csrf(
            "accounts:recovery-verify-key",
            {
                "email": self.user.email,
                "recovery_key": old_key,
            },
        )

        self.assertEqual(old_key_response.status_code, 400)

    def test_recovery_token_cannot_be_reused_after_reset(self):
        recovery_key = self.setup_recovery()

        token_response = self.post_with_csrf(
            "accounts:recovery-verify-key",
            {
                "email": self.user.email,
                "recovery_key": recovery_key,
            },
        )

        payload = {
            "recovery_token": token_response.data["recovery_token"],
            "new_password": "nova-senha-segura-456",
            "new_password_confirm": "nova-senha-segura-456",
        }

        first = self.post_with_csrf(
            "accounts:recovery-reset-password",
            payload,
        )
        second = self.post_with_csrf(
            "accounts:recovery-reset-password",
            payload,
        )

        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 400)

    def test_failed_attempts_temporarily_block_recovery_but_not_login(self):
        self.setup_recovery()

        for _index in range(5):
            self.post_with_csrf(
                "accounts:recovery-verify-key",
                {
                    "email": self.user.email,
                    "recovery_key": "MRD-INVALID-KEY",
                },
            )

        blocked = self.post_with_csrf(
            "accounts:recovery-verify-key",
            {
                "email": self.user.email,
                "recovery_key": "MRD-INVALID-KEY",
            },
        )

        self.assertEqual(blocked.status_code, 429)

        login = self.post_with_csrf(
            "accounts:login",
            {
                "email": self.user.email,
                "password": self.password,
            },
        )

        self.assertEqual(login.status_code, 200)

    def test_authenticated_key_rotation_requires_current_password(self):
        old_key = self.setup_recovery()
        self.auth_login()

        wrong = self.post_with_csrf(
            "accounts:recovery-rotate-key",
            {"current_password": "senha-errada"},
        )
        self.assertEqual(wrong.status_code, 400)

        right = self.post_with_csrf(
            "accounts:recovery-rotate-key",
            {"current_password": self.password},
        )
        self.assertEqual(right.status_code, 200)

        old_key_response = self.post_with_csrf(
            "accounts:recovery-verify-key",
            {
                "email": self.user.email,
                "recovery_key": old_key,
            },
        )
        self.assertEqual(old_key_response.status_code, 400)

    def test_authenticated_question_change_requires_current_password(self):
        self.setup_recovery()
        self.auth_login()

        wrong = self.post_with_csrf(
            "accounts:recovery-change-questions",
            {
                "current_password": "senha-errada",
                "question_1": "Nova 1?",
                "answer_1": "Resposta 1",
                "question_2": "Nova 2?",
                "answer_2": "Resposta 2",
            },
        )
        self.assertEqual(wrong.status_code, 400)

        right = self.post_with_csrf(
            "accounts:recovery-change-questions",
            {
                "current_password": self.password,
                "question_1": "Nova 1?",
                "answer_1": "Resposta 1",
                "question_2": "Nova 2?",
                "answer_2": "Resposta 2",
            },
        )
        self.assertEqual(right.status_code, 200)
        self.assertIn("recovery_key", right.data)

    def test_authenticated_password_change_requires_authentication(self):
        response = self.post_with_csrf(
            "accounts:password-change",
            self.password_change_payload(),
        )

        self.assertIn(
            response.status_code,
            {
                401,
                403,
            },
        )

    def test_authenticated_password_change_requires_csrf(self):
        self.client.force_login(
            self.user
        )

        response = self.client.post(
            reverse("accounts:password-change"),
            self.password_change_payload(),
            format="json",
        )

        self.assertEqual(
            response.status_code,
            403,
        )

    def test_authenticated_password_change_rejects_wrong_current_password(self):
        self.auth_login()

        response = self.post_with_csrf(
            "accounts:password-change",
            self.password_change_payload(
                current_password="senha-errada",
            ),
        )

        self.assertEqual(
            response.status_code,
            400,
        )

        self.assertEqual(
            response.data["code"],
            "current_password_invalid",
        )

        self.user.refresh_from_db()

        self.assertTrue(
            self.user.check_password(
                self.password
            )
        )

    def test_authenticated_password_change_rejects_mismatch(self):
        self.auth_login()

        response = self.post_with_csrf(
            "accounts:password-change",
            self.password_change_payload(
                new_password_confirm="senha-diferente-789",
            ),
        )

        self.assertEqual(
            response.status_code,
            400,
        )

        self.assertIn(
            "new_password_confirm",
            response.data,
        )

    def test_authenticated_password_change_uses_django_validators(self):
        self.auth_login()

        response = self.post_with_csrf(
            "accounts:password-change",
            self.password_change_payload(
                new_password="12345678",
                new_password_confirm="12345678",
            ),
        )

        self.assertEqual(
            response.status_code,
            400,
        )

        self.assertIn(
            "new_password",
            response.data,
        )

        self.user.refresh_from_db()

        self.assertTrue(
            self.user.check_password(
                self.password
            )
        )

    def test_authenticated_password_change_preserves_recovery_key_and_current_session(self):
        recovery_key = self.setup_recovery()

        self.client.force_login(
            self.user
        )

        response = self.post_with_csrf(
            "accounts:password-change",
            self.password_change_payload(),
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertEqual(
            response.data,
            {
                "detail": (
                    "Senha alterada com sucesso."
                )
            },
        )

        me_response = self.client.get(
            reverse("accounts:me")
        )

        self.assertEqual(
            me_response.status_code,
            200,
        )

        self.user.refresh_from_db()

        self.assertTrue(
            self.user.check_password(
                "nova-senha-segura-789"
            )
        )

        self.assertFalse(
            self.user.check_password(
                self.password
            )
        )

        old_key_response = self.post_with_csrf(
            "accounts:recovery-verify-key",
            {
                "email": self.user.email,
                "recovery_key": recovery_key,
            },
        )

        self.assertEqual(
            old_key_response.status_code,
            200,
        )

        security = AccountRecoverySecurity.objects.get(
            user=self.user
        )

        self.assertTrue(
            security.recovery_configured
        )

        self.assertTrue(
            AuditLog.objects.filter(
                user=self.user,
                action="PASSWORD_CHANGED",
                metadata={
                    "source": (
                        "authenticated_account_security"
                    ),
                },
            ).exists()
        )

    def test_authenticated_password_change_invalidates_other_session(self):
        other_client = APIClient(
            enforce_csrf_checks=True
        )

        self.client.force_login(
            self.user
        )
        other_client.force_login(
            self.user
        )

        before = other_client.get(
            reverse("accounts:me")
        )

        self.assertEqual(
            before.status_code,
            200,
        )

        response = self.post_with_csrf(
            "accounts:password-change",
            self.password_change_payload(),
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        after = other_client.get(
            reverse("accounts:me")
        )

        self.assertIn(
            after.status_code,
            {
                401,
                403,
            },
        )

    def test_superadmin_can_change_own_password_only(self):
        self.client.force_authenticate(
            user=self.superadmin
        )

        response = self.post_with_csrf(
            "accounts:password-change",
            {
                "current_password": self.password,
                "new_password": "nova-senha-super-789",
                "new_password_confirm": "nova-senha-super-789",
                "user_id": self.user.pk,
                "organization_id": str(
                    self.organization.pk
                ),
                "is_staff": True,
            },
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.superadmin.refresh_from_db()
        self.user.refresh_from_db()

        self.assertTrue(
            self.superadmin.check_password(
                "nova-senha-super-789"
            )
        )

        self.assertTrue(
            self.user.check_password(
                self.password
            )
        )

    def test_superadmin_profile_not_forced_into_recovery(self):
        self.client.force_authenticate(user=self.superadmin)

        response = self.client.get(reverse("accounts:me"))

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data["recovery_configured"])
        self.assertTrue(response.data["is_superuser"])

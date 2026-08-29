from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APITestCase, APIClient

from apps.billing.models import BillingCycle, Plan, Subscription, SubscriptionStatus
from apps.organizations.models import Organization
from .models import UserRole


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

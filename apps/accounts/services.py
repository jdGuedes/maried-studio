import json
import logging
import secrets
import unicodedata
from html import escape
from urllib import error, request

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import check_password, make_password
from django.contrib.auth.tokens import default_token_generator
from django.core import signing
from django.core.exceptions import ValidationError
from django.contrib.auth.password_validation import validate_password
from django.db import transaction
from django.utils import timezone
from django.utils.encoding import force_bytes, force_str
from django.utils.http import (
    urlsafe_base64_decode,
    urlsafe_base64_encode,
)

from apps.audit.models import AuditLog

from .models import (
    AccountRecoveryQuestionChallenge,
    AccountRecoverySecurity,
)


logger = logging.getLogger(__name__)


PASSWORD_RESET_NEUTRAL_DETAIL = (
    "Se existir uma conta com este e-mail, enviaremos "
    "as instruções de recuperação."
)

PASSWORD_RESET_INVALID_DETAIL = (
    "Link de recuperação inválido ou expirado."
)


class EmailDeliveryError(Exception):
    pass


class PasswordResetInvalidError(Exception):
    pass


class PasswordChangeError(Exception):
    detail = (
        "NÃ£o foi possÃ­vel confirmar sua senha atual."
    )


class AccountPasswordService:
    @staticmethod
    def change_authenticated_password(
        *,
        user,
        current_password,
        new_password,
    ):
        if not user.check_password(
            current_password
        ):
            raise PasswordChangeError()

        with transaction.atomic():
            user.set_password(
                new_password
            )

            user.save(
                update_fields=[
                    "password",
                ]
            )

            AuditLog.objects.create(
                organization=user.organization,
                user=user,
                action="PASSWORD_CHANGED",
                entity_type="User",
                entity_id=str(
                    user.pk
                ),
                metadata={
                    "source": (
                        "authenticated_account_security"
                    ),
                },
            )

        return user


class ResendEmailService:
    api_url = "https://api.resend.com/emails"

    def send_password_reset_email(
        self,
        *,
        to_email,
        reset_url,
    ):
        api_key = getattr(
            settings,
            "RESEND_API_KEY",
            "",
        )

        if not api_key:
            raise EmailDeliveryError(
                "Email provider is not configured."
            )

        subject = (
            "Redefinição de senha — MARIED Studio"
        )

        text_body = (
            "Recebemos uma solicitação para redefinir sua senha "
            "do MARIED Studio.\n\n"
            "Use o link abaixo para criar uma nova senha:\n"
            f"{reset_url}\n\n"
            "Se você não solicitou esta alteração, ignore este e-mail."
        )

        safe_reset_url = escape(
            reset_url,
            quote=True,
        )

        html_body = (
            "<p>Recebemos uma solicitação para redefinir sua senha "
            "do MARIED Studio.</p>"
            "<p>Use o link abaixo para criar uma nova senha:</p>"
            f'<p><a href="{safe_reset_url}">Redefinir senha</a></p>'
            "<p>Se você não solicitou esta alteração, ignore este e-mail.</p>"
        )

        payload = json.dumps(
            {
                "from": settings.EMAIL_FROM,
                "to": [
                    to_email,
                ],
                "subject": subject,
                "text": text_body,
                "html": html_body,
            }
        ).encode("utf-8")

        resend_request = request.Request(
            self.api_url,
            data=payload,
            method="POST",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
        )

        try:
            with request.urlopen(
                resend_request,
                timeout=10,
            ) as response:
                if response.status < 200 or response.status >= 300:
                    raise EmailDeliveryError(
                        f"Resend returned HTTP {response.status}."
                    )

        except error.HTTPError as exc:
            logger.warning(
                "resend_password_reset_delivery_failed status=%s",
                exc.code,
            )
            raise EmailDeliveryError(
                "Resend request failed."
            ) from exc

        except error.URLError as exc:
            logger.warning(
                "resend_password_reset_delivery_failed reason=%s",
                exc.reason.__class__.__name__,
            )
            raise EmailDeliveryError(
                "Resend request failed."
            ) from exc


class PasswordResetService:
    def __init__(
        self,
        email_service=None,
    ):
        self.email_service = (
            email_service
            or ResendEmailService()
        )

    def request_reset(
        self,
        *,
        email,
    ):
        User = get_user_model()

        normalized_email = (
            User.objects.normalize_email(
                email
            )
        )

        user = (
            User.objects
            .filter(
                email__iexact=normalized_email,
                is_active=True,
            )
            .first()
        )

        if (
            not user
            or
            not user.has_usable_password()
        ):
            return False

        uid = urlsafe_base64_encode(
            force_bytes(
                user.pk
            )
        )

        token = (
            default_token_generator
            .make_token(
                user
            )
        )

        reset_url = (
            f"{settings.FRONTEND_URL}"
            f"/redefinir-senha/{uid}/{token}"
        )

        try:
            self.email_service.send_password_reset_email(
                to_email=user.email,
                reset_url=reset_url,
            )

        except EmailDeliveryError:
            logger.warning(
                "password_reset_email_not_sent user_id=%s",
                user.pk,
            )

        return True

    def confirm_reset(
        self,
        *,
        uid,
        token,
        new_password,
    ):
        user = self.get_user_from_uid(
            uid
        )

        if (
            not user
            or
            not user.is_active
            or
            not default_token_generator.check_token(
                user,
                token,
            )
        ):
            raise PasswordResetInvalidError(
                PASSWORD_RESET_INVALID_DETAIL
            )

        try:
            validate_password(
                new_password,
                user,
            )

        except ValidationError as exc:
            raise exc

        user.set_password(
            new_password
        )

        user.save(
            update_fields=[
                "password",
            ]
        )

        return user

    def get_user_from_uid(
        self,
        uid,
    ):
        User = get_user_model()

        try:
            user_id = force_str(
                urlsafe_base64_decode(
                    uid
                )
            )

            return User.objects.get(
                pk=user_id
            )

        except (
            TypeError,
            ValueError,
            OverflowError,
            User.DoesNotExist,
            ValidationError,
        ):
            return None


RECOVERY_INVALID_DETAIL = (
    "Não foi possível validar os dados de recuperação."
)

RECOVERY_BLOCKED_DETAIL = (
    "Não foi possível validar os dados de recuperação."
)

RECOVERY_CURRENT_PASSWORD_INVALID_DETAIL = (
    "Não foi possível confirmar sua senha atual."
)

RECOVERY_TOKEN_INVALID_DETAIL = (
    "Autorização de recuperação inválida ou expirada."
)


class AccountRecoveryError(Exception):
    status_code = 400
    detail = RECOVERY_INVALID_DETAIL

    def __init__(self, detail=None, status_code=None):
        self.detail = detail or self.detail

        if status_code is not None:
            self.status_code = status_code

        super().__init__(
            self.detail
        )


class AccountRecoveryBlockedError(AccountRecoveryError):
    status_code = 429
    detail = RECOVERY_BLOCKED_DETAIL


class AccountRecoveryTokenError(AccountRecoveryError):
    detail = RECOVERY_TOKEN_INVALID_DETAIL


class AccountRecoveryService:
    token_salt = "maried.accounts.recovery.authorization"
    alphabet = "23456789ABCDEFGHJKMNPQRSTUVWXYZ"
    synthetic_questions = (
        "Qual resposta de segurança você configurou para esta conta?",
        "Qual segunda resposta de segurança você configurou para esta conta?",
    )

    @classmethod
    def get_or_create_security(
        cls,
        user,
    ):
        security, _created = (
            AccountRecoverySecurity.objects
            .get_or_create(
                user=user
            )
        )

        return security

    @classmethod
    def status_for_user(
        cls,
        user,
    ):
        security = cls.get_or_create_security(
            user
        )

        return cls.status_from_security(
            security
        )

    @classmethod
    def status_from_security(
        cls,
        security,
    ):
        return {
            "recovery_configured": (
                security.recovery_configured
            ),
            "recovery_key_configured": (
                security.recovery_key_configured
            ),
            "security_questions_configured": (
                security.security_questions_configured
            ),
            "configured_at": security.configured_at,
            "key_rotated_at": security.key_rotated_at,
            "temporarily_blocked": (
                security.temporarily_blocked
            ),
            "blocked_until": security.blocked_until,
        }

    @classmethod
    def is_required_for_user(
        cls,
        user,
    ):
        if (
            not user
            or not user.is_authenticated
            or user.is_superuser
        ):
            return False

        return True

    @classmethod
    def user_has_configured_recovery(
        cls,
        user,
    ):
        if not cls.is_required_for_user(
            user
        ):
            return True

        try:
            security = user.recovery_security

        except AccountRecoverySecurity.DoesNotExist:
            return False

        return security.recovery_configured

    @classmethod
    def ensure_user_can_operate(
        cls,
        user,
    ):
        if not cls.user_has_configured_recovery(
            user
        ):
            raise AccountRecoveryError(
                "Configure a recuperação da conta antes de continuar.",
                status_code=403,
            )

    @classmethod
    def setup(
        cls,
        *,
        user,
        question_1,
        answer_1,
        question_2,
        answer_2,
    ):
        with transaction.atomic():
            security, _created = (
                AccountRecoverySecurity.objects
                .select_for_update()
                .get_or_create(
                    user=user
                )
            )

            if security.recovery_configured:
                raise AccountRecoveryError(
                    "Recuperação de conta já configurada."
                )

            recovery_key = (
                cls.generate_recovery_key()
            )

            cls._store_recovery_factors(
                security=security,
                question_1=question_1,
                answer_1=answer_1,
                question_2=question_2,
                answer_2=answer_2,
                recovery_key=recovery_key,
            )

        return {
            "recovery_key": recovery_key,
            "status": cls.status_from_security(
                security
            ),
        }

    @classmethod
    def rotate_key_authenticated(
        cls,
        *,
        user,
        current_password,
    ):
        cls._validate_current_password(
            user=user,
            current_password=current_password,
        )

        with transaction.atomic():
            security = (
                AccountRecoverySecurity.objects
                .select_for_update()
                .get(
                    user=user
                )
            )

            if not security.security_questions_configured:
                raise AccountRecoveryError(
                    "Configure as perguntas de segurança antes de gerar uma chave."
                )

            recovery_key = (
                cls.generate_recovery_key()
            )

            security.recovery_key_hash = (
                make_password(
                    cls.normalize_recovery_key(
                        recovery_key
                    )
                )
            )
            security.key_rotated_at = (
                timezone.now()
            )
            security.failed_attempts = 0
            security.last_failed_at = None
            security.blocked_until = None
            security.save(
                update_fields=[
                    "recovery_key_hash",
                    "key_rotated_at",
                    "failed_attempts",
                    "last_failed_at",
                    "blocked_until",
                    "updated_at",
                ]
            )

        return {
            "recovery_key": recovery_key,
            "status": cls.status_from_security(
                security
            ),
        }

    @classmethod
    def change_questions_authenticated(
        cls,
        *,
        user,
        current_password,
        question_1,
        answer_1,
        question_2,
        answer_2,
    ):
        cls._validate_current_password(
            user=user,
            current_password=current_password,
        )

        with transaction.atomic():
            security, _created = (
                AccountRecoverySecurity.objects
                .select_for_update()
                .get_or_create(
                    user=user
                )
            )

            recovery_key = (
                cls.generate_recovery_key()
            )

            cls._store_recovery_factors(
                security=security,
                question_1=question_1,
                answer_1=answer_1,
                question_2=question_2,
                answer_2=answer_2,
                recovery_key=recovery_key,
            )

        return {
            "recovery_key": recovery_key,
            "status": cls.status_from_security(
                security
            ),
        }

    @classmethod
    def verify_recovery_key(
        cls,
        *,
        email,
        recovery_key,
    ):
        user = cls._find_recoverable_user(
            email
        )

        if not user:
            cls._dummy_hash_check(
                recovery_key
            )
            raise AccountRecoveryError()

        failure = None
        result = None

        with transaction.atomic():
            security = (
                AccountRecoverySecurity.objects
                .select_for_update()
                .get(
                    user=user
                )
            )

            cls._raise_if_blocked(
                security
            )

            valid = (
                security.recovery_key_configured
                and check_password(
                    cls.normalize_recovery_key(
                        recovery_key
                    ),
                    security.recovery_key_hash,
                )
            )

            if not valid:
                cls._record_failed_attempt(
                    security
                )
                failure = (
                    AccountRecoveryBlockedError()
                    if security.temporarily_blocked
                    else AccountRecoveryError()
                )

            else:
                cls._reset_failed_attempts(
                    security
                )

                result = cls._build_recovery_authorization(
                    user=user,
                    security=security,
                )

        if failure:
            raise failure

        return result

    @classmethod
    def create_questions_challenge(
        cls,
        *,
        email,
    ):
        user = cls._find_recoverable_user(
            email
        )

        questions = cls.synthetic_questions
        challenge_user = None

        if user:
            try:
                security = user.recovery_security

            except AccountRecoverySecurity.DoesNotExist:
                security = None

            if (
                security
                and security.security_questions_configured
            ):
                questions = (
                    security.security_question_1,
                    security.security_question_2,
                )
                challenge_user = user

        challenge = (
            AccountRecoveryQuestionChallenge.objects
            .create(
                user=challenge_user,
                question_1_id=get_random_challenge_id(),
                question_2_id=get_random_challenge_id(),
                expires_at=(
                    timezone.now()
                    + timezone.timedelta(
                        seconds=settings.ACCOUNT_RECOVERY_CHALLENGE_TIMEOUT
                    )
                ),
            )
        )

        return {
            "challenge_id": challenge.pk,
            "questions": [
                {
                    "id": challenge.question_1_id,
                    "question": questions[0],
                },
                {
                    "id": challenge.question_2_id,
                    "question": questions[1],
                },
            ],
            "expires_in": settings.ACCOUNT_RECOVERY_CHALLENGE_TIMEOUT,
        }

    @classmethod
    def verify_questions(
        cls,
        *,
        challenge_id,
        answers,
    ):
        challenge = (
            AccountRecoveryQuestionChallenge.objects
            .filter(
                pk=challenge_id
            )
            .first()
        )

        if (
            not challenge
            or challenge.is_expired
            or challenge.is_used
            or not challenge.user_id
        ):
            raise AccountRecoveryError()

        failure = None
        result = None

        with transaction.atomic():
            challenge = (
                AccountRecoveryQuestionChallenge.objects
                .select_for_update()
                .get(
                    pk=challenge.pk
                )
            )

            if (
                challenge.is_expired
                or challenge.is_used
                or not challenge.user_id
            ):
                raise AccountRecoveryError()

            security = (
                AccountRecoverySecurity.objects
                .select_for_update()
                .get(
                    user=challenge.user
                )
            )

            cls._raise_if_blocked(
                security
            )

            answer_map = {
                item["question_id"]: item["answer"]
                for item in answers
            }

            valid = (
                check_password(
                    cls.normalize_answer(
                        answer_map.get(
                            challenge.question_1_id,
                            "",
                        )
                    ),
                    security.security_answer_1_hash,
                )
                and check_password(
                    cls.normalize_answer(
                        answer_map.get(
                            challenge.question_2_id,
                            "",
                        )
                    ),
                    security.security_answer_2_hash,
                )
            )

            if not valid:
                cls._record_failed_attempt(
                    security
                )
                failure = (
                    AccountRecoveryBlockedError()
                    if security.temporarily_blocked
                    else AccountRecoveryError()
                )

            else:
                challenge.used_at = timezone.now()
                challenge.save(
                    update_fields=[
                        "used_at",
                    ]
                )

                cls._reset_failed_attempts(
                    security
                )

                result = cls._build_recovery_authorization(
                    user=challenge.user,
                    security=security,
                )

        if failure:
            raise failure

        return result

    @classmethod
    def reset_password(
        cls,
        *,
        recovery_token,
        new_password,
    ):
        payload = cls._load_recovery_authorization(
            recovery_token
        )

        User = get_user_model()

        try:
            user = User.objects.get(
                pk=payload["user_id"],
                is_active=True,
            )

        except User.DoesNotExist as exc:
            raise AccountRecoveryTokenError() from exc

        if (
            not user.is_superuser
            and
            (
                not user.organization_id
                or not user.organization.is_active
            )
        ):
            raise AccountRecoveryTokenError()

        try:
            validate_password(
                new_password,
                user,
            )

        except ValidationError as exc:
            raise exc

        with transaction.atomic():
            user = (
                User.objects
                .select_for_update()
                .get(
                    pk=user.pk
                )
            )

            security = (
                AccountRecoverySecurity.objects
                .select_for_update()
                .get(
                    user=user
                )
            )

            cls._validate_authorization_state(
                payload=payload,
                user=user,
                security=security,
            )

            recovery_key = (
                cls.generate_recovery_key()
            )

            user.set_password(
                new_password
            )
            user.save(
                update_fields=[
                    "password",
                ]
            )

            security.recovery_key_hash = (
                make_password(
                    cls.normalize_recovery_key(
                        recovery_key
                    )
                )
            )
            security.key_rotated_at = (
                timezone.now()
            )
            security.failed_attempts = 0
            security.last_failed_at = None
            security.blocked_until = None
            security.save(
                update_fields=[
                    "recovery_key_hash",
                    "key_rotated_at",
                    "failed_attempts",
                    "last_failed_at",
                    "blocked_until",
                    "updated_at",
                ]
            )

        return {
            "detail": "Senha alterada com sucesso.",
            "recovery_key": recovery_key,
        }

    @classmethod
    def generate_recovery_key(
        cls,
    ):
        raw = "".join(
            secrets.choice(
                cls.alphabet
            )
            for _index in range(20)
        )

        groups = [
            raw[index:index + 5]
            for index in range(0, len(raw), 5)
        ]

        return "MRD-" + "-".join(
            groups
        )

    @classmethod
    def normalize_recovery_key(
        cls,
        value,
    ):
        normalized = (
            unicodedata
            .normalize(
                "NFKC",
                str(value or ""),
            )
            .strip()
            .upper()
        )

        normalized = (
            normalized
            .replace(" ", "")
            .replace("-", "")
        )

        if normalized.startswith(
            "MRD"
        ):
            normalized = normalized[3:]

        return normalized

    @classmethod
    def normalize_answer(
        cls,
        value,
    ):
        return (
            unicodedata
            .normalize(
                "NFKC",
                str(value or ""),
            )
            .strip()
            .casefold()
        )

    @classmethod
    def _store_recovery_factors(
        cls,
        *,
        security,
        question_1,
        answer_1,
        question_2,
        answer_2,
        recovery_key,
    ):
        now = timezone.now()

        security.security_question_1 = (
            question_1.strip()
        )
        security.security_question_2 = (
            question_2.strip()
        )
        security.security_answer_1_hash = (
            make_password(
                cls.normalize_answer(
                    answer_1
                )
            )
        )
        security.security_answer_2_hash = (
            make_password(
                cls.normalize_answer(
                    answer_2
                )
            )
        )
        security.recovery_key_hash = (
            make_password(
                cls.normalize_recovery_key(
                    recovery_key
                )
            )
        )
        security.configured_at = (
            security.configured_at
            or now
        )
        security.key_rotated_at = now
        security.failed_attempts = 0
        security.last_failed_at = None
        security.blocked_until = None
        security.save(
            update_fields=[
                "security_question_1",
                "security_question_2",
                "security_answer_1_hash",
                "security_answer_2_hash",
                "recovery_key_hash",
                "configured_at",
                "key_rotated_at",
                "failed_attempts",
                "last_failed_at",
                "blocked_until",
                "updated_at",
            ]
        )

    @classmethod
    def _find_recoverable_user(
        cls,
        email,
    ):
        User = get_user_model()

        normalized_email = (
            User.objects
            .normalize_email(
                email
            )
        )

        user = (
            User.objects
            .select_related(
                "organization"
            )
            .filter(
                email__iexact=normalized_email,
                is_active=True,
            )
            .first()
        )

        if not user:
            return None

        if (
            not user.is_superuser
            and
            (
                not user.organization_id
                or not user.organization.is_active
            )
        ):
            return None

        return user

    @classmethod
    def _build_recovery_authorization(
        cls,
        *,
        user,
        security,
    ):
        payload = {
            "user_id": user.pk,
            "state": cls._authorization_state(
                user=user,
                security=security,
            ),
        }

        return {
            "recovery_token": signing.dumps(
                payload,
                salt=cls.token_salt,
                compress=True,
            ),
            "expires_in": settings.ACCOUNT_RECOVERY_TOKEN_TIMEOUT,
        }

    @classmethod
    def _load_recovery_authorization(
        cls,
        token,
    ):
        try:
            return signing.loads(
                token,
                salt=cls.token_salt,
                max_age=settings.ACCOUNT_RECOVERY_TOKEN_TIMEOUT,
            )

        except signing.BadSignature as exc:
            raise AccountRecoveryTokenError() from exc

    @classmethod
    def _authorization_state(
        cls,
        *,
        user,
        security,
    ):
        return signing.Signer(
            salt=cls.token_salt
        ).signature(
            f"{user.pk}:{user.password}:{security.recovery_key_hash}"
        )

    @classmethod
    def _validate_authorization_state(
        cls,
        *,
        payload,
        user,
        security,
    ):
        expected = cls._authorization_state(
            user=user,
            security=security,
        )

        if payload.get("state") != expected:
            raise AccountRecoveryTokenError()

    @classmethod
    def _validate_current_password(
        cls,
        *,
        user,
        current_password,
    ):
        if not user.check_password(
            current_password
        ):
            raise AccountRecoveryError(
                RECOVERY_CURRENT_PASSWORD_INVALID_DETAIL
            )

    @classmethod
    def _raise_if_blocked(
        cls,
        security,
    ):
        if security.temporarily_blocked:
            raise AccountRecoveryBlockedError()

    @classmethod
    def _record_failed_attempt(
        cls,
        security,
    ):
        now = timezone.now()

        security.failed_attempts += 1
        security.last_failed_at = now

        if (
            security.failed_attempts
            >= settings.ACCOUNT_RECOVERY_FAILED_ATTEMPT_LIMIT
        ):
            security.blocked_until = (
                now
                + timezone.timedelta(
                    minutes=settings.ACCOUNT_RECOVERY_BLOCK_MINUTES
                )
            )

        security.save(
            update_fields=[
                "failed_attempts",
                "last_failed_at",
                "blocked_until",
                "updated_at",
            ]
        )

    @classmethod
    def _reset_failed_attempts(
        cls,
        security,
    ):
        if (
            security.failed_attempts
            or security.last_failed_at
            or security.blocked_until
        ):
            security.failed_attempts = 0
            security.last_failed_at = None
            security.blocked_until = None
            security.save(
                update_fields=[
                    "failed_attempts",
                    "last_failed_at",
                    "blocked_until",
                    "updated_at",
                ]
            )

    @classmethod
    def _dummy_hash_check(
        cls,
        value,
    ):
        check_password(
            cls.normalize_recovery_key(
                value
            ),
            make_password(
                "dummy-recovery-key"
            ),
        )


def get_random_challenge_id():
    return secrets.token_urlsafe(
        16
    )

"use client";

import {
  FormEvent,
  useEffect,
  useState,
} from "react";

import Link from "next/link";

import {
  CheckCircle2,
  KeyRound,
  LoaderCircle,
  Sparkles,
} from "lucide-react";

import {
  useParams,
} from "next/navigation";

import {
  confirmPasswordReset,
  ensureCsrfCookie,
} from "@/lib/api";

import {
  PasswordStrengthGuide,
} from "@/components/auth/password-strength-guide";


export default function ResetPasswordPage() {
  const params =
    useParams<{
      uid: string;
      token: string;
    }>();

  const [
    newPassword,
    setNewPassword,
  ] = useState(
    ""
  );

  const [
    newPasswordConfirm,
    setNewPasswordConfirm,
  ] = useState(
    ""
  );

  const [
    submitting,
    setSubmitting,
  ] = useState(
    false
  );

  const [
    success,
    setSuccess,
  ] = useState(
    false
  );

  const [
    error,
    setError,
  ] = useState<string | null>(
    null
  );


  useEffect(() => {
    void ensureCsrfCookie();
  }, []);


  async function handleSubmit(
    event: FormEvent<HTMLFormElement>
  ) {
    event.preventDefault();

    if (
      submitting
    ) {
      return;
    }

    setSubmitting(
      true
    );

    setError(
      null
    );

    if (
      newPassword !==
      newPasswordConfirm
    ) {
      setError(
        "As novas senhas não coincidem."
      );

      setSubmitting(
        false
      );

      return;
    }

    try {
      await confirmPasswordReset({
        uid:
          params.uid,
        token:
          params.token,
        newPassword,
        newPasswordConfirm,
      });

      setNewPassword(
        ""
      );

      setNewPasswordConfirm(
        ""
      );

      setSuccess(
        true
      );

    } catch (error) {
      setError(
        error instanceof Error
          ? error.message
          : "Não foi possível alterar sua senha."
      );

    } finally {
      setSubmitting(
        false
      );
    }
  }


  return (
    <main className="flex min-h-screen items-center justify-center bg-[var(--maried-ivory)] px-5 py-10">
      <section className="w-full max-w-[420px]">
        <div className="text-center">
          <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-[var(--maried-soft-gold)] text-[var(--maried-gold)]">
            <Sparkles
              size={
                22
              }
            />
          </div>

          <div className="mt-5 text-[32px] font-light tracking-[0.12em] text-[var(--maried-gold)]">
            MARIED
          </div>

          <div className="mt-1 text-[11px] tracking-[0.42em] text-[var(--maried-coffee)]">
            STUDIO
          </div>
        </div>

        <form
          onSubmit={
            handleSubmit
          }
          className="maried-card mt-8 space-y-5 p-6"
        >
          <div>
            <h1 className="text-xl font-semibold text-[var(--maried-espresso)]">
              Redefinir senha
            </h1>

            <p className="mt-1 text-sm text-[var(--maried-cocoa)]">
              Crie uma nova senha para acessar sua conta.
            </p>
          </div>

          {success ? (
            <div className="rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-700">
              <div className="flex items-center gap-2 font-medium">
                <CheckCircle2
                  size={
                    17
                  }
                />
                Senha alterada com sucesso.
              </div>
            </div>
          ) : (
            <>
              <label className="block">
                <span className="text-xs font-medium text-[var(--maried-coffee)]">
                  Nova senha
                </span>

                <input
                  type="password"
                  autoComplete="new-password"
                  value={
                    newPassword
                  }
                  onChange={(event) => {
                    setNewPassword(
                      event.target.value
                    );
                  }}
                  required
                  disabled={
                    submitting
                  }
                  className="mt-2 h-12 w-full rounded-xl border border-[var(--maried-sand)] bg-white px-4 text-sm outline-none transition-colors focus:border-[var(--maried-gold)] disabled:opacity-60"
                />
              </label>

              <PasswordStrengthGuide
                password={newPassword}
              />

              <label className="block">
                <span className="text-xs font-medium text-[var(--maried-coffee)]">
                  Confirmar nova senha
                </span>

                <input
                  type="password"
                  autoComplete="new-password"
                  value={
                    newPasswordConfirm
                  }
                  onChange={(event) => {
                    setNewPasswordConfirm(
                      event.target.value
                    );
                  }}
                  required
                  disabled={
                    submitting
                  }
                  className="mt-2 h-12 w-full rounded-xl border border-[var(--maried-sand)] bg-white px-4 text-sm outline-none transition-colors focus:border-[var(--maried-gold)] disabled:opacity-60"
                />
              </label>

              {newPasswordConfirm ? (
                <div
                  aria-live="polite"
                  className={[
                    "rounded-xl px-4 py-2 text-xs",
                    newPassword ===
                    newPasswordConfirm
                      ? "border border-emerald-200 bg-emerald-50 text-emerald-700"
                      : "border border-red-200 bg-red-50 text-red-700",
                  ].join(" ")}
                >
                  {newPassword ===
                  newPasswordConfirm
                    ? "Senhas coincidem."
                    : "As senhas não coincidem."}
                </div>
              ) : null}
            </>
          )}

          {error ? (
            <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
              {error}
            </div>
          ) : null}

          {!success ? (
            <button
              type="submit"
              disabled={
                submitting
              }
              className="flex h-12 w-full items-center justify-center gap-2 rounded-xl bg-[var(--maried-gold)] px-4 text-sm font-medium text-white transition-opacity disabled:opacity-70"
            >
              {submitting ? (
                <LoaderCircle
                  size={
                    18
                  }
                  className="animate-spin"
                />
              ) : (
                <KeyRound
                  size={
                    18
                  }
                />
              )}

              {submitting
                ? "Alterando..."
                : "Alterar senha"}
            </button>
          ) : null}

          <Link
            href="/login"
            className="flex h-12 items-center justify-center rounded-xl border border-[var(--maried-sand)] bg-white px-4 text-sm font-medium text-[var(--maried-coffee)] transition-colors hover:border-[var(--maried-gold)]"
          >
            Voltar para o login
          </Link>
        </form>
      </section>
    </main>
  );
}

"use client";

import {
  FormEvent,
  useEffect,
  useState,
} from "react";

import Link from "next/link";

import {
  ArrowLeft,
  CheckCircle2,
  KeyRound,
  LoaderCircle,
  ShieldQuestion,
} from "lucide-react";

import {
  ensureCsrfCookie,
  requestAccountRecoveryQuestions,
  resetPasswordWithRecovery,
  verifyAccountRecoveryKey,
  verifyAccountRecoveryQuestions,
  type AccountRecoveryQuestion,
} from "@/lib/api";

import {
  PasswordStrengthGuide,
} from "@/components/auth/password-strength-guide";


type Step =
  | "key"
  | "questions"
  | "password"
  | "success";


export default function ForgotPasswordPage() {
  const [
    step,
    setStep,
  ] = useState<Step>(
    "key"
  );

  const [
    email,
    setEmail,
  ] = useState(
    ""
  );

  const [
    recoveryKey,
    setRecoveryKey,
  ] = useState(
    ""
  );

  const [
    recoveryToken,
    setRecoveryToken,
  ] = useState<string | null>(
    null
  );

  const [
    challengeId,
    setChallengeId,
  ] = useState<string | null>(
    null
  );

  const [
    questions,
    setQuestions,
  ] = useState<AccountRecoveryQuestion[]>(
    []
  );

  const [
    answers,
    setAnswers,
  ] = useState<string[]>(
    [
      "",
      "",
    ]
  );

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
    newRecoveryKey,
    setNewRecoveryKey,
  ] = useState<string | null>(
    null
  );

  const [
    submitting,
    setSubmitting,
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

  function clearError() {
    setError(
      null
    );
  }

  async function handleKeySubmit(
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
    clearError();

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
      const response =
        await verifyAccountRecoveryKey({
          email:
            email.trim(),
          recoveryKey,
        });

      setRecoveryKey(
        ""
      );
      setRecoveryToken(
        response.recovery_token
      );
      setStep(
        "password"
      );

    } catch (error) {
      setRecoveryKey(
        ""
      );
      setError(
        error instanceof Error
          ? error.message
          : "Não foi possível validar os dados de recuperação."
      );

    } finally {
      setSubmitting(
        false
      );
    }
  }

  async function handleQuestionsRequest() {
    if (
      submitting
    ) {
      return;
    }

    setSubmitting(
      true
    );
    clearError();

    try {
      const response =
        await requestAccountRecoveryQuestions(
          email.trim()
        );

      setChallengeId(
        response.challenge_id
      );
      setQuestions(
        response.questions
      );
      setAnswers(
        [
          "",
          "",
        ]
      );
      setStep(
        "questions"
      );

    } catch (error) {
      setError(
        error instanceof Error
          ? error.message
          : "Não foi possível iniciar a recuperação."
      );

    } finally {
      setSubmitting(
        false
      );
    }
  }

  async function handleQuestionsSubmit(
    event: FormEvent<HTMLFormElement>
  ) {
    event.preventDefault();

    if (
      submitting ||
      !challengeId
    ) {
      return;
    }

    setSubmitting(
      true
    );
    clearError();

    try {
      const response =
        await verifyAccountRecoveryQuestions({
          challengeId,
          answers:
            questions.map(
              (
                question,
                index
              ) => ({
                questionId:
                  question.id,
                answer:
                  answers[index] ?? "",
              })
            ),
        });

      setAnswers(
        [
          "",
          "",
        ]
      );
      setRecoveryToken(
        response.recovery_token
      );
      setStep(
        "password"
      );

    } catch (error) {
      setAnswers(
        [
          "",
          "",
        ]
      );
      setError(
        error instanceof Error
          ? error.message
          : "Não foi possível validar os dados de recuperação."
      );

    } finally {
      setSubmitting(
        false
      );
    }
  }

  async function handlePasswordSubmit(
    event: FormEvent<HTMLFormElement>
  ) {
    event.preventDefault();

    if (
      submitting ||
      !recoveryToken
    ) {
      return;
    }

    setSubmitting(
      true
    );
    clearError();

    try {
      const response =
        await resetPasswordWithRecovery({
          recoveryToken,
          newPassword,
          newPasswordConfirm,
        });

      setRecoveryToken(
        null
      );
      setNewPassword(
        ""
      );
      setNewPasswordConfirm(
        ""
      );
      setNewRecoveryKey(
        response.recovery_key
      );
      setStep(
        "success"
      );

    } catch (error) {
      setError(
        error instanceof Error
          ? error.message
          : "Não foi possível alterar a senha."
      );

    } finally {
      setSubmitting(
        false
      );
    }
  }

  return (
    <main className="flex min-h-screen items-center justify-center bg-[var(--maried-ivory)] px-5 py-10">
      <section className="w-full max-w-[460px]">
        <div className="text-center">
          <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-[var(--maried-soft-gold)] text-[var(--maried-gold)]">
            <KeyRound
              size={22}
            />
          </div>

          <div className="mt-5 text-[32px] font-light tracking-[0.12em] text-[var(--maried-gold)]">
            MARIED
          </div>

          <div className="mt-1 text-[11px] tracking-[0.42em] text-[var(--maried-coffee)]">
            STUDIO
          </div>
        </div>

        <div className="maried-card mt-8 space-y-5 p-6">
          <div>
            <h1 className="text-xl font-semibold text-[var(--maried-espresso)]">
              Recuperar acesso
            </h1>

            <p className="mt-1 text-sm text-[var(--maried-cocoa)]">
              Use sua chave de recuperação ou responda às perguntas de segurança.
            </p>
          </div>

          {step === "key" ? (
            <form
              onSubmit={handleKeySubmit}
              className="space-y-5"
            >
              <label className="block">
                <span className="text-xs font-medium text-[var(--maried-coffee)]">
                  E-mail
                </span>
                <input
                  type="email"
                  autoComplete="email"
                  value={email}
                  onChange={(event) => {
                    setEmail(
                      event.target.value
                    );
                  }}
                  required
                  disabled={submitting}
                  className="mt-2 h-12 w-full rounded-xl border border-[var(--maried-sand)] bg-white px-4 text-sm outline-none transition-colors focus:border-[var(--maried-gold)] disabled:opacity-60"
                />
              </label>

              <label className="block">
                <span className="text-xs font-medium text-[var(--maried-coffee)]">
                  Chave de recuperação
                </span>
                <input
                  autoComplete="off"
                  value={recoveryKey}
                  onChange={(event) => {
                    setRecoveryKey(
                      event.target.value
                    );
                  }}
                  required
                  disabled={submitting}
                  className="mt-2 h-12 w-full rounded-xl border border-[var(--maried-sand)] bg-white px-4 font-mono text-sm outline-none transition-colors focus:border-[var(--maried-gold)] disabled:opacity-60"
                />
              </label>

              {error ? (
                <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
                  {error}
                </div>
              ) : null}

              <button
                type="submit"
                disabled={submitting}
                className="flex h-12 w-full items-center justify-center gap-2 rounded-xl bg-[var(--maried-gold)] px-4 text-sm font-medium text-white transition-opacity disabled:opacity-70"
              >
                {submitting ? (
                  <LoaderCircle
                    size={18}
                    className="animate-spin"
                  />
                ) : (
                  <KeyRound
                    size={18}
                  />
                )}
                Continuar
              </button>

              <button
                type="button"
                onClick={handleQuestionsRequest}
                disabled={
                  submitting ||
                  !email.trim()
                }
                className="flex h-12 w-full items-center justify-center gap-2 rounded-xl border border-[var(--maried-sand)] bg-white px-4 text-sm font-medium text-[var(--maried-coffee)] transition-colors hover:border-[var(--maried-gold)] disabled:opacity-60"
              >
                <ShieldQuestion
                  size={18}
                />
                Não lembro minha chave de recuperação
              </button>
            </form>
          ) : null}

          {step === "questions" ? (
            <form
              onSubmit={handleQuestionsSubmit}
              className="space-y-5"
            >
              {questions.map(
                (
                  question,
                  index
                ) => (
                  <label
                    key={question.id}
                    className="block"
                  >
                    <span className="text-xs font-medium text-[var(--maried-coffee)]">
                      {question.question}
                    </span>
                    <input
                      type="password"
                      autoComplete="off"
                      value={answers[index] ?? ""}
                      onChange={(event) => {
                        const next =
                          [
                            ...answers,
                          ];

                        next[index] =
                          event.target.value;

                        setAnswers(
                          next
                        );
                      }}
                      required
                      disabled={submitting}
                      className="mt-2 h-12 w-full rounded-xl border border-[var(--maried-sand)] bg-white px-4 text-sm outline-none transition-colors focus:border-[var(--maried-gold)] disabled:opacity-60"
                    />
                  </label>
                )
              )}

              {error ? (
                <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
                  {error}
                </div>
              ) : null}

              <button
                type="submit"
                disabled={submitting}
                className="flex h-12 w-full items-center justify-center gap-2 rounded-xl bg-[var(--maried-gold)] px-4 text-sm font-medium text-white transition-opacity disabled:opacity-70"
              >
                {submitting ? (
                  <LoaderCircle
                    size={18}
                    className="animate-spin"
                  />
                ) : (
                  <ShieldQuestion
                    size={18}
                  />
                )}
                Validar respostas
              </button>
            </form>
          ) : null}

          {step === "password" ? (
            <form
              onSubmit={handlePasswordSubmit}
              className="space-y-5"
            >
              <label className="block">
                <span className="text-xs font-medium text-[var(--maried-coffee)]">
                  Nova senha
                </span>
                <input
                  type="password"
                  autoComplete="new-password"
                  value={newPassword}
                  onChange={(event) => {
                    setNewPassword(
                      event.target.value
                    );
                  }}
                  required
                  disabled={submitting}
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
                  value={newPasswordConfirm}
                  onChange={(event) => {
                    setNewPasswordConfirm(
                      event.target.value
                    );
                  }}
                  required
                  disabled={submitting}
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

              {error ? (
                <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
                  {error}
                </div>
              ) : null}

              <button
                type="submit"
                disabled={submitting}
                className="flex h-12 w-full items-center justify-center gap-2 rounded-xl bg-[var(--maried-gold)] px-4 text-sm font-medium text-white transition-opacity disabled:opacity-70"
              >
                {submitting ? (
                  <LoaderCircle
                    size={18}
                    className="animate-spin"
                  />
                ) : (
                  <KeyRound
                    size={18}
                  />
                )}
                Alterar senha
              </button>
            </form>
          ) : null}

          {step === "success" && newRecoveryKey ? (
            <div className="space-y-5">
              <div className="rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-800">
                <div className="flex items-center gap-2 font-medium">
                  <CheckCircle2
                    size={18}
                  />
                  Senha alterada com sucesso.
                </div>
              </div>

              <div>
                <div className="text-xs font-medium text-[var(--maried-coffee)]">
                  Nova chave de recuperação
                </div>
                <div className="mt-2 break-all rounded-xl border border-[var(--maried-sand)] bg-white px-4 py-4 font-mono text-sm text-[var(--maried-espresso)]">
                  {newRecoveryKey}
                </div>
              </div>

              <p className="text-sm text-[var(--maried-cocoa)]">
                Sua chave anterior deixou de funcionar. Guarde a nova chave antes de voltar ao login.
              </p>

              <Link
                href="/login"
                onClick={() => {
                  setNewRecoveryKey(
                    null
                  );
                }}
                className="flex h-12 items-center justify-center rounded-xl bg-[var(--maried-gold)] px-4 text-sm font-medium text-white"
              >
                Guardei minha nova chave
              </Link>
            </div>
          ) : null}
        </div>

        <Link
          href="/login"
          className="mt-5 flex items-center justify-center gap-2 text-sm font-medium text-[var(--maried-coffee)] underline-offset-4 hover:underline"
        >
          <ArrowLeft
            size={16}
          />
          Voltar para o login
        </Link>
      </section>
    </main>
  );
}

"use client";

import {
  FormEvent,
  useEffect,
  useState,
} from "react";

import Link from "next/link";

import {
  CheckCircle2,
  Clipboard,
  KeyRound,
  LoaderCircle,
  ShieldCheck,
  ShieldQuestion,
} from "lucide-react";

import {
  AppShell,
} from "@/components/layout/app-shell";

import {
  changeSecurityQuestions,
  getAccountRecoveryStatus,
  rotateRecoveryKey,
  type AccountRecoveryStatus,
} from "@/lib/api";


function formatDate(
  value: string | null
) {
  if (!value) {
    return "-";
  }

  return new Intl.DateTimeFormat(
    "pt-BR",
    {
      day:
        "2-digit",
      month:
        "2-digit",
      year:
        "numeric",
      hour:
        "2-digit",
      minute:
        "2-digit",
    }
  ).format(
    new Date(value)
  );
}


export default function AccountSecurityPage() {
  const [
    status,
    setStatus,
  ] = useState<AccountRecoveryStatus | null>(
    null
  );

  const [
    loading,
    setLoading,
  ] = useState(
    true
  );

  const [
    error,
    setError,
  ] = useState<string | null>(
    null
  );

  const [
    success,
    setSuccess,
  ] = useState<string | null>(
    null
  );

  const [
    currentPasswordForKey,
    setCurrentPasswordForKey,
  ] = useState(
    ""
  );

  const [
    currentPasswordForQuestions,
    setCurrentPasswordForQuestions,
  ] = useState(
    ""
  );

  const [
    question1,
    setQuestion1,
  ] = useState(
    ""
  );

  const [
    answer1,
    setAnswer1,
  ] = useState(
    ""
  );

  const [
    question2,
    setQuestion2,
  ] = useState(
    ""
  );

  const [
    answer2,
    setAnswer2,
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
    submittingKey,
    setSubmittingKey,
  ] = useState(
    false
  );

  const [
    submittingQuestions,
    setSubmittingQuestions,
  ] = useState(
    false
  );

  async function loadStatus() {
    setLoading(
      true
    );
    setError(
      null
    );

    try {
      const data =
        await getAccountRecoveryStatus();

      setStatus(
        data
      );
    } catch {
      setError(
        "Não foi possível carregar as informações de segurança."
      );
    } finally {
      setLoading(
        false
      );
    }
  }

  useEffect(() => {
    let active =
      true;

    getAccountRecoveryStatus()
      .then((data) => {
        if (active) {
          setStatus(
            data
          );
        }
      })
      .catch(() => {
        if (active) {
          setError(
            "Não foi possível carregar as informações de segurança."
          );
        }
      })
      .finally(() => {
        if (active) {
          setLoading(
            false
          );
        }
      });

    return () => {
      active =
        false;
    };
  }, []);

  async function handleRotateKey(
    event: FormEvent<HTMLFormElement>
  ) {
    event.preventDefault();

    if (submittingKey) {
      return;
    }

    setSubmittingKey(
      true
    );
    setError(
      null
    );
    setSuccess(
      null
    );

    try {
      const response =
        await rotateRecoveryKey({
          currentPassword:
            currentPasswordForKey,
        });

      setCurrentPasswordForKey(
        ""
      );
      setStatus(
        response.status
      );
      setNewRecoveryKey(
        response.recovery_key
      );
      setSuccess(
        "Nova chave de recuperação gerada."
      );
    } catch (error) {
      setError(
        error instanceof Error
          ? error.message
          : "Não foi possível gerar uma nova chave agora."
      );
    } finally {
      setSubmittingKey(
        false
      );
    }
  }

  async function handleChangeQuestions(
    event: FormEvent<HTMLFormElement>
  ) {
    event.preventDefault();

    if (submittingQuestions) {
      return;
    }

    setSubmittingQuestions(
      true
    );
    setError(
      null
    );
    setSuccess(
      null
    );

    try {
      const response =
        await changeSecurityQuestions({
          currentPassword:
            currentPasswordForQuestions,
          question1,
          answer1,
          question2,
          answer2,
        });

      setCurrentPasswordForQuestions(
        ""
      );
      setQuestion1(
        ""
      );
      setAnswer1(
        ""
      );
      setQuestion2(
        ""
      );
      setAnswer2(
        ""
      );
      setStatus(
        response.status
      );
      setNewRecoveryKey(
        response.recovery_key
      );
      setSuccess(
        "Perguntas alteradas e nova chave de recuperação gerada."
      );
    } catch (error) {
      setError(
        error instanceof Error
          ? error.message
          : "Não foi possível alterar as perguntas agora."
      );
    } finally {
      setSubmittingQuestions(
        false
      );
    }
  }

  async function copyRecoveryKey() {
    if (
      !newRecoveryKey ||
      typeof navigator === "undefined"
    ) {
      return;
    }

    await navigator.clipboard.writeText(
      newRecoveryKey
    );
    setSuccess(
      "Chave copiada."
    );
  }

  return (
    <AppShell>
      <main className="px-4 py-6 sm:px-6 lg:px-8 lg:py-8">
        <div className="mx-auto max-w-[1000px]">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <h1 className="text-[30px] font-semibold tracking-[-0.035em] text-[var(--maried-espresso)] sm:text-[36px]">
                Segurança da conta
              </h1>

              <p className="mt-2 text-sm text-[var(--maried-cocoa)]">
                Gerencie sua senha e as opções de recuperação da sua conta.
              </p>
            </div>

            <Link
              href="/perfil"
              className="flex h-11 items-center justify-center rounded-xl border border-[var(--maried-sand)] bg-white px-4 text-sm font-medium text-[var(--maried-coffee)]"
            >
              Voltar ao perfil
            </Link>
          </div>

          {error ? (
            <div className="mt-5 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
              {error}
            </div>
          ) : null}

          {success ? (
            <div className="mt-5 flex items-center gap-2 rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-700">
              <CheckCircle2 size={16} />
              {success}
            </div>
          ) : null}

          <section className="maried-card mt-7 p-5">
            <div className="flex items-center gap-2">
              <ShieldCheck
                size={18}
                className="text-[var(--maried-gold)]"
              />
              <h2 className="text-sm font-semibold">
                Recuperação da conta
              </h2>
            </div>

            {loading ? (
              <div className="mt-5 flex min-h-[110px] items-center">
                <LoaderCircle
                  size={22}
                  className="animate-spin text-[var(--maried-gold)]"
                />
              </div>
            ) : status ? (
              <div className="mt-5 grid gap-3 sm:grid-cols-3">
                <div className="rounded-xl border border-[var(--maried-sand)] bg-white px-4 py-3">
                  <div className="text-[10px] font-medium uppercase text-[var(--maried-caramel)]">
                    Chave
                  </div>
                  <div className="mt-1 text-sm font-semibold text-[var(--maried-espresso)]">
                    {status.recovery_key_configured
                      ? "Chave configurada"
                      : "Ainda não configurada"}
                  </div>
                </div>

                <div className="rounded-xl border border-[var(--maried-sand)] bg-white px-4 py-3">
                  <div className="text-[10px] font-medium uppercase text-[var(--maried-caramel)]">
                    Perguntas
                  </div>
                  <div className="mt-1 text-sm font-semibold text-[var(--maried-espresso)]">
                    {status.security_questions_configured
                      ? "2 perguntas configuradas"
                      : "Ainda não configuradas"}
                  </div>
                </div>

                <div className="rounded-xl border border-[var(--maried-sand)] bg-white px-4 py-3">
                  <div className="text-[10px] font-medium uppercase text-[var(--maried-caramel)]">
                    Última rotação
                  </div>
                  <div className="mt-1 text-sm font-semibold text-[var(--maried-espresso)]">
                    {formatDate(
                      status.key_rotated_at
                    )}
                  </div>
                </div>
              </div>
            ) : (
              <button
                type="button"
                onClick={() => {
                  void loadStatus();
                }}
                className="mt-5 h-10 rounded-xl border border-[var(--maried-sand)] bg-white px-4 text-xs font-medium text-[var(--maried-gold)]"
              >
                Tentar novamente
              </button>
            )}

            <p className="mt-4 text-sm text-[var(--maried-cocoa)]">
              Por segurança, sua chave atual não pode ser exibida novamente.
            </p>
          </section>

          {newRecoveryKey ? (
            <section className="maried-card mt-5 p-5">
              <h2 className="text-sm font-semibold text-[var(--maried-espresso)]">
                Nova chave de recuperação
              </h2>

              <div className="mt-3 break-all rounded-xl border border-[var(--maried-sand)] bg-white px-4 py-4 font-mono text-sm text-[var(--maried-espresso)]">
                {newRecoveryKey}
              </div>

              <p className="mt-3 text-sm text-[var(--maried-cocoa)]">
                Sua chave anterior deixará de funcionar assim que esta nova chave for criada. Guarde-a antes de fechar esta tela.
              </p>

              <div className="mt-4 flex flex-col gap-2 sm:flex-row">
                <button
                  type="button"
                  onClick={() => {
                    void copyRecoveryKey();
                  }}
                  className="flex h-11 items-center justify-center gap-2 rounded-xl border border-[var(--maried-sand)] bg-white px-4 text-sm font-medium text-[var(--maried-coffee)]"
                >
                  <Clipboard size={16} />
                  Copiar
                </button>

                <button
                  type="button"
                  onClick={() => {
                    setNewRecoveryKey(
                      null
                    );
                  }}
                  className="flex h-11 items-center justify-center gap-2 rounded-xl bg-[var(--maried-gold)] px-4 text-sm font-medium text-white"
                >
                  <CheckCircle2 size={16} />
                  Guardei minha nova chave
                </button>
              </div>
            </section>
          ) : null}

          <div className="mt-5 grid gap-5 lg:grid-cols-2">
            <form
              onSubmit={handleRotateKey}
              className="maried-card p-5"
            >
              <div className="flex items-center gap-2">
                <KeyRound
                  size={18}
                  className="text-[var(--maried-gold)]"
                />
                <h2 className="text-sm font-semibold">
                  Gerar nova chave
                </h2>
              </div>

              <p className="mt-4 text-sm text-[var(--maried-cocoa)]">
                Sua chave atual deixará de funcionar assim que uma nova chave for criada.
              </p>

              <label className="mt-5 block">
                <span className="text-xs font-medium text-[var(--maried-coffee)]">
                  Senha atual
                </span>
                <input
                  type="password"
                  autoComplete="current-password"
                  value={currentPasswordForKey}
                  onChange={(event) => {
                    setCurrentPasswordForKey(
                      event.target.value
                    );
                  }}
                  required
                  disabled={submittingKey}
                  className="mt-2 h-12 w-full rounded-xl border border-[var(--maried-sand)] bg-white px-4 text-sm outline-none transition-colors focus:border-[var(--maried-gold)] disabled:opacity-60"
                />
              </label>

              <button
                type="submit"
                disabled={submittingKey}
                className="mt-5 flex h-11 w-full items-center justify-center gap-2 rounded-xl bg-[var(--maried-gold)] px-4 text-sm font-medium text-white disabled:opacity-70"
              >
                {submittingKey ? (
                  <LoaderCircle
                    size={16}
                    className="animate-spin"
                  />
                ) : (
                  <KeyRound size={16} />
                )}
                Gerar nova chave
              </button>
            </form>

            <form
              onSubmit={handleChangeQuestions}
              className="maried-card p-5"
            >
              <div className="flex items-center gap-2">
                <ShieldQuestion
                  size={18}
                  className="text-[var(--maried-gold)]"
                />
                <h2 className="text-sm font-semibold">
                  Alterar perguntas
                </h2>
              </div>

              <p className="mt-4 text-sm text-[var(--maried-cocoa)]">
                Ao alterar as perguntas, uma nova Recovery Key também será gerada.
              </p>

              <label className="mt-5 block">
                <span className="text-xs font-medium text-[var(--maried-coffee)]">
                  Senha atual
                </span>
                <input
                  type="password"
                  autoComplete="current-password"
                  value={currentPasswordForQuestions}
                  onChange={(event) => {
                    setCurrentPasswordForQuestions(
                      event.target.value
                    );
                  }}
                  required
                  disabled={submittingQuestions}
                  className="mt-2 h-12 w-full rounded-xl border border-[var(--maried-sand)] bg-white px-4 text-sm outline-none transition-colors focus:border-[var(--maried-gold)] disabled:opacity-60"
                />
              </label>

              {[
                {
                  label: "Nova pergunta 1",
                  value: question1,
                  setter: setQuestion1,
                  type: "text",
                },
                {
                  label: "Nova resposta 1",
                  value: answer1,
                  setter: setAnswer1,
                  type: "password",
                },
                {
                  label: "Nova pergunta 2",
                  value: question2,
                  setter: setQuestion2,
                  type: "text",
                },
                {
                  label: "Nova resposta 2",
                  value: answer2,
                  setter: setAnswer2,
                  type: "password",
                },
              ].map((field) => (
                <label
                  key={field.label}
                  className="mt-4 block"
                >
                  <span className="text-xs font-medium text-[var(--maried-coffee)]">
                    {field.label}
                  </span>
                  <input
                    type={field.type}
                    autoComplete="off"
                    value={field.value}
                    onChange={(event) => {
                      field.setter(
                        event.target.value
                      );
                    }}
                    required
                    disabled={submittingQuestions}
                    className="mt-2 h-12 w-full rounded-xl border border-[var(--maried-sand)] bg-white px-4 text-sm outline-none transition-colors focus:border-[var(--maried-gold)] disabled:opacity-60"
                  />
                </label>
              ))}

              <button
                type="submit"
                disabled={submittingQuestions}
                className="mt-5 flex h-11 w-full items-center justify-center gap-2 rounded-xl bg-[var(--maried-gold)] px-4 text-sm font-medium text-white disabled:opacity-70"
              >
                {submittingQuestions ? (
                  <LoaderCircle
                    size={16}
                    className="animate-spin"
                  />
                ) : (
                  <ShieldQuestion size={16} />
                )}
                Alterar perguntas
              </button>
            </form>
          </div>
        </div>
      </main>
    </AppShell>
  );
}

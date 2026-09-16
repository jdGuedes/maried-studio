"use client";

import {
  FormEvent,
  useEffect,
  useState,
} from "react";

import {
  useRouter,
} from "next/navigation";

import {
  CheckCircle2,
  KeyRound,
  LoaderCircle,
  ShieldCheck,
} from "lucide-react";

import {
  ensureCsrfCookie,
  setupAccountRecovery,
} from "@/lib/api";

import {
  useProfile,
} from "@/providers/profile-provider";


function resolveNextPath() {
  if (
    typeof window ===
    "undefined"
  ) {
    return "/";
  }

  const params =
    new URLSearchParams(
      window.location.search
    );

  const next =
    params.get("next");

  if (
    !next ||
    !next.startsWith("/") ||
    next.startsWith("//") ||
    next.startsWith("/login") ||
    next.startsWith("/esqueci-senha") ||
    next.startsWith("/configurar-recuperacao")
  ) {
    return "/";
  }

  return next;
}


export default function ConfigurarRecuperacaoPage() {
  const router =
    useRouter();

  const {
    profile,
    refreshProfile,
  } = useProfile();

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
    recoveryKey,
    setRecoveryKey,
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

  useEffect(() => {
    if (
      profile?.is_superuser ||
      profile?.recovery_configured
    ) {
      router.replace(
        resolveNextPath()
      );
    }
  }, [
    profile,
    router,
  ]);

  async function handleSubmit(
    event: FormEvent<HTMLFormElement>
  ) {
    event.preventDefault();

    if (
      submitting ||
      recoveryKey
    ) {
      return;
    }

    setSubmitting(
      true
    );
    setError(
      null
    );

    try {
      const response =
        await setupAccountRecovery({
          question1,
          answer1,
          question2,
          answer2,
        });

      setAnswer1(
        ""
      );
      setAnswer2(
        ""
      );
      setRecoveryKey(
        response.recovery_key
      );

    } catch (error) {
      setError(
        error instanceof Error
          ? error.message
          : "Não foi possível configurar a recuperação."
      );

    } finally {
      setSubmitting(
        false
      );
    }
  }

  async function handleAcknowledged() {
    setRecoveryKey(
      null
    );

    await refreshProfile();

    router.replace(
      resolveNextPath()
    );
  }

  return (
    <main className="flex min-h-screen items-center justify-center bg-[var(--maried-ivory)] px-5 py-10">
      <section className="w-full max-w-[560px]">
        <div className="text-center">
          <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-[var(--maried-soft-gold)] text-[var(--maried-gold)]">
            <ShieldCheck
              size={22}
            />
          </div>

          <h1 className="mt-5 text-2xl font-semibold text-[var(--maried-espresso)]">
            Configure a recuperação da conta
          </h1>

          <p className="mt-2 text-sm text-[var(--maried-cocoa)]">
            A chave de recuperação será mostrada uma única vez.
          </p>
        </div>

        <form
          onSubmit={handleSubmit}
          className="maried-card mt-8 space-y-5 p-6"
        >
          {recoveryKey ? (
            <div className="space-y-5">
              <div className="rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-800">
                <div className="flex items-center gap-2 font-medium">
                  <CheckCircle2
                    size={18}
                  />
                  Recuperação configurada.
                </div>
              </div>

              <div>
                <div className="text-xs font-medium text-[var(--maried-coffee)]">
                  Nova chave de recuperação
                </div>

                <div className="mt-2 break-all rounded-xl border border-[var(--maried-sand)] bg-white px-4 py-4 font-mono text-sm text-[var(--maried-espresso)]">
                  {recoveryKey}
                </div>
              </div>

              <p className="text-sm text-[var(--maried-cocoa)]">
                Guarde esta chave em um local seguro. Ela não será exibida novamente.
              </p>

              <button
                type="button"
                onClick={handleAcknowledged}
                className="flex h-12 w-full items-center justify-center gap-2 rounded-xl bg-[var(--maried-gold)] px-4 text-sm font-medium text-white"
              >
                <KeyRound
                  size={18}
                />
                Guardei minha chave
              </button>
            </div>
          ) : (
            <>
              <p className="text-sm text-[var(--maried-cocoa)]">
                Evite perguntas cujas respostas possam ser encontradas em redes sociais ou conhecidas facilmente por outras pessoas.
              </p>

              <label className="block">
                <span className="text-xs font-medium text-[var(--maried-coffee)]">
                  Pergunta 1
                </span>
                <input
                  value={question1}
                  onChange={(event) => {
                    setQuestion1(
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
                  Resposta 1
                </span>
                <input
                  type="password"
                  autoComplete="off"
                  value={answer1}
                  onChange={(event) => {
                    setAnswer1(
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
                  Pergunta 2
                </span>
                <input
                  value={question2}
                  onChange={(event) => {
                    setQuestion2(
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
                  Resposta 2
                </span>
                <input
                  type="password"
                  autoComplete="off"
                  value={answer2}
                  onChange={(event) => {
                    setAnswer2(
                      event.target.value
                    );
                  }}
                  required
                  disabled={submitting}
                  className="mt-2 h-12 w-full rounded-xl border border-[var(--maried-sand)] bg-white px-4 text-sm outline-none transition-colors focus:border-[var(--maried-gold)] disabled:opacity-60"
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
                  <ShieldCheck
                    size={18}
                  />
                )}
                {submitting
                  ? "Configurando..."
                  : "Configurar recuperação"}
              </button>
            </>
          )}
        </form>
      </section>
    </main>
  );
}

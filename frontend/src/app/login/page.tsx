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
  LoaderCircle,
  LogIn,
  Sparkles,
} from "lucide-react";

import {
  ensureCsrfCookie,
  loginUser,
} from "@/lib/api";

import {
  useProfile,
} from "@/providers/profile-provider";

import {
  useCreditWallet,
} from "@/providers/credit-wallet-provider";


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
    next.startsWith("/login")
  ) {
    return "/";
  }

  return next;
}


export default function LoginPage() {
  const router =
    useRouter();

  const {
    profile,
    setAuthenticatedProfile,
  } =
    useProfile();

  const {
    clearWallet,
    refreshWallet,
  } =
    useCreditWallet();

  const [
    email,
    setEmail,
  ] = useState(
    ""
  );

  const [
    password,
    setPassword,
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
      profile
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

    clearWallet();

    try {
      const response =
        await loginUser({
          email:
            email.trim(),
          password,
        });

      setPassword(
        ""
      );

      setAuthenticatedProfile(
        response.user
      );

      await refreshWallet();

      router.replace(
        resolveNextPath()
      );

    } catch (error) {
      setPassword(
        ""
      );

      setError(
        error instanceof Error
          ? error.message
          : "Não foi possível iniciar sua sessão."
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
              Entrar
            </h1>

            <p className="mt-1 text-sm text-[var(--maried-cocoa)]">
              Acesse sua conta para criar imagens.
            </p>
          </div>

          <label className="block">
            <span className="text-xs font-medium text-[var(--maried-coffee)]">
              E-mail
            </span>

            <input
              type="email"
              autoComplete="email"
              value={
                email
              }
              onChange={(event) => {
                setEmail(
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

          <label className="block">
            <span className="text-xs font-medium text-[var(--maried-coffee)]">
              Senha
            </span>

            <input
              type="password"
              autoComplete="current-password"
              value={
                password
              }
              onChange={(event) => {
                setPassword(
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

          {error ? (
            <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
              {error}
            </div>
          ) : null}

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
              <LogIn
                size={
                  18
                }
              />
            )}

            {submitting
              ? "Entrando..."
              : "Entrar"}
          </button>
        </form>
      </section>
    </main>
  );
}

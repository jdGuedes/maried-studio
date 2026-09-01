"use client";

import Link from "next/link";

import {
  CheckCircle2,
  LoaderCircle,
} from "lucide-react";

import {
  useEffect,
  useState,
} from "react";

import { AppShell } from "@/components/layout/app-shell";

import {
  getCurrentSubscription,
  type ClientSubscription,
} from "@/lib/subscription";


export default function SubscriptionSuccessPage() {
  const [
    subscription,
    setSubscription,
  ] = useState<ClientSubscription | null>(
    null
  );

  const [
    checking,
    setChecking,
  ] = useState(
    true
  );


  useEffect(() => {
    let cancelled = false;

    async function poll() {
      for (
        let attempt = 0;
        attempt < 6;
        attempt += 1
      ) {
        const data =
          await getCurrentSubscription();

        if (cancelled) {
          return;
        }

        setSubscription(
          data
        );

        if (
          data.operational_status ===
          "ACTIVE"
        ) {
          setChecking(
            false
          );
          return;
        }

        await new Promise(
          (
            resolve
          ) =>
            window.setTimeout(
              resolve,
              1800
            )
        );
      }

      if (!cancelled) {
        setChecking(
          false
        );
      }
    }

    void poll();

    return () => {
      cancelled = true;
    };
  }, []);


  const active =
    subscription?.operational_status ===
    "ACTIVE";


  return (
    <AppShell>
      <main className="px-4 py-6 sm:px-6 lg:px-8 lg:py-8">
        <div className="mx-auto max-w-[720px]">
          <section className="maried-card p-6 sm:p-8">
            <div className="flex items-center gap-3">
              {checking ? (
                <LoaderCircle
                  size={24}
                  className="animate-spin text-[var(--maried-gold)]"
                />
              ) : (
                <CheckCircle2
                  size={24}
                  className={
                    active
                      ? "text-green-600"
                      : "text-[var(--maried-gold)]"
                  }
                />
              )}

              <h1 className="text-2xl font-semibold text-[var(--maried-espresso)]">
                {active
                  ? "Assinatura ativa"
                  : "Pagamento em confirmacao"}
              </h1>
            </div>

            <p className="mt-4 text-sm leading-6 text-[var(--maried-cocoa)]">
              {active
                ? "Seu pagamento foi confirmado pelo webhook financeiro e o Studio esta liberado."
                : "Estamos aguardando a confirmacao financeira do Stripe. Voce pode atualizar esta pagina em instantes."}
            </p>

            <div className="mt-6 flex flex-wrap gap-3">
              <Link
                href="/"
                className="flex h-11 items-center justify-center rounded-xl bg-[var(--maried-gold)] px-5 text-sm font-medium text-white"
              >
                Ir para o Studio
              </Link>

              <Link
                href="/assinatura"
                className="flex h-11 items-center justify-center rounded-xl border border-[var(--maried-sand)] bg-white px-5 text-sm font-medium text-[var(--maried-gold)]"
              >
                Ver assinatura
              </Link>
            </div>
          </section>
        </div>
      </main>
    </AppShell>
  );
}

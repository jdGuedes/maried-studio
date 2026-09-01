"use client";

import {
  LoaderCircle,
  ShieldCheck,
} from "lucide-react";
import Link from "next/link";
import {
  useSearchParams,
} from "next/navigation";
import {
  useEffect,
  useState,
} from "react";

import {
  getCreditPurchaseBySession,
  type CreditPurchase,
} from "@/lib/subscription";
import {
  useCreditWallet,
} from "@/providers/credit-wallet-provider";


export default function CreditSuccessPage() {
  const params = useSearchParams();
  const sessionId = params.get("session_id");
  const {
    refreshWallet,
  } = useCreditWallet();

  const [
    purchase,
    setPurchase,
  ] = useState<CreditPurchase | null>(
    null
  );
  const [
    loading,
    setLoading,
  ] = useState(true);
  const [
    error,
    setError,
  ] = useState<string | null>(
    null
  );

  const missingSessionError =
    sessionId
      ? null
      : "Sessão de pagamento não informada.";

  const visibleError =
    missingSessionError ??
    error;

  const visibleLoading =
    Boolean(sessionId) &&
    loading;

  useEffect(() => {
    if (!sessionId) {
      return;
    }

    const safeSessionId = sessionId;
    let cancelled = false;
    let attempts = 0;

    async function poll() {
      attempts += 1;

      try {
        const data =
          await getCreditPurchaseBySession(
            safeSessionId
          );

        if (cancelled) {
          return;
        }

        setPurchase(
          data
        );

        if (
          data.status === "PAID" ||
          attempts >= 12
        ) {
          if (data.status === "PAID") {
            await refreshWallet();
          }

          setLoading(false);
          return;
        }

        window.setTimeout(
          () => {
            void poll();
          },
          2500
        );
      } catch (error) {
        if (cancelled) {
          return;
        }

        setError(
          error instanceof Error
            ? error.message
            : "Não foi possível consultar a compra."
        );
        setLoading(false);
      }
    }

    void poll();

    return () => {
      cancelled = true;
    };
  }, [
    refreshWallet,
    sessionId,
  ]);

  return (
    <main className="px-4 py-10 sm:px-6 lg:px-8">
      <section className="maried-card mx-auto max-w-[640px] p-6">
        <div className="flex items-center gap-2">
          <ShieldCheck
            size={20}
            className="text-[var(--maried-gold)]"
          />

          <h1 className="text-xl font-semibold text-[var(--maried-espresso)]">
            Compra de créditos
          </h1>
        </div>

        {visibleLoading ? (
          <div className="mt-6 flex items-center gap-3 text-sm text-[var(--maried-cocoa)]">
            <LoaderCircle
              size={20}
              className="animate-spin text-[var(--maried-gold)]"
            />
            Confirmando pagamento...
          </div>
        ) : visibleError ? (
          <p className="mt-6 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
            {visibleError}
          </p>
        ) : purchase?.status === "PAID" ? (
          <p className="mt-6 rounded-xl border border-green-200 bg-green-50 px-4 py-3 text-sm text-green-700">
            Pagamento confirmado. {purchase.credits_snapshot} crédito(s)
            foram adicionados à sua carteira.
          </p>
        ) : (
          <p className="mt-6 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
            Pagamento ainda não confirmado. Assim que o Stripe enviar a
            confirmação, seus créditos aparecerão na carteira.
          </p>
        )}

        <Link
          href="/creditos"
          className="mt-6 inline-flex h-10 items-center rounded-xl bg-[var(--maried-coffee)] px-4 text-sm font-medium text-white"
        >
          Voltar aos créditos
        </Link>
      </section>
    </main>
  );
}

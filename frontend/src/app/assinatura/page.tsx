"use client";

import {
  AlertTriangle,
  CalendarDays,
  Check,
  CreditCard,
  LoaderCircle,
  X,
} from "lucide-react";

import {
  useEffect,
  useState,
} from "react";

import { AppShell } from "@/components/layout/app-shell";

import {
  cancelSubscription,
  createSubscriptionCheckout,
  getAvailablePlans,
  getCurrentSubscription,
  resumeSubscription,
  SubscriptionApiError,
  type AvailablePlan,
  type ClientSubscription,
} from "@/lib/subscription";


function formatPrice(
  value: string
) {
  return new Intl.NumberFormat(
    "pt-BR",
    {
      style:
        "currency",
      currency:
        "BRL",
    }
  ).format(
    Number(value)
  );
}


function formatDate(
  value: string | null
) {
  if (!value) {
    return "data não informada";
  }

  return new Intl.DateTimeFormat(
    "pt-BR"
  ).format(
    new Date(value)
  );
}


export default function SubscriptionPage() {
  const [
    plans,
    setPlans,
  ] = useState<AvailablePlan[]>([]);

  const [
    subscription,
    setSubscription,
  ] = useState<ClientSubscription | null>(
    null
  );

  const [
    loading,
    setLoading,
  ] = useState(
    true
  );

  const [
    submittingPlanId,
    setSubmittingPlanId,
  ] = useState<string | null>(
    null
  );

  const [
    subscriptionAction,
    setSubscriptionAction,
  ] = useState<"cancel" | "resume" | null>(
    null
  );

  const [
    showCancelConfirm,
    setShowCancelConfirm,
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
    async function load() {
      setLoading(
        true
      );
      setError(
        null
      );

      try {
        const [
          subscriptionData,
          planData,
        ] = await Promise.all([
          getCurrentSubscription(),
          getAvailablePlans(),
        ]);

        setSubscription(
          subscriptionData
        );
        setPlans(
          planData
        );

      } catch (error) {
        setError(
          error instanceof Error
            ? error.message
            : "Nao foi possivel carregar os planos."
        );
      } finally {
        setLoading(
          false
        );
      }
    }

    void load();
  }, []);


  async function subscribe(
    planId: string
  ) {
    if (
      submittingPlanId
    ) {
      return;
    }

    setSubmittingPlanId(
      planId
    );
    setError(
      null
    );

    try {
      const checkout =
        await createSubscriptionCheckout(
          planId
        );

      window.location.assign(
        checkout.url
      );

    } catch (error) {
      if (
        error instanceof SubscriptionApiError &&
        error.data?.code ===
          "CHECKOUT_RETRY_REQUIRED"
      ) {
        setError(
          "Não foi possível iniciar o pagamento. Tente novamente."
        );
        setSubmittingPlanId(
          null
        );
        return;
      }

      setError(
        error instanceof Error
          ? error.message
          : "Nao foi possivel iniciar o Checkout."
      );
      setSubmittingPlanId(
        null
      );
    }
  }


  async function cancelRenewal() {
    if (subscriptionAction) {
      return;
    }

    setSubscriptionAction("cancel");
    setError(null);

    try {
      const data = await cancelSubscription();
      setSubscription(data);
      setShowCancelConfirm(false);
    } catch (error) {
      setError(
        error instanceof Error
          ? error.message
          : "Não foi possível cancelar a renovação."
      );
    } finally {
      setSubscriptionAction(null);
    }
  }


  async function resumeRenewal() {
    if (subscriptionAction) {
      return;
    }

    setSubscriptionAction("resume");
    setError(null);

    try {
      setSubscription(
        await resumeSubscription()
      );
    } catch (error) {
      setError(
        error instanceof Error
          ? error.message
          : "Não foi possível manter a assinatura."
      );
    } finally {
      setSubscriptionAction(null);
    }
  }


  const hasOperationalAccess =
    subscription?.operational_status ===
    "ACTIVE";

  const isFinancialBlocked =
    subscription?.financial_blocked ?? false;

  const isPendingFirstPayment =
    subscription?.status === "PENDING" &&
    Boolean(
      subscription.plan?.id
    );

  const isPaymentRecoveryState =
    subscription?.status === "PAST_DUE" ||
    (
      subscription?.operational_status === "GRACE" &&
      subscription.status !== "PENDING"
    ) ||
    (
      subscription?.operational_status === "BLOCKED" &&
      subscription.status === "PAST_DUE"
    );

  const visiblePlans =
    isPendingFirstPayment
      ? plans.filter(
          (
            plan
          ) =>
            plan.id === subscription?.plan?.id
        )
      : hasOperationalAccess ||
        isPaymentRecoveryState ||
        !subscription?.can_start_subscription
        ? []
        : plans;


  return (
    <AppShell>
      <main className="px-4 py-6 sm:px-6 lg:px-8 lg:py-8">
        <div className="mx-auto max-w-[1100px]">
          <div className="flex flex-col gap-2">
            <h1 className="text-[30px] font-semibold text-[var(--maried-espresso)] sm:text-[36px]">
              Assinatura
            </h1>

            <p className="max-w-2xl text-sm leading-6 text-[var(--maried-cocoa)]">
              Escolha um plano para liberar o Studio. A ativacao acontece apos confirmacao do pagamento pelo Stripe.
            </p>
          </div>

          {error ? (
            <div className="mt-6 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
              {error}
            </div>
          ) : null}

          {hasOperationalAccess ? (
            <div className="mt-6 rounded-xl border border-green-200 bg-green-50 px-4 py-3 text-sm text-green-700">
              {subscription?.cancel_at_period_end ? (
                <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                  <span>
                    Seu plano será encerrado em {formatDate(subscription.current_period_end)}.
                  </span>
                  <button
                    type="button"
                    onClick={() => void resumeRenewal()}
                    disabled={subscriptionAction !== null || isFinancialBlocked}
                    className="inline-flex h-10 items-center justify-center gap-2 rounded-xl bg-[var(--maried-gold)] px-4 text-sm font-medium text-white disabled:cursor-not-allowed disabled:opacity-60"
                  >
                    {subscriptionAction === "resume" ? (
                      <LoaderCircle size={16} className="animate-spin" />
                    ) : (
                      <Check size={16} />
                    )}
                    Manter assinatura
                  </button>
                </div>
              ) : (
                <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                  <span>
                    Sua assinatura está ativa. A renovação é automática pelo Stripe.
                  </span>
                  <button
                    type="button"
                    onClick={() => setShowCancelConfirm(true)}
                    disabled={subscriptionAction !== null}
                    className="inline-flex h-10 items-center justify-center gap-2 rounded-xl border border-green-300 bg-white px-4 text-sm font-medium text-green-800 disabled:cursor-not-allowed disabled:opacity-60"
                  >
                    <X size={16} />
                    Cancelar renovação
                  </button>
                </div>
              )}
            </div>
          ) : null}

          {isFinancialBlocked ? (
            <div className="mt-6 flex flex-col gap-3 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800 sm:flex-row">
              <AlertTriangle size={18} className="mt-0.5 shrink-0" />
              <div className="flex-1">
                <p className="font-medium">
                  Sua conta possui uma contestação financeira em análise.
                </p>
                <p className="mt-1 text-red-700">
                  Você ainda pode consultar seus dados e encerrar futuras cobranças, mas novas criações, assinaturas e compras de créditos ficam indisponíveis até a regularização.
                </p>
              </div>
              {subscription?.status === "ACTIVE" && !subscription.cancel_at_period_end ? (
                <button
                  type="button"
                  onClick={() => setShowCancelConfirm(true)}
                  disabled={subscriptionAction !== null}
                  className="inline-flex h-10 items-center justify-center gap-2 rounded-xl border border-red-300 bg-white px-4 text-sm font-medium text-red-800 disabled:cursor-not-allowed disabled:opacity-60"
                >
                  <X size={16} />
                  Cancelar renovação
                </button>
              ) : null}
            </div>
          ) : null}

          {isPaymentRecoveryState ? (
            <div className="mt-6 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
              Regularize a assinatura atual pelo Stripe. Nao e possivel contratar outro plano por aqui.
            </div>
          ) : null}

          {loading ? (
            <div className="mt-8 flex min-h-[180px] items-center gap-3 text-sm text-[var(--maried-cocoa)]">
              <LoaderCircle
                size={18}
                className="animate-spin text-[var(--maried-gold)]"
              />
              Carregando planos...
            </div>
          ) : (
            <section className="mt-8 grid gap-4 md:grid-cols-3">
              {visiblePlans.map(
                (
                  plan
                ) => (
                  <article
                    key={plan.id}
                    className="maried-card flex min-h-[260px] flex-col p-5"
                  >
                    <div className="flex items-center gap-2 text-[var(--maried-gold)]">
                      <CreditCard
                        size={18}
                      />
                      <span className="text-xs font-medium uppercase tracking-[0.12em]">
                        Plano mensal
                      </span>
                    </div>

                    <h2 className="mt-4 text-xl font-semibold text-[var(--maried-espresso)]">
                      {plan.name}
                    </h2>

                    <p className="mt-2 min-h-[48px] text-sm leading-6 text-[var(--maried-cocoa)]">
                      {plan.description}
                    </p>

                    <div className="mt-5 text-3xl font-semibold text-[var(--maried-espresso)]">
                      {formatPrice(
                        plan.price
                      )}
                    </div>

                    <div className="mt-4 flex items-center gap-2 text-sm text-[var(--maried-coffee)]">
                      <CalendarDays
                        size={16}
                      />
                      {plan.credits_per_cycle} creditos por ciclo
                    </div>

                    <button
                      type="button"
                      disabled={
                        Boolean(submittingPlanId) ||
                        hasOperationalAccess
                      }
                      onClick={() => void subscribe(plan.id)}
                      className="mt-auto flex h-11 items-center justify-center gap-2 rounded-xl bg-[var(--maried-gold)] px-5 text-sm font-medium text-white disabled:cursor-not-allowed disabled:opacity-60"
                    >
                      {submittingPlanId === plan.id ? (
                        <LoaderCircle
                          size={17}
                          className="animate-spin"
                        />
                      ) : (
                        <Check
                          size={17}
                        />
                      )}
                      Assinar
                    </button>
                  </article>
                )
              )}
            </section>
          )}

          {!loading && visiblePlans.length === 0 && !hasOperationalAccess && !isPaymentRecoveryState ? (
            <p className="mt-6 rounded-xl border border-[var(--maried-sand)] bg-white px-4 py-3 text-sm text-[var(--maried-cocoa)]">
              Nenhum plano esta disponivel para pagamento no momento.
            </p>
          ) : null}

          {showCancelConfirm ? (
            <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/35 px-4">
              <div className="w-full max-w-md rounded-xl bg-white p-6 shadow-xl">
                <h2 className="text-lg font-semibold text-[var(--maried-espresso)]">
                  Cancelar renovação
                </h2>
                <p className="mt-3 text-sm leading-6 text-[var(--maried-cocoa)]">
                  Seu plano continuará ativo até o fim do período já pago. Depois dessa data, não haverá nova cobrança automática.
                </p>
                <div className="mt-6 flex justify-end gap-3">
                  <button
                    type="button"
                    onClick={() => setShowCancelConfirm(false)}
                    disabled={subscriptionAction !== null}
                    className="h-10 rounded-xl border border-[var(--maried-sand)] px-4 text-sm font-medium text-[var(--maried-cocoa)] disabled:opacity-60"
                  >
                    Voltar
                  </button>
                  <button
                    type="button"
                    onClick={() => void cancelRenewal()}
                    disabled={subscriptionAction !== null}
                    className="inline-flex h-10 items-center justify-center gap-2 rounded-xl bg-[var(--maried-gold)] px-4 text-sm font-medium text-white disabled:cursor-not-allowed disabled:opacity-60"
                  >
                    {subscriptionAction === "cancel" ? (
                      <LoaderCircle size={16} className="animate-spin" />
                    ) : null}
                    Cancelar renovação
                  </button>
                </div>
              </div>
            </div>
          ) : null}
        </div>
      </main>
    </AppShell>
  );
}

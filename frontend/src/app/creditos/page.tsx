"use client";

import {
  CalendarDays,
  CreditCard,
  LoaderCircle,
  Plus,
  ShieldCheck,
  Sparkles,
} from "lucide-react";

import {
  useEffect,
  useState,
} from "react";

import {
  cancelCreditPurchase,
  createCreditCheckout,
  getCreditPackages,
  getCurrentSubscription,
  type CreditPackage,
  type ClientSubscription,
} from "@/lib/subscription";

import {
  useCreditWallet,
} from "@/providers/credit-wallet-provider";


function formatDate(
  value: string | null
) {
  if (!value) {
    return "Não informado";
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
    }
  ).format(
    new Date(
      value
    )
  );
}


function getSubscriptionStatusLabel(
  subscription: ClientSubscription | null
) {
  if (!subscription?.status) {
    return "Sem assinatura ativa";
  }

  if (
    subscription.operational_status ===
    "GRACE"
  ) {
    return "Em período de tolerância";
  }

  if (
    subscription.operational_status ===
    "BLOCKED"
  ) {
    return "Assinatura bloqueada";
  }

  return "Ativa";
}


export default function CreditsPage() {
  const {
    availableCredits,
    error:
      walletError,
    loading:
      loadingWallet,
    refreshWallet,
    wallet,
  } =
    useCreditWallet();

  const [
    subscription,
    setSubscription,
  ] = useState<ClientSubscription | null>(
    null
  );

  const [
    loadingSubscription,
    setLoadingSubscription,
  ] = useState(
    true
  );

  const [
    subscriptionError,
    setSubscriptionError,
  ] = useState<string | null>(
    null
  );

  const [
    packages,
    setPackages,
  ] = useState<CreditPackage[]>(
    []
  );

  const [
    buyingPackageId,
    setBuyingPackageId,
  ] = useState<string | null>(
    null
  );

  const [
    cancelingPurchaseId,
    setCancelingPurchaseId,
  ] = useState<string | null>(
    null
  );


  useEffect(() => {
    async function loadSubscription() {
      setLoadingSubscription(
        true
      );

      setSubscriptionError(
        null
      );

      try {
        const data =
          await getCurrentSubscription();

        setSubscription(
          data
        );

        setPackages(
          await getCreditPackages()
        );
      } catch (error) {
        setSubscriptionError(
          error instanceof Error
            ? error.message
            : "Não foi possível carregar sua assinatura."
        );
      } finally {
        setLoadingSubscription(
          false
        );
      }
    }

    void loadSubscription();
  }, []);

  async function reloadBilling() {
    const data =
      await getCurrentSubscription();

    setSubscription(
      data
    );

    setPackages(
      await getCreditPackages()
    );
  }

  async function buyPackage(
    packageId: string
  ) {
    setBuyingPackageId(
      packageId
    );
    setSubscriptionError(
      null
    );

    try {
      const checkout =
        await createCreditCheckout(
          packageId
        );

      window.location.assign(
        checkout.url
      );
    } catch (error) {
      setSubscriptionError(
        error instanceof Error
          ? error.message
          : "Não foi possível iniciar a compra."
      );
      setBuyingPackageId(
        null
      );
    }
  }


  async function cancelPendingPurchase(
    purchaseId: string
  ) {
    setCancelingPurchaseId(
      purchaseId
    );
    setSubscriptionError(
      null
    );

    try {
      await cancelCreditPurchase(
        purchaseId
      );
      await reloadBilling();
    } catch (error) {
      setSubscriptionError(
        error instanceof Error
          ? error.message
          : "Não foi possível cancelar a tentativa."
      );
    } finally {
      setCancelingPurchaseId(
        null
      );
    }
  }

  return (
    <main className="px-4 py-6 sm:px-6 lg:px-8 lg:py-8">
      <div className="mx-auto max-w-[1100px]">

        <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <h1 className="text-[30px] font-semibold tracking-[-0.035em] text-[var(--maried-espresso)] sm:text-[36px]">
              Meus créditos
            </h1>

            <p className="mt-2 text-sm text-[var(--maried-cocoa)]">
              Acompanhe seu saldo disponível
              e entenda a diferença entre créditos
              do plano e créditos comprados.
            </p>
          </div>

          <button
            type="button"
            onClick={() => {
              document
                .getElementById(
                  "pacotes-creditos"
                )
                ?.scrollIntoView({
                  behavior:
                    "smooth",
                });
            }}
            className="flex h-11 items-center justify-center gap-2 rounded-xl border border-[var(--maried-sand)] bg-white px-5 text-sm font-medium text-[var(--maried-gold)]"
          >
            <Plus
              size={
                17
              }
            />
            Adicionar créditos
          </button>
        </div>


        <section className="maried-card mt-7 p-5 sm:p-6">
          <div className="flex items-center gap-2">
            <Sparkles
              size={
                18
              }
              className="text-[var(--maried-gold)]"
            />

            <h2 className="text-sm font-semibold">
              Total disponível
            </h2>
          </div>

          {loadingWallet ? (
            <div className="mt-6 flex min-h-[120px] items-center">
              <LoaderCircle
                size={
                  26
                }
                className="animate-spin text-[var(--maried-gold)]"
              />
            </div>
          ) : (
            <>
              <div className="mt-6 text-5xl font-semibold tracking-[-0.045em] text-[var(--maried-espresso)]">
                {availableCredits ??
                  0}
              </div>

              <p className="mt-2 text-xs leading-5 text-[var(--maried-cocoa)]">
                Este é o saldo utilizável da sua carteira.
                Ele soma os créditos disponíveis do plano
                e os créditos comprados disponíveis.
              </p>

              {walletError ? (
                <div className="mt-4 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-xs text-red-700">
                  {walletError}
                </div>
              ) : null}
            </>
          )}
        </section>


        <div className="mt-5 grid gap-5 lg:grid-cols-2">

          <section className="maried-card p-5">
            <div className="flex items-center gap-2">
              <CreditCard
                size={
                  17
                }
                className="text-[var(--maried-gold)]"
              />

              <h2 className="text-sm font-semibold">
                Créditos do plano
              </h2>
            </div>

            {loadingWallet ? (
              <LoaderCircle
                size={
                  22
                }
                className="mt-6 animate-spin text-[var(--maried-gold)]"
              />
            ) : (
              <>
                <div className="mt-6 text-4xl font-semibold tracking-[-0.04em] text-[var(--maried-espresso)]">
                  {wallet?.available_plan_balance ??
                    0}
                </div>

                <p className="mt-2 text-xs leading-5 text-[var(--maried-cocoa)]">
                  {subscription?.status
                    ? (
                        <>
                          Seu plano disponibiliza{" "}
                          {subscription.credits_per_cycle ??
                            0}{" "}
                          créditos a cada novo ciclo.
                          Créditos não utilizados do plano
                          não acumulam.
                        </>
                      )
                    : "Sem plano ativo vinculado à sua conta."}
                </p>

                <div className="mt-4 rounded-xl bg-[var(--maried-cream)] px-3 py-3 text-xs text-[var(--maried-coffee)]">
                  Próxima renovação:{" "}
                  {formatDate(
                    subscription?.next_billing_at ??
                      null
                  )}
                </div>
              </>
            )}
          </section>


          <section className="maried-card p-5">
            <div className="flex items-center gap-2">
              <ShieldCheck
                size={
                  17
                }
                className="text-[var(--maried-gold)]"
              />

              <h2 className="text-sm font-semibold">
                Créditos comprados
              </h2>
            </div>

            {loadingWallet ? (
              <LoaderCircle
                size={
                  22
                }
                className="mt-6 animate-spin text-[var(--maried-gold)]"
              />
            ) : (
              <>
                <div className="mt-6 text-4xl font-semibold tracking-[-0.04em] text-[var(--maried-espresso)]">
                  {wallet?.available_purchased_balance ??
                    0}
                </div>

                <p className="mt-2 text-xs leading-5 text-[var(--maried-cocoa)]">
                  Créditos comprados não expiram.
                  Eles permanecem disponíveis até serem
                  utilizados.
                </p>

                <div className="mt-4 rounded-xl bg-[var(--maried-cream)] px-3 py-3 text-xs text-[var(--maried-coffee)]">
                  Os créditos do plano são utilizados antes
                  dos créditos comprados.
                </div>
              </>
            )}
          </section>

        </div>


        {wallet &&
        wallet.reserved_balance >
          0 ? (
          <section className="maried-card mt-5 p-5">
            <h2 className="text-sm font-semibold">
              Créditos reservados
            </h2>

            <p className="mt-2 text-xs leading-5 text-[var(--maried-cocoa)]">
              {wallet.reserved_balance} crédito(s) estão
              reservados em criações em processamento.
              Isso não significa consumo definitivo.
            </p>
          </section>
        ) : null}


        <section className="maried-card mt-5 p-5">
          <div className="flex items-center gap-2">
            <CalendarDays
              size={
                17
              }
              className="text-[var(--maried-gold)]"
            />

            <h2 className="text-sm font-semibold">
              Assinatura
            </h2>
          </div>

          {loadingSubscription ? (
            <LoaderCircle
              size={
                22
              }
              className="mt-6 animate-spin text-[var(--maried-gold)]"
            />
          ) : subscriptionError ? (
            <div className="mt-5 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-xs text-red-700">
              {subscriptionError}
            </div>
          ) : (
            <>
              <div className="mt-5 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
                <div>
                  <div className="text-[11px] text-[var(--maried-cocoa)]">
                    Plano atual
                  </div>

                  <div className="mt-1 text-sm font-semibold text-[var(--maried-espresso)]">
                    {subscription?.plan_name ??
                      "Sem assinatura ativa"}
                  </div>
                </div>

                <div>
                  <div className="text-[11px] text-[var(--maried-cocoa)]">
                    Status
                  </div>

                  <div className="mt-1 text-sm font-semibold text-[var(--maried-espresso)]">
                    {getSubscriptionStatusLabel(
                      subscription
                    )}
                  </div>
                </div>

                <div>
                  <div className="text-[11px] text-[var(--maried-cocoa)]">
                    Créditos por ciclo
                  </div>

                  <div className="mt-1 text-sm font-semibold text-[var(--maried-espresso)]">
                    {subscription?.credits_per_cycle ??
                      0}
                  </div>
                </div>

                <div>
                  <div className="text-[11px] text-[var(--maried-cocoa)]">
                    Próxima renovação
                  </div>

                  <div className="mt-1 text-sm font-semibold text-[var(--maried-espresso)]">
                    {formatDate(
                      subscription?.next_billing_at ??
                        null
                    )}
                  </div>
                </div>
              </div>


              {subscription?.status ? (
                <div className="mt-5 rounded-xl bg-[var(--maried-cream)] px-4 py-3 text-xs leading-5 text-[var(--maried-coffee)]">
                  Ciclo atual:{" "}
                  {formatDate(
                    subscription.current_period_start
                  )}{" "}
                  →{" "}
                  {formatDate(
                    subscription.current_period_end
                  )}
                </div>
              ) : (
                <p className="mt-4 text-xs leading-5 text-[var(--maried-cocoa)]">
                  Nenhum plano ativo está vinculado à sua
                  conta.
                </p>
              )}


              {subscription?.operational_status ===
              "GRACE" ? (
                <p className="mt-5 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-xs leading-5 text-amber-800">
                  Regularize sua assinatura até{" "}
                  {formatDate(
                    subscription.grace_until
                  )}{" "}
                  para evitar interrupção do Studio.
                </p>
              ) : null}


              {subscription?.operational_status ===
              "BLOCKED" &&
              subscription.status ? (
                <p className="mt-5 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-xs leading-5 text-red-700">
                  Regularize sua assinatura para voltar
                  a criar imagens. Seus dados e créditos
                  permanecem preservados.
                </p>
              ) : null}
            </>
          )}
        </section>


        <section id="pacotes-creditos" className="maried-card mt-5 p-5">
          <div className="flex items-center gap-2">
            <Plus
              size={
                17
              }
              className="text-[var(--maried-gold)]"
            />

            <h2 className="text-sm font-semibold">
              Comprar créditos extras
            </h2>
          </div>

          <div className="mt-4 rounded-xl bg-[var(--maried-cream)] px-4 py-3 text-xs leading-5 text-[var(--maried-coffee)]">
            Limite do ciclo:{" "}
            {subscription?.extra_credit_limit_per_cycle ??
              0}{" "}
            créditos. Comprados/pendentes neste ciclo:{" "}
            {subscription?.paid_credits_this_cycle ??
              0}
            /
            {subscription?.pending_credits_this_cycle ??
              0}
            . Restante:{" "}
            {subscription?.remaining_extra_credits ??
              0}
            .
          </div>

          {!subscription?.can_purchase_credits ? (
            <p className="mt-4 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-xs leading-5 text-amber-800">
              Compra de créditos extras disponível apenas
              para assinatura ativa.
            </p>
          ) : null}

          <div className="mt-5 grid gap-4 md:grid-cols-3">
            {packages.map((creditPackage) => (
              <div
                key={creditPackage.id}
                className="rounded-xl border border-[var(--maried-sand)] bg-white p-4"
              >
                <div className="text-sm font-semibold text-[var(--maried-espresso)]">
                  {creditPackage.name}
                </div>

                <div className="mt-3 text-3xl font-semibold tracking-[-0.035em] text-[var(--maried-espresso)]">
                  {creditPackage.credits}
                </div>

                <p className="mt-1 text-xs text-[var(--maried-cocoa)]">
                  créditos extras
                </p>

                <div className="mt-4 text-sm font-medium text-[var(--maried-coffee)]">
                  R$ {creditPackage.price}
                </div>

                {creditPackage.pending_purchase ? (
                  <div className="mt-4 space-y-2">
                    <div className="rounded-xl border border-amber-200 bg-amber-50 px-3 py-2 text-xs font-medium text-amber-800">
                      Pagamento pendente
                    </div>

                    <button
                      type="button"
                      disabled={
                        buyingPackageId === creditPackage.id
                      }
                      onClick={() => {
                        void buyPackage(
                          creditPackage.id
                        );
                      }}
                      className="h-10 w-full rounded-xl bg-[var(--maried-coffee)] px-4 text-xs font-medium text-white disabled:opacity-50"
                    >
                      {buyingPackageId === creditPackage.id
                        ? "Abrindo Stripe..."
                        : "Continuar pagamento"}
                    </button>

                    <button
                      type="button"
                      disabled={
                        cancelingPurchaseId ===
                        creditPackage.pending_purchase.id
                      }
                      onClick={() => {
                        void cancelPendingPurchase(
                          creditPackage.pending_purchase!.id
                        );
                      }}
                      className="h-10 w-full rounded-xl border border-[var(--maried-sand)] bg-white px-4 text-xs font-medium text-[var(--maried-gold)] disabled:opacity-50"
                    >
                      {cancelingPurchaseId ===
                      creditPackage.pending_purchase.id
                        ? "Cancelando..."
                        : "Cancelar tentativa"}
                    </button>
                  </div>
                ) : (
                  <button
                    type="button"
                    disabled={
                      !creditPackage.checkout_available ||
                      buyingPackageId === creditPackage.id
                    }
                    onClick={() => {
                      void buyPackage(
                        creditPackage.id
                      );
                    }}
                    className="mt-4 h-10 w-full rounded-xl bg-[var(--maried-coffee)] px-4 text-xs font-medium text-white disabled:opacity-50"
                  >
                    {buyingPackageId === creditPackage.id
                      ? "Abrindo Stripe..."
                      : "Comprar"}
                  </button>
                )}
              </div>
            ))}
          </div>

          {!loadingSubscription &&
          packages.length === 0 ? (
            <p className="mt-4 text-xs leading-5 text-[var(--maried-cocoa)]">
              Nenhum pacote de créditos está disponível no
              momento.
            </p>
          ) : null}
        </section>


        <section className="maried-card mt-5 p-5">
          <h2 className="text-sm font-semibold">
            Histórico
          </h2>

          <p className="mt-2 text-xs leading-5 text-[var(--maried-cocoa)]">
            O histórico de movimentações ficará disponível
            quando existir um endpoint cliente seguro para
            consultar transações da própria organização.
          </p>

          <button
            type="button"
            onClick={() => {
              void refreshWallet();
            }}
            className="mt-5 h-10 rounded-xl border border-[var(--maried-sand)] bg-white px-4 text-xs font-medium text-[var(--maried-gold)]"
          >
            Atualizar saldo
          </button>
        </section>

      </div>
    </main>
  );
}

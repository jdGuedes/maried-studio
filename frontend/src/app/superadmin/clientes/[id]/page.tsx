"use client";

import { useParams } from "next/navigation";
import { useEffect, useState, type FormEvent } from "react";

import {
  AdminCard,
  EmptyState,
  MetricCard,
  StatusMessage,
  SuperAdminShell,
} from "@/components/superadmin/superadmin-shell";
import {
  activateSuperAdminSubscription,
  adjustSuperAdminCredits,
  getSuperAdminClient,
  getSuperAdminPlans,
  reconcileSuperAdminClientStripe,
  updateSuperAdminOrganization,
  updateSuperAdminUser,
  type SuperAdminClientDetail,
  type SuperAdminPlan,
} from "@/lib/api";


function formatDate(value?: string | null) {
  if (!value) {
    return "-";
  }

  return new Intl.DateTimeFormat("pt-BR", {
    dateStyle: "short",
  }).format(new Date(value));
}


export default function SuperAdminClienteDetalhePage() {
  const params =
    useParams<{ id: string }>();

  const clientId =
    params.id;

  const [
    client,
    setClient,
  ] = useState<SuperAdminClientDetail | null>(null);
  const [
    plans,
    setPlans,
  ] = useState<SuperAdminPlan[]>([]);
  const [
    planId,
    setPlanId,
  ] = useState("");
  const [
    creditType,
    setCreditType,
  ] = useState<"PLAN" | "PURCHASED">("PLAN");
  const [
    operation,
    setOperation,
  ] = useState<"ADD" | "REMOVE">("ADD");
  const [
    quantity,
    setQuantity,
  ] = useState("");
  const [
    reason,
    setReason,
  ] = useState("");
  const [
    loading,
    setLoading,
  ] = useState(true);
  const [
    saving,
    setSaving,
  ] = useState(false);
  const [
    error,
    setError,
  ] = useState<string | null>(null);
  const [
    message,
    setMessage,
  ] = useState<string | null>(null);

  async function load() {
    const [
      clientData,
      planData,
    ] = await Promise.all([
      getSuperAdminClient(clientId),
      getSuperAdminPlans(),
    ]);

    setClient(clientData);
    setPlans(planData);
    setPlanId(
      clientData.subscription?.plan ??
      planData.find((plan) => plan.is_active)?.id ??
      ""
    );
  }

  useEffect(() => {
    let active = true;

    void (async () => {
      try {
        const [
          clientData,
          planData,
        ] = await Promise.all([
          getSuperAdminClient(clientId),
          getSuperAdminPlans(),
        ]);

        if (!active) {
          return;
        }

        setClient(clientData);
        setPlans(planData);
        setPlanId(
          clientData.subscription?.plan ??
          planData.find((plan) => plan.is_active)?.id ??
          ""
        );
      } catch (error) {
        if (active) {
          setError(error instanceof Error ? error.message : "Erro ao carregar cliente.");
        }
      } finally {
        if (active) {
          setLoading(false);
        }
      }
    })();

    return () => {
      active = false;
    };
  }, [clientId]);

  async function runAction(
    action: () => Promise<void>,
    success: string
  ) {
    setSaving(true);
    setError(null);
    setMessage(null);

    try {
      await action();
      await load();
      if (success) {
        setMessage(success);
      }
    } catch (error) {
      setError(error instanceof Error ? error.message : "Operacao nao concluida.");
    } finally {
      setSaving(false);
    }
  }

  async function handleCreditSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (!client) {
      return;
    }

    const parsedQuantity =
      Number.parseInt(quantity, 10);

    if (Number.isNaN(parsedQuantity) || parsedQuantity <= 0) {
      setError("Informe uma quantidade positiva.");
      return;
    }

    if (!window.confirm("Confirmar ajuste manual de creditos?")) {
      return;
    }

    await runAction(
      async () => {
        await adjustSuperAdminCredits({
          organization_id: client.id,
          balance_type: creditType,
          amount: operation === "ADD" ? parsedQuantity : -parsedQuantity,
          reason,
        });
        setQuantity("");
        setReason("");
      },
      "Creditos ajustados com auditoria."
    );
  }

  async function handleStripeReconcile() {
    if (!client) {
      return;
    }

    if (
      !window.confirm(
        "Consultar o Stripe e sincronizar o estado financeiro desta assinatura?\n\nEsta acao nao cria uma nova cobranca."
      )
    ) {
      return;
    }

    await runAction(
      async () => {
        const result =
          await reconcileSuperAdminClientStripe(
            client.id
          );

        setMessage(
          result.financial_blocked
            ? "Stripe sincronizado. Conta bloqueada por contestacao financeira."
            : result.disputes_reconciled
              ? "Stripe sincronizado. Disputas financeiras atualizadas."
              : result.applied
                ? "Pagamento encontrado no Stripe e assinatura sincronizada."
                : "Esta assinatura ja esta sincronizada com o Stripe."
        );
      },
      ""
    );
  }

  return (
    <SuperAdminShell
      title={client?.name ?? "Cliente"}
      subtitle="Ficha operacional: conta, assinatura, creditos e uso."
    >
      {error ? <StatusMessage text={error} /> : null}
      {message ? <StatusMessage text={message} tone="success" /> : null}

      {loading ? (
        <AdminCard>Carregando cliente...</AdminCard>
      ) : client ? (
        <div className="space-y-5">
          {client.subscription.operational_status === "FINANCIAL_BLOCK" ? (
            <StatusMessage
              text="Conta bloqueada por contestacao financeira."
              tone="error"
            />
          ) : null}

          <div className="grid gap-3 md:grid-cols-4">
            <MetricCard label="Conta" value={client.is_active ? "Ativa" : "Bloqueada"} />
            <MetricCard label="Usuario" value={client.user?.is_active ? "Ativo" : "Bloqueado"} />
            <MetricCard label="Operacao" value={client.subscription.operational_status} />
            <MetricCard label="Disponiveis" value={client.wallet.available_balance} />
          </div>

          <div className="grid gap-5 xl:grid-cols-2">
            <AdminCard>
              <h2 className="mb-4 text-sm font-semibold text-[var(--maried-espresso)]">Conta</h2>
              <Info label="Nome" value={client.name} />
              <Info label="Organization" value={client.slug} />
              <Info label="E-mail" value={client.user?.email ?? "-"} />

              <div className="mt-4 flex flex-wrap gap-2">
                <button
                  disabled={saving}
                  onClick={() => {
                    if (window.confirm("Confirmar alteracao de status da conta?")) {
                      void runAction(
                        () => updateSuperAdminOrganization(client.id, { is_active: !client.is_active }).then(() => undefined),
                        "Status da conta atualizado."
                      );
                    }
                  }}
                  className="h-10 rounded-xl border border-[var(--maried-sand)] px-4 text-sm"
                  type="button"
                >
                  {client.is_active ? "Bloquear conta" : "Reativar conta"}
                </button>

                {client.user ? (
                  <button
                    disabled={saving}
                    onClick={() => {
                      if (window.confirm("Confirmar alteracao de status do usuario?")) {
                        void runAction(
                          () => updateSuperAdminUser(client.user!.id, { is_active: !client.user!.is_active }).then(() => undefined),
                          "Status do usuario atualizado."
                        );
                      }
                    }}
                    className="h-10 rounded-xl border border-[var(--maried-sand)] px-4 text-sm"
                    type="button"
                  >
                    {client.user.is_active ? "Bloquear usuario" : "Reativar usuario"}
                  </button>
                ) : null}
              </div>
            </AdminCard>

            <AdminCard>
              <h2 className="mb-4 text-sm font-semibold text-[var(--maried-espresso)]">Assinatura</h2>
              <Info label="Plano" value={client.subscription.plan_name ?? "-"} />
              <Info label="Status persistido" value={client.subscription.status ?? "-"} />
              <Info label="Operational status" value={client.subscription.operational_status} />
              <Info label="Current period end" value={formatDate(client.subscription.current_period_end)} />
              <Info label="Next billing" value={formatDate(client.subscription.next_billing_at)} />
              <Info label="Grace ate" value={formatDate(client.subscription.grace_until)} />

              <div className="mt-4 flex flex-col gap-2 sm:flex-row">
                <select
                  value={planId}
                  onChange={(event) => setPlanId(event.target.value)}
                  className="h-10 rounded-xl border border-[var(--maried-sand)] bg-white px-3 text-sm"
                >
                  {plans.filter((plan) => plan.is_active).map((plan) => (
                    <option key={plan.id} value={plan.id}>{plan.name}</option>
                  ))}
                </select>
                {client.subscription.id ? (
                  <button
                    disabled
                    className="h-10 rounded-xl bg-[var(--maried-coffee)] px-4 text-sm text-white disabled:opacity-60"
                    type="button"
                  >
                    {client.subscription.status === "ACTIVE"
                      ? "Renovacao automatica"
                      : client.subscription.status === "PENDING"
                        ? "Primeiro pagamento pelo cliente"
                        : "Regularizacao via Stripe"}
                  </button>
                ) : (
                  <button
                    disabled={saving || !planId}
                    onClick={() => {
                      void runAction(
                        () => activateSuperAdminSubscription(client.id, planId).then(() => undefined),
                        "Plano pendente criado."
                      );
                    }}
                    className="h-10 rounded-xl bg-[var(--maried-coffee)] px-4 text-sm text-white disabled:opacity-60"
                    type="button"
                  >
                    Criar pendencia
                  </button>
                )}
                {client.stripe_customer_id ? (
                  <button
                    disabled={saving}
                    onClick={() => {
                      void handleStripeReconcile();
                    }}
                    className="h-10 rounded-xl border border-[var(--maried-sand)] px-4 text-sm disabled:opacity-60"
                    type="button"
                  >
                    Sincronizar com Stripe
                  </button>
                ) : null}
              </div>
            </AdminCard>
          </div>

          <div className="grid gap-5 xl:grid-cols-2">
            <AdminCard>
              <h2 className="mb-4 text-sm font-semibold text-[var(--maried-espresso)]">Creditos</h2>
              <div className="grid gap-3 sm:grid-cols-2">
                <MetricCard label="Plano" value={client.wallet.plan_balance} />
                <MetricCard label="Comprados" value={client.wallet.purchased_balance} />
                <MetricCard label="Reservados" value={client.wallet.reserved_balance} />
                <MetricCard label="Disponiveis" value={client.wallet.available_balance} />
              </div>
            </AdminCard>

            <AdminCard>
              <h2 className="mb-4 text-sm font-semibold text-[var(--maried-espresso)]">Ajuste manual</h2>
              <form onSubmit={(event) => void handleCreditSubmit(event)} className="space-y-3">
                <div className="grid gap-3 sm:grid-cols-2">
                  <Select value={creditType} onChange={(value) => setCreditType(value as "PLAN" | "PURCHASED")} options={[["PLAN", "Plano"], ["PURCHASED", "Comprados"]]} />
                  <Select value={operation} onChange={(value) => setOperation(value as "ADD" | "REMOVE")} options={[["ADD", "Adicionar"], ["REMOVE", "Remover"]]} />
                </div>
                <input required type="number" min="1" value={quantity} onChange={(event) => setQuantity(event.target.value)} placeholder="Quantidade" className="h-10 w-full rounded-xl border border-[var(--maried-sand)] px-3 text-sm" />
                <input required value={reason} onChange={(event) => setReason(event.target.value)} placeholder="Motivo obrigatorio" className="h-10 w-full rounded-xl border border-[var(--maried-sand)] px-3 text-sm" />
                <button disabled={saving} type="submit" className="h-10 w-full rounded-xl bg-[var(--maried-coffee)] px-4 text-sm text-white disabled:opacity-60">
                  Confirmar ajuste
                </button>
              </form>
            </AdminCard>
          </div>

          <AdminCard>
            <h2 className="mb-4 text-sm font-semibold text-[var(--maried-espresso)]">Uso</h2>
            <div className="grid gap-3 sm:grid-cols-2">
              <MetricCard label="Pecas" value={client.usage.products_count} />
              <MetricCard label="Geracoes" value={client.usage.generations_count} />
            </div>
          </AdminCard>
        </div>
      ) : (
        <EmptyState>Cliente nao encontrado.</EmptyState>
      )}
    </SuperAdminShell>
  );
}


function Info({
  label,
  value,
}: {
  label: string;
  value: string | number;
}) {
  return (
    <div className="flex justify-between gap-3 border-b border-[var(--maried-sand)] py-2 text-sm">
      <span className="text-[var(--maried-cocoa)]">{label}</span>
      <span className="text-right font-medium text-[var(--maried-espresso)]">{value}</span>
    </div>
  );
}


function Select({
  value,
  onChange,
  options,
}: {
  value: string;
  onChange: (value: string) => void;
  options: Array<[string, string]>;
}) {
  return (
    <select
      value={value}
      onChange={(event) => onChange(event.target.value)}
      className="h-10 rounded-xl border border-[var(--maried-sand)] bg-white px-3 text-sm"
    >
      {options.map(([optionValue, label]) => (
        <option key={optionValue} value={optionValue}>{label}</option>
      ))}
    </select>
  );
}

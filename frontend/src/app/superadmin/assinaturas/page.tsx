"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import {
  AdminCard,
  EmptyState,
  StatusMessage,
  SuperAdminShell,
} from "@/components/superadmin/superadmin-shell";
import {
  getSuperAdminSubscriptions,
  renewSuperAdminSubscription,
  type SuperAdminSubscription,
} from "@/lib/api";


function formatDate(value?: string | null) {
  return value
    ? new Intl.DateTimeFormat("pt-BR", { dateStyle: "short" }).format(new Date(value))
    : "-";
}


export default function SuperAdminAssinaturasPage() {
  const [subscriptions, setSubscriptions] = useState<SuperAdminSubscription[]>([]);
  const [filter, setFilter] = useState("ALL");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    setSubscriptions(await getSuperAdminSubscriptions());
  }

  useEffect(() => {
    let active = true;

    void (async () => {
      try {
        const data = await getSuperAdminSubscriptions();

        if (active) {
          setSubscriptions(data);
        }
      } catch (error) {
        if (active) {
          setError(error instanceof Error ? error.message : "Erro ao carregar assinaturas.");
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
  }, []);

  const filtered =
    subscriptions.filter((subscription) => (
      filter === "ALL" ||
      subscription.status === filter ||
      subscription.operational_status === filter
    ));

  async function renew(subscriptionId: string) {
    if (!window.confirm("Confirmar renovação da assinatura?")) {
      return;
    }

    setSaving(true);
    setError(null);

    try {
      await renewSuperAdminSubscription(subscriptionId);
      await load();
    } catch (error) {
      setError(error instanceof Error ? error.message : "Erro ao renovar assinatura.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <SuperAdminShell title="Assinaturas" subtitle="Consulta global com status persistido e status operacional calculado.">
      {error ? <StatusMessage text={error} /> : null}

      <AdminCard>
        <div className="mb-4 flex justify-end">
          <select value={filter} onChange={(event) => setFilter(event.target.value)} className="h-10 rounded-xl border border-[var(--maried-sand)] bg-white px-3 text-sm">
            <option value="ALL">Todas</option>
            <option value="ACTIVE">Active</option>
            <option value="GRACE">Grace</option>
            <option value="BLOCKED">Blocked</option>
            <option value="CANCELED">Canceled</option>
          </select>
        </div>

        {loading ? (
          <EmptyState>Carregando assinaturas...</EmptyState>
        ) : filtered.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[860px] text-left text-sm">
              <thead className="text-xs text-[var(--maried-cocoa)]">
                <tr>
                  <th className="py-2">Cliente</th>
                  <th>Plano</th>
                  <th>Status</th>
                  <th>Operação</th>
                  <th>Vencimento</th>
                  <th>Próxima cobrança</th>
                  <th></th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[var(--maried-sand)]">
                {filtered.map((subscription) => (
                  <tr key={subscription.id}>
                    <td className="py-3 font-medium text-[var(--maried-espresso)]">{subscription.organization_name}</td>
                    <td>{subscription.plan_name}</td>
                    <td>{subscription.status}</td>
                    <td>{subscription.operational_status}</td>
                    <td>{formatDate(subscription.current_period_end)}</td>
                    <td>{formatDate(subscription.next_billing_at)}</td>
                    <td className="space-x-3 text-right">
                      <Link href={`/superadmin/clientes/${subscription.organization}`} className="font-medium text-[var(--maried-gold)]">Ver cliente</Link>
                      <button disabled={saving} type="button" onClick={() => void renew(subscription.id)} className="font-medium text-[var(--maried-gold)] disabled:opacity-60">Renovar</button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <EmptyState>Nenhuma assinatura encontrada.</EmptyState>
        )}
      </AdminCard>
    </SuperAdminShell>
  );
}

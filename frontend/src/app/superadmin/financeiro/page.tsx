"use client";

import { useEffect, useState } from "react";

import {
  AdminCard,
  EmptyState,
  StatusMessage,
  SuperAdminShell,
} from "@/components/superadmin/superadmin-shell";
import {
  getSuperAdminPaymentDisputes,
  type SuperAdminPaymentDispute,
} from "@/lib/api";


function formatMoney(dispute: SuperAdminPaymentDispute) {
  return new Intl.NumberFormat(
    "pt-BR",
    {
      style: "currency",
      currency: dispute.currency || "BRL",
    }
  ).format(
    dispute.amount / 100
  );
}


function formatDate(value: string | null) {
  if (!value) {
    return "-";
  }

  return new Intl.DateTimeFormat(
    "pt-BR"
  ).format(
    new Date(value)
  );
}


export default function SuperAdminFinanceiroPage() {
  const [
    disputes,
    setDisputes,
  ] = useState<SuperAdminPaymentDispute[]>([]);
  const [
    loading,
    setLoading,
  ] = useState(true);
  const [
    error,
    setError,
  ] = useState<string | null>(null);

  useEffect(() => {
    let active = true;

    void (async () => {
      try {
        const data =
          await getSuperAdminPaymentDisputes();

        if (active) {
          setDisputes(data);
        }
      } catch (error) {
        if (active) {
          setError(
            error instanceof Error
              ? error.message
              : "Erro ao carregar disputas."
          );
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

  return (
    <SuperAdminShell
      title="Financeiro"
      subtitle="Disputas Stripe e bloqueios financeiros derivados."
    >
      {error ? (
        <StatusMessage text={error} />
      ) : null}

      <AdminCard>
        <div className="overflow-x-auto">
          {loading ? (
            <p className="text-sm text-[var(--maried-cocoa)]">
              Carregando disputas...
            </p>
          ) : disputes.length === 0 ? (
            <EmptyState>
              Nenhuma disputa financeira registrada.
            </EmptyState>
          ) : (
            <table className="min-w-full text-left text-sm">
              <thead className="text-xs uppercase text-[var(--maried-cocoa)]">
                <tr>
                  <th className="px-3 py-2">Cliente</th>
                  <th className="px-3 py-2">Origem</th>
                  <th className="px-3 py-2">Valor</th>
                  <th className="px-3 py-2">Status</th>
                  <th className="px-3 py-2">Motivo</th>
                  <th className="px-3 py-2">Disputa</th>
                  <th className="px-3 py-2">Vencimento</th>
                  <th className="px-3 py-2">Conta</th>
                </tr>
              </thead>
              <tbody>
                {disputes.map((dispute) => (
                  <tr
                    key={dispute.id}
                    className="border-t border-[var(--maried-sand)]"
                  >
                    <td className="px-3 py-3">
                      {dispute.organization_name}
                    </td>
                    <td className="px-3 py-3">
                      {dispute.origin_type}
                    </td>
                    <td className="px-3 py-3">
                      {formatMoney(dispute)}
                    </td>
                    <td className="px-3 py-3">
                      {dispute.status}
                    </td>
                    <td className="px-3 py-3">
                      {dispute.reason || "-"}
                    </td>
                    <td className="px-3 py-3">
                      {dispute.stripe_dispute_reference}
                    </td>
                    <td className="px-3 py-3">
                      {formatDate(dispute.evidence_due_by)}
                    </td>
                    <td className="px-3 py-3">
                      {dispute.is_blocking
                        ? "Bloqueada"
                        : "Liberada"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </AdminCard>
    </SuperAdminShell>
  );
}

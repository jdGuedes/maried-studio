"use client";

import { useEffect, useState } from "react";

import {
  AdminCard,
  EmptyState,
  MetricCard,
  StatusMessage,
  SuperAdminShell,
} from "@/components/superadmin/superadmin-shell";
import {
  getSuperAdminAuditLogs,
  getSuperAdminSummary,
  type SuperAdminAuditLog,
  type SuperAdminSummary,
} from "@/lib/api";


function formatDate(value: string) {
  return new Intl.DateTimeFormat(
    "pt-BR",
    {
      dateStyle: "short",
      timeStyle: "short",
    }
  ).format(new Date(value));
}


export default function SuperAdminDashboardPage() {
  const [
    summary,
    setSummary,
  ] = useState<SuperAdminSummary | null>(null);
  const [
    auditLogs,
    setAuditLogs,
  ] = useState<SuperAdminAuditLog[]>([]);
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
        const [
          summaryData,
          auditData,
        ] = await Promise.all([
          getSuperAdminSummary(),
          getSuperAdminAuditLogs(),
        ]);

        if (!active) {
          return;
        }

        setSummary(summaryData);
        setAuditLogs(auditData.slice(0, 6));
      } catch (error) {
        if (active) {
          setError(
            error instanceof Error
              ? error.message
              : "Não foi possível carregar o painel."
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
      title="Dashboard"
      subtitle="Visão global da operação MARIED STUDIO."
    >
      {error ? <StatusMessage text={error} /> : null}

      {loading ? (
        <AdminCard>Carregando métricas...</AdminCard>
      ) : summary ? (
        <div className="space-y-5">
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
            <MetricCard label="Clientes" value={summary.organizations} />
            <MetricCard label="Clientes ativos" value={summary.active_organizations} />
            <MetricCard label="Assinaturas ativas" value={summary.operational_active_subscriptions} />
            <MetricCard label="Em grace" value={summary.operational_grace_subscriptions} />
            <MetricCard label="Bloqueadas" value={summary.operational_blocked_subscriptions} />
            <MetricCard label="Gerações" value={summary.generations} />
            <MetricCard label="Falhas de geração" value={summary.failed_generations} />
            <MetricCard label="Planos" value={summary.plans} />
          </div>

          <AdminCard>
            <h2 className="mb-4 text-sm font-semibold text-[var(--maried-espresso)]">
              Atividade administrativa recente
            </h2>

            {auditLogs.length > 0 ? (
              <div className="divide-y divide-[var(--maried-sand)]">
                {auditLogs.map((log) => (
                  <div key={log.id} className="py-3 text-sm">
                    <div className="flex flex-col gap-1 sm:flex-row sm:items-center sm:justify-between">
                      <span className="font-medium text-[var(--maried-espresso)]">
                        {log.action}
                      </span>
                      <span className="text-xs text-[var(--maried-cocoa)]">
                        {formatDate(log.created_at)}
                      </span>
                    </div>
                    <div className="mt-1 text-xs text-[var(--maried-cocoa)]">
                      {log.organization_name ?? "Global"} · {log.actor_email ?? "Sistema"}
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <EmptyState>Nenhum evento de auditoria registrado.</EmptyState>
            )}
          </AdminCard>
        </div>
      ) : null}
    </SuperAdminShell>
  );
}

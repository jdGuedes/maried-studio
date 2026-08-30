"use client";

import { useEffect, useState } from "react";

import {
  AdminCard,
  EmptyState,
  StatusMessage,
  SuperAdminShell,
} from "@/components/superadmin/superadmin-shell";
import {
  getSuperAdminAuditLogs,
  type SuperAdminAuditLog,
} from "@/lib/api";


const sensitiveKeys = [
  "password",
  "senha",
  "token",
  "cookie",
  "session",
  "secret",
  "api_key",
  "database_url",
];


function formatDate(value: string) {
  return new Intl.DateTimeFormat("pt-BR", {
    dateStyle: "short",
    timeStyle: "short",
  }).format(new Date(value));
}


function safeMetadata(metadata: Record<string, unknown>) {
  return JSON.stringify(
    metadata,
    (key, value) => (
      sensitiveKeys.some((sensitiveKey) => key.toLowerCase().includes(sensitiveKey))
        ? "[redacted]"
        : value
    ),
    2
  );
}


export default function SuperAdminAuditoriaPage() {
  const [logs, setLogs] = useState<SuperAdminAuditLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;

    void (async () => {
      try {
        const data = await getSuperAdminAuditLogs();

        if (active) {
          setLogs(data);
        }
      } catch (error) {
        if (active) {
          setError(error instanceof Error ? error.message : "Erro ao carregar auditoria.");
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
    <SuperAdminShell title="Auditoria" subtitle="Histórico administrativo somente leitura.">
      {error ? <StatusMessage text={error} /> : null}

      <AdminCard>
        {loading ? (
          <EmptyState>Carregando auditoria...</EmptyState>
        ) : logs.length > 0 ? (
          <div className="space-y-3">
            {logs.map((log) => (
              <article key={log.id} className="rounded-xl border border-[var(--maried-sand)] p-4">
                <div className="flex flex-col gap-1 md:flex-row md:items-start md:justify-between">
                  <div>
                    <h2 className="text-sm font-semibold text-[var(--maried-espresso)]">{log.action}</h2>
                    <p className="mt-1 text-xs text-[var(--maried-cocoa)]">
                      {log.organization_name ?? "Global"} · {log.actor_email ?? "Sistema"} · {log.entity_type} {log.entity_id}
                    </p>
                  </div>
                  <span className="text-xs text-[var(--maried-cocoa)]">{formatDate(log.created_at)}</span>
                </div>
                <pre className="mt-3 max-h-40 overflow-auto rounded-xl bg-[var(--maried-ivory)] p-3 text-xs text-[var(--maried-cocoa)]">
                  {safeMetadata(log.metadata)}
                </pre>
              </article>
            ))}
          </div>
        ) : (
          <EmptyState>Nenhum evento de auditoria registrado.</EmptyState>
        )}
      </AdminCard>
    </SuperAdminShell>
  );
}

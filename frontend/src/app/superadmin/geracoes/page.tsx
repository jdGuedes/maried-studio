"use client";

import { useEffect, useState } from "react";

import {
  AdminCard,
  EmptyState,
  StatusMessage,
  SuperAdminShell,
} from "@/components/superadmin/superadmin-shell";
import {
  getSuperAdminGeneration,
  getSuperAdminGenerations,
  type SuperAdminGeneration,
} from "@/lib/api";


function formatDate(value?: string | null) {
  return value
    ? new Intl.DateTimeFormat("pt-BR", {
        dateStyle: "short",
        timeStyle: "short",
      }).format(new Date(value))
    : "-";
}


export default function SuperAdminGeracoesPage() {
  const [generations, setGenerations] = useState<SuperAdminGeneration[]>([]);
  const [selected, setSelected] = useState<SuperAdminGeneration | null>(null);
  const [statusFilter, setStatusFilter] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  async function load(filter = statusFilter) {
    const data = await getSuperAdminGenerations(filter);
    setGenerations(data);
    setSelected(data[0] ?? null);
  }

  useEffect(() => {
    let active = true;

    void (async () => {
      try {
        const data = await getSuperAdminGenerations();

        if (active) {
          setGenerations(data);
          setSelected(data[0] ?? null);
        }
      } catch (error) {
        if (active) {
          setError(error instanceof Error ? error.message : "Erro ao carregar gerações.");
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

  async function selectGeneration(id: string) {
    setError(null);

    try {
      setSelected(await getSuperAdminGeneration(id));
    } catch (error) {
      setError(error instanceof Error ? error.message : "Erro ao carregar geração.");
    }
  }

  return (
    <SuperAdminShell title="Gerações" subtitle="Consulta administrativa para suporte e diagnóstico.">
      {error ? <StatusMessage text={error} /> : null}

      <div className="grid gap-5 xl:grid-cols-[1fr_360px]">
        <AdminCard>
          <div className="mb-4 flex justify-end">
            <select
              value={statusFilter}
              onChange={(event) => {
                const value = event.target.value;
                setStatusFilter(value);
                void load(value);
              }}
              className="h-10 rounded-xl border border-[var(--maried-sand)] bg-white px-3 text-sm"
            >
              <option value="">Todas</option>
              <option value="COMPLETED">Completed</option>
              <option value="FAILED">Failed</option>
            </select>
          </div>

          {loading ? (
            <EmptyState>Carregando gerações...</EmptyState>
          ) : generations.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="w-full min-w-[860px] text-left text-sm">
                <thead className="text-xs text-[var(--maried-cocoa)]">
                  <tr>
                    <th className="py-2">Cliente</th>
                    <th>Peça</th>
                    <th>Modo</th>
                    <th>Status</th>
                    <th>Provider</th>
                    <th>Data</th>
                    <th></th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[var(--maried-sand)]">
                  {generations.map((generation) => (
                    <tr key={generation.id}>
                      <td className="py-3 font-medium text-[var(--maried-espresso)]">{generation.organization_name}</td>
                      <td>{generation.product_name}</td>
                      <td>{generation.mode}</td>
                      <td>{generation.status}</td>
                      <td>{generation.provider}</td>
                      <td>{formatDate(generation.created_at)}</td>
                      <td className="text-right">
                        <button type="button" onClick={() => void selectGeneration(generation.id)} className="font-medium text-[var(--maried-gold)]">
                          Detalhe
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <EmptyState>Nenhuma geração encontrada.</EmptyState>
          )}
        </AdminCard>

        <AdminCard>
          <h2 className="mb-4 text-sm font-semibold text-[var(--maried-espresso)]">Detalhe</h2>
          {selected ? (
            <div className="space-y-2 text-sm text-[var(--maried-cocoa)]">
              <Info label="ID" value={selected.id} />
              <Info label="Cliente" value={selected.organization_name} />
              <Info label="Produto" value={selected.product_name} />
              <Info label="Status" value={selected.status} />
              <Info label="Modo" value={selected.mode} />
              <Info label="Provider" value={selected.provider} />
              <Info label="Modelo" value={selected.model || "-"} />
              <Info label="Crédito" value={selected.credit_cost} />
              <Info label="Retries" value={selected.retry_count} />
              <Info label="Failure type" value={selected.failure_type || "-"} />
              <Info label="Error code" value={selected.error_code || "-"} />
              <Info label="Error message" value={selected.error_message || "-"} />
            </div>
          ) : (
            <EmptyState>Nenhuma geração selecionada.</EmptyState>
          )}
        </AdminCard>
      </div>
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
    <div className="border-b border-[var(--maried-sand)] py-2">
      <div className="text-xs">{label}</div>
      <div className="break-words font-medium text-[var(--maried-espresso)]">{value}</div>
    </div>
  );
}

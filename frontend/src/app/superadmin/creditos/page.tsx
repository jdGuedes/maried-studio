"use client";

import Link from "next/link";
import { useEffect, useState, type FormEvent } from "react";

import {
  AdminCard,
  EmptyState,
  StatusMessage,
  SuperAdminShell,
} from "@/components/superadmin/superadmin-shell";
import {
  adjustSuperAdminCredits,
  getSuperAdminWallets,
  type SuperAdminWallet,
} from "@/lib/api";


export default function SuperAdminCreditosPage() {
  const [wallets, setWallets] = useState<SuperAdminWallet[]>([]);
  const [selectedId, setSelectedId] = useState("");
  const [balanceType, setBalanceType] = useState<"PLAN" | "PURCHASED">("PLAN");
  const [operation, setOperation] = useState<"ADD" | "REMOVE">("ADD");
  const [quantity, setQuantity] = useState("");
  const [reason, setReason] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  async function load() {
    const data = await getSuperAdminWallets();
    setWallets(data);
    setSelectedId((current) => current || data[0]?.organization || "");
  }

  useEffect(() => {
    let active = true;

    void (async () => {
      try {
        const data = await getSuperAdminWallets();

        if (active) {
          setWallets(data);
          setSelectedId(data[0]?.organization || "");
        }
      } catch (error) {
        if (active) {
          setError(error instanceof Error ? error.message : "Erro ao carregar carteiras.");
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

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    const parsedQuantity = Number.parseInt(quantity, 10);

    if (Number.isNaN(parsedQuantity) || parsedQuantity <= 0) {
      setError("Informe uma quantidade positiva.");
      return;
    }

    if (!window.confirm("Remover ou adicionar créditos altera o saldo do cliente. Confirmar?")) {
      return;
    }

    setSaving(true);
    setError(null);
    setMessage(null);

    try {
      await adjustSuperAdminCredits({
        organization_id: selectedId,
        balance_type: balanceType,
        amount: operation === "ADD" ? parsedQuantity : -parsedQuantity,
        reason,
      });
      setQuantity("");
      setReason("");
      setMessage("Ajuste registrado em transação e auditoria.");
      await load();
    } catch (error) {
      setError(error instanceof Error ? error.message : "Erro ao ajustar créditos.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <SuperAdminShell title="Créditos" subtitle="Carteiras globais e ajuste manual via CreditService.">
      <div className="grid gap-5 xl:grid-cols-[360px_1fr]">
        <AdminCard>
          <h2 className="mb-4 text-sm font-semibold text-[var(--maried-espresso)]">Ajuste manual</h2>
          <form onSubmit={(event) => void submit(event)} className="space-y-3">
            <select required value={selectedId} onChange={(event) => setSelectedId(event.target.value)} className="h-10 w-full rounded-xl border border-[var(--maried-sand)] bg-white px-3 text-sm">
              {wallets.map((wallet) => (
                <option key={wallet.id} value={wallet.organization}>{wallet.organization_name}</option>
              ))}
            </select>
            <div className="grid gap-3 sm:grid-cols-2">
              <select value={balanceType} onChange={(event) => setBalanceType(event.target.value as "PLAN" | "PURCHASED")} className="h-10 rounded-xl border border-[var(--maried-sand)] bg-white px-3 text-sm">
                <option value="PLAN">Plano</option>
                <option value="PURCHASED">Comprados</option>
              </select>
              <select value={operation} onChange={(event) => setOperation(event.target.value as "ADD" | "REMOVE")} className="h-10 rounded-xl border border-[var(--maried-sand)] bg-white px-3 text-sm">
                <option value="ADD">Adicionar</option>
                <option value="REMOVE">Remover</option>
              </select>
            </div>
            <input required min="1" type="number" value={quantity} onChange={(event) => setQuantity(event.target.value)} placeholder="Quantidade" className="h-10 w-full rounded-xl border border-[var(--maried-sand)] px-3 text-sm" />
            <input required value={reason} onChange={(event) => setReason(event.target.value)} placeholder="Motivo obrigatório" className="h-10 w-full rounded-xl border border-[var(--maried-sand)] px-3 text-sm" />
            <button disabled={saving || !selectedId} type="submit" className="h-10 w-full rounded-xl bg-[var(--maried-coffee)] px-4 text-sm text-white disabled:opacity-60">
              Confirmar ajuste
            </button>
          </form>
        </AdminCard>

        <div className="space-y-4">
          {error ? <StatusMessage text={error} /> : null}
          {message ? <StatusMessage text={message} tone="success" /> : null}

          <AdminCard>
            {loading ? (
              <EmptyState>Carregando carteiras...</EmptyState>
            ) : wallets.length > 0 ? (
              <div className="overflow-x-auto">
                <table className="w-full min-w-[760px] text-left text-sm">
                  <thead className="text-xs text-[var(--maried-cocoa)]">
                    <tr>
                      <th className="py-2">Cliente</th>
                      <th>Plano</th>
                      <th>Comprados</th>
                      <th>Reservados</th>
                      <th>Disponíveis</th>
                      <th>Total</th>
                      <th></th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[var(--maried-sand)]">
                    {wallets.map((wallet) => (
                      <tr key={wallet.id}>
                        <td className="py-3 font-medium text-[var(--maried-espresso)]">{wallet.organization_name}</td>
                        <td>{wallet.plan_balance}</td>
                        <td>{wallet.purchased_balance}</td>
                        <td>{wallet.reserved_balance}</td>
                        <td>{wallet.available_balance}</td>
                        <td>{wallet.total_balance}</td>
                        <td className="text-right">
                          <Link href={`/superadmin/clientes/${wallet.organization}`} className="font-medium text-[var(--maried-gold)]">Ver cliente</Link>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <EmptyState>Nenhuma carteira encontrada.</EmptyState>
            )}
          </AdminCard>
        </div>
      </div>
    </SuperAdminShell>
  );
}

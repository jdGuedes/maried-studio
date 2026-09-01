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
  createSuperAdminCreditPackage,
  getSuperAdminCreditPackages,
  getSuperAdminCreditPurchases,
  getSuperAdminWallets,
  syncSuperAdminCreditPackageStripe,
  updateSuperAdminCreditPackage,
  type SuperAdminCreditPackage,
  type SuperAdminCreditPurchase,
  type SuperAdminWallet,
} from "@/lib/api";


const emptyPackage = {
  name: "",
  slug: "",
  description: "",
  credits: 10,
  price: "",
  currency: "BRL",
  is_active: true,
  sort_order: 10,
};


export default function SuperAdminCreditosPage() {
  const [wallets, setWallets] = useState<SuperAdminWallet[]>([]);
  const [packages, setPackages] = useState<SuperAdminCreditPackage[]>([]);
  const [purchases, setPurchases] = useState<SuperAdminCreditPurchase[]>([]);
  const [packageForm, setPackageForm] = useState(emptyPackage);
  const [editingPackageId, setEditingPackageId] = useState<string | null>(null);
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
    const [walletData, packageData, purchaseData] = await Promise.all([
      getSuperAdminWallets(),
      getSuperAdminCreditPackages(),
      getSuperAdminCreditPurchases(),
    ]);
    setWallets(walletData);
    setPackages(packageData);
    setPurchases(purchaseData);
    setSelectedId((current) => current || walletData[0]?.organization || "");
  }

  useEffect(() => {
    let active = true;

    void (async () => {
      try {
        const [data, packageData, purchaseData] = await Promise.all([
          getSuperAdminWallets(),
          getSuperAdminCreditPackages(),
          getSuperAdminCreditPurchases(),
        ]);

        if (active) {
          setWallets(data);
          setPackages(packageData);
          setPurchases(purchaseData);
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

  function editPackage(creditPackage: SuperAdminCreditPackage) {
    setEditingPackageId(creditPackage.id);
    setPackageForm({
      name: creditPackage.name,
      slug: creditPackage.slug,
      description: creditPackage.description,
      credits: creditPackage.credits,
      price: creditPackage.price,
      currency: creditPackage.currency,
      is_active: creditPackage.is_active,
      sort_order: creditPackage.sort_order,
    });
  }

  async function submitPackage(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    setSaving(true);
    setError(null);
    setMessage(null);

    try {
      if (editingPackageId) {
        await updateSuperAdminCreditPackage(editingPackageId, packageForm);
        setMessage("Pacote atualizado. Sincronização Stripe verificada.");
      } else {
        await createSuperAdminCreditPackage(packageForm);
        setMessage("Pacote criado. Sincronização Stripe verificada.");
      }

      setEditingPackageId(null);
      setPackageForm(emptyPackage);
      await load();
    } catch (error) {
      setError(error instanceof Error ? error.message : "Erro ao salvar pacote.");
    } finally {
      setSaving(false);
    }
  }

  async function togglePackage(creditPackage: SuperAdminCreditPackage) {
    setSaving(true);
    setError(null);

    try {
      await updateSuperAdminCreditPackage(creditPackage.id, {
        is_active: !creditPackage.is_active,
      });
      await load();
    } catch (error) {
      setError(error instanceof Error ? error.message : "Erro ao alterar pacote.");
    } finally {
      setSaving(false);
    }
  }

  async function syncPackage(creditPackage: SuperAdminCreditPackage) {
    setSaving(true);
    setError(null);
    setMessage(null);

    try {
      await syncSuperAdminCreditPackageStripe(creditPackage.id);
      setMessage("Pacote sincronizado com Stripe.");
      await load();
    } catch (error) {
      setError(error instanceof Error ? error.message : "Erro ao sincronizar pacote.");
      await load();
    } finally {
      setSaving(false);
    }
  }

  return (
    <SuperAdminShell title="Créditos" subtitle="Carteiras globais e ajuste manual via CreditService.">
      <div className="grid gap-5 xl:grid-cols-[360px_1fr]">
        <div className="space-y-5">
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

        <AdminCard>
          <h2 className="mb-4 text-sm font-semibold text-[var(--maried-espresso)]">{editingPackageId ? "Editar pacote" : "Criar pacote"}</h2>
          <form onSubmit={(event) => void submitPackage(event)} className="space-y-3">
            <input required value={packageForm.name} onChange={(event) => setPackageForm({ ...packageForm, name: event.target.value })} placeholder="Nome" className="h-10 w-full rounded-xl border border-[var(--maried-sand)] px-3 text-sm" />
            <input required value={packageForm.slug} onChange={(event) => setPackageForm({ ...packageForm, slug: event.target.value })} placeholder="Slug" className="h-10 w-full rounded-xl border border-[var(--maried-sand)] px-3 text-sm" />
            <input value={packageForm.description} onChange={(event) => setPackageForm({ ...packageForm, description: event.target.value })} placeholder="Descrição" className="h-10 w-full rounded-xl border border-[var(--maried-sand)] px-3 text-sm" />
            <div className="grid gap-3 sm:grid-cols-2">
              <input required min="1" type="number" value={packageForm.credits} onChange={(event) => setPackageForm({ ...packageForm, credits: Number(event.target.value) })} placeholder="Créditos" className="h-10 rounded-xl border border-[var(--maried-sand)] px-3 text-sm" />
              <input required value={packageForm.price} onChange={(event) => setPackageForm({ ...packageForm, price: event.target.value })} placeholder="Preço" className="h-10 rounded-xl border border-[var(--maried-sand)] px-3 text-sm" />
            </div>
            <div className="grid gap-3 sm:grid-cols-2">
              <input required maxLength={3} value={packageForm.currency} onChange={(event) => setPackageForm({ ...packageForm, currency: event.target.value.toUpperCase() })} placeholder="Moeda" className="h-10 rounded-xl border border-[var(--maried-sand)] px-3 text-sm" />
              <input required min="0" type="number" value={packageForm.sort_order} onChange={(event) => setPackageForm({ ...packageForm, sort_order: Number(event.target.value) })} placeholder="Ordem" className="h-10 rounded-xl border border-[var(--maried-sand)] px-3 text-sm" />
            </div>
            <label className="flex items-center gap-2 text-sm text-[var(--maried-cocoa)]">
              <input type="checkbox" checked={packageForm.is_active} onChange={(event) => setPackageForm({ ...packageForm, is_active: event.target.checked })} />
              Comercializado
            </label>
            <button disabled={saving} type="submit" className="h-10 w-full rounded-xl bg-[var(--maried-coffee)] px-4 text-sm text-white disabled:opacity-60">
              {saving ? "Salvando..." : "Salvar pacote"}
            </button>
          </form>
        </AdminCard>
        </div>

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

          <AdminCard>
            {packages.length > 0 ? (
              <div className="overflow-x-auto">
                <table className="w-full min-w-[760px] text-left text-sm">
                  <thead className="text-xs text-[var(--maried-cocoa)]">
                    <tr>
                      <th className="py-2">Pacote</th>
                      <th>Créditos</th>
                      <th>Preço</th>
                      <th>Status</th>
                      <th>Stripe</th>
                      <th></th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[var(--maried-sand)]">
                    {packages.map((creditPackage) => (
                      <tr key={creditPackage.id}>
                        <td className="py-3 font-medium text-[var(--maried-espresso)]">{creditPackage.name}</td>
                        <td>{creditPackage.credits}</td>
                        <td>{creditPackage.currency} {creditPackage.price}</td>
                        <td>{creditPackage.is_active ? "Ativo" : "Inativo"}</td>
                        <td>{creditPackage.stripe_sync_status ?? "PENDING"}</td>
                        <td className="space-x-3 text-right">
                          <button type="button" onClick={() => editPackage(creditPackage)} className="font-medium text-[var(--maried-gold)]">Editar</button>
                          <button disabled={saving} type="button" onClick={() => void togglePackage(creditPackage)} className="font-medium text-[var(--maried-gold)] disabled:opacity-60">{creditPackage.is_active ? "Arquivar" : "Ativar"}</button>
                          <button disabled={saving} type="button" onClick={() => void syncPackage(creditPackage)} className="font-medium text-[var(--maried-gold)] disabled:opacity-60">Stripe</button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <EmptyState>Nenhum pacote cadastrado.</EmptyState>
            )}
          </AdminCard>

          <AdminCard>
            {purchases.length > 0 ? (
              <div className="overflow-x-auto">
                <table className="w-full min-w-[760px] text-left text-sm">
                  <thead className="text-xs text-[var(--maried-cocoa)]">
                    <tr>
                      <th className="py-2">Cliente</th>
                      <th>Pacote</th>
                      <th>Créditos</th>
                      <th>Status</th>
                      <th>Pagamento</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[var(--maried-sand)]">
                    {purchases.map((purchase) => (
                      <tr key={purchase.id}>
                        <td className="py-3 font-medium text-[var(--maried-espresso)]">{purchase.organization_name}</td>
                        <td>{purchase.package_name}</td>
                        <td>{purchase.credits_snapshot}</td>
                        <td>{purchase.status}</td>
                        <td>{purchase.paid_at ? "Confirmado" : "Pendente"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <EmptyState>Nenhuma compra avulsa encontrada.</EmptyState>
            )}
          </AdminCard>
        </div>
      </div>
    </SuperAdminShell>
  );
}

"use client";

import { useEffect, useState, type FormEvent } from "react";

import {
  AdminCard,
  EmptyState,
  StatusMessage,
  SuperAdminShell,
} from "@/components/superadmin/superadmin-shell";
import {
  createSuperAdminPlan,
  getSuperAdminPlans,
  syncSuperAdminPlanStripe,
  updateSuperAdminPlan,
  type SuperAdminPlan,
} from "@/lib/api";


const emptyPlan = {
  name: "",
  slug: "",
  description: "",
  price: "",
  billing_cycle: "MONTHLY",
  credits_per_cycle: 50,
  is_active: true,
  sort_order: 10,
};


export default function SuperAdminPlanosPage() {
  const [plans, setPlans] = useState<SuperAdminPlan[]>([]);
  const [form, setForm] = useState(emptyPlan);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [syncingId, setSyncingId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  async function load() {
    setPlans(await getSuperAdminPlans());
  }

  useEffect(() => {
    let active = true;

    void (async () => {
      try {
        const data = await getSuperAdminPlans();

        if (active) {
          setPlans(data);
        }
      } catch (error) {
        if (active) {
          setError(error instanceof Error ? error.message : "Erro ao carregar planos.");
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

  function edit(plan: SuperAdminPlan) {
    setEditingId(plan.id);
    setForm({
      name: plan.name,
      slug: plan.slug,
      description: plan.description,
      price: plan.price,
      billing_cycle: plan.billing_cycle,
      credits_per_cycle: plan.credits_per_cycle,
      is_active: plan.is_active,
      sort_order: plan.sort_order,
    });
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSaving(true);
    setError(null);
    setMessage(null);

    try {
      if (editingId) {
        await updateSuperAdminPlan(editingId, form);
        setMessage("Plano atualizado. Sincronização Stripe verificada.");
      } else {
        await createSuperAdminPlan(form);
        setMessage("Plano criado. Sincronização Stripe verificada.");
      }

      setEditingId(null);
      setForm(emptyPlan);
      await load();
    } catch (error) {
      setError(error instanceof Error ? error.message : "Erro ao salvar plano.");
    } finally {
      setSaving(false);
    }
  }

  async function toggle(plan: SuperAdminPlan) {
    if (!window.confirm("Desativar plano impede novas contratações, sem apagar assinaturas existentes. Confirmar?")) {
      return;
    }

    setSaving(true);
    setError(null);

    try {
      await updateSuperAdminPlan(plan.id, { is_active: !plan.is_active });
      await load();
    } catch (error) {
      setError(error instanceof Error ? error.message : "Erro ao alterar status do plano.");
    } finally {
      setSaving(false);
    }
  }

  async function syncStripe(plan: SuperAdminPlan) {
    setSyncingId(plan.id);
    setError(null);
    setMessage(null);

    try {
      await syncSuperAdminPlanStripe(plan.id);
      setMessage("Sincronização Stripe verificada.");
      await load();
    } catch (error) {
      setError(error instanceof Error ? error.message : "Não foi possível sincronizar este plano com o Stripe.");
      await load();
    } finally {
      setSyncingId(null);
    }
  }

  return (
    <SuperAdminShell title="Planos" subtitle="Criação e edição comercial sem DELETE físico.">
      <div className="grid gap-5 xl:grid-cols-[360px_1fr]">
        <AdminCard>
          <h2 className="mb-4 text-sm font-semibold text-[var(--maried-espresso)]">
            {editingId ? "Editar plano" : "Criar plano"}
          </h2>

          <form onSubmit={(event) => void submit(event)} className="space-y-3">
            <Input label="Nome" value={form.name} onChange={(name) => setForm({ ...form, name })} />
            <Input label="Slug" value={form.slug} onChange={(slug) => setForm({ ...form, slug })} />
            <Input label="Descrição" value={form.description} onChange={(description) => setForm({ ...form, description })} />
            <Input label="Preço" value={form.price} onChange={(price) => setForm({ ...form, price })} />
            <Input label="Créditos por ciclo" type="number" value={String(form.credits_per_cycle)} onChange={(value) => setForm({ ...form, credits_per_cycle: Number(value) })} />
            <Input label="Ordem" type="number" value={String(form.sort_order)} onChange={(value) => setForm({ ...form, sort_order: Number(value) })} />

            <label className="flex items-center gap-2 text-sm text-[var(--maried-cocoa)]">
              <input type="checkbox" checked={form.is_active} onChange={(event) => setForm({ ...form, is_active: event.target.checked })} />
              Comercializado
            </label>

            <button disabled={saving} type="submit" className="h-10 w-full rounded-xl bg-[var(--maried-coffee)] px-4 text-sm text-white disabled:opacity-60">
              {saving ? "Salvando..." : "Salvar plano"}
            </button>
          </form>
        </AdminCard>

        <div className="space-y-4">
          {error ? <StatusMessage text={error} /> : null}
          {message ? <StatusMessage text={message} tone="success" /> : null}

          <AdminCard>
            {loading ? (
              <EmptyState>Carregando planos...</EmptyState>
            ) : plans.length > 0 ? (
              <div className="overflow-x-auto">
                <table className="w-full min-w-[760px] text-left text-sm">
                  <thead className="text-xs text-[var(--maried-cocoa)]">
                    <tr>
                      <th className="py-2">Nome</th>
                      <th>Preço</th>
                      <th>Ciclo</th>
                      <th>Créditos</th>
                      <th>Status</th>
                      <th>Stripe</th>
                      <th>Ordem</th>
                      <th></th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[var(--maried-sand)]">
                    {plans.map((plan) => (
                      <tr key={plan.id}>
                        <td className="py-3 font-medium text-[var(--maried-espresso)]">{plan.name}</td>
                        <td>{plan.price}</td>
                        <td>{plan.billing_cycle}</td>
                        <td>{plan.credits_per_cycle}</td>
                        <td>{plan.is_active ? "Ativo" : "Inativo"}</td>
                        <td>
                          <div className="flex flex-col gap-1">
                            <span className={[
                              "w-fit rounded-full px-2 py-1 text-[11px] font-medium",
                              plan.stripe_sync_status === "SYNCED"
                                ? "bg-green-50 text-green-700"
                                : plan.stripe_sync_status === "ERROR"
                                  ? "bg-red-50 text-red-700"
                                  : "bg-[var(--maried-soft-gold)] text-[var(--maried-coffee)]",
                            ].join(" ")}>
                              {plan.stripe_sync_status === "SYNCED"
                                ? "Sincronizado"
                                : plan.stripe_sync_status === "ERROR"
                                  ? "Erro"
                                  : "Pendente"}
                            </span>
                            {plan.stripe_sync_error ? (
                              <span className="max-w-[220px] text-xs text-red-700">
                                {plan.stripe_sync_error}
                              </span>
                            ) : null}
                          </div>
                        </td>
                        <td>{plan.sort_order}</td>
                        <td className="space-x-3 text-right">
                          <button type="button" onClick={() => edit(plan)} className="font-medium text-[var(--maried-gold)]">Editar</button>
                          <button disabled={saving} type="button" onClick={() => void toggle(plan)} className="font-medium text-[var(--maried-gold)] disabled:opacity-60">
                            {plan.is_active ? "Desativar" : "Ativar"}
                          </button>
                          <button disabled={syncingId === plan.id} type="button" onClick={() => void syncStripe(plan)} className="font-medium text-[var(--maried-gold)] disabled:opacity-60">
                            {syncingId === plan.id ? "Sincronizando..." : "Stripe"}
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <EmptyState>Nenhum plano cadastrado.</EmptyState>
            )}
          </AdminCard>
        </div>
      </div>
    </SuperAdminShell>
  );
}


function Input({
  label,
  value,
  onChange,
  type = "text",
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  type?: string;
}) {
  return (
    <label className="block text-sm">
      <span className="mb-1 block text-xs text-[var(--maried-cocoa)]">{label}</span>
      <input required type={type} value={value} onChange={(event) => onChange(event.target.value)} className="h-10 w-full rounded-xl border border-[var(--maried-sand)] px-3 text-sm" />
    </label>
  );
}

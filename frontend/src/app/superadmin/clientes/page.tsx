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
  createSuperAdminClient,
  getSuperAdminClients,
  getSuperAdminPlans,
  type SuperAdminClientListItem,
  type SuperAdminPlan,
} from "@/lib/api";


const emptyForm = {
  name: "",
  email: "",
  initial_password: "",
  plan_id: "",
};


export default function SuperAdminClientesPage() {
  const [
    clients,
    setClients,
  ] = useState<SuperAdminClientListItem[]>([]);
  const [
    plans,
    setPlans,
  ] = useState<SuperAdminPlan[]>([]);
  const [
    form,
    setForm,
  ] = useState(emptyForm);
  const [
    search,
    setSearch,
  ] = useState("");
  const [
    statusFilter,
    setStatusFilter,
  ] = useState("ALL");
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
      getSuperAdminClients(),
      getSuperAdminPlans(),
    ]);

    setClients(clientData);
    setPlans(planData);
  }

  useEffect(() => {
    let active = true;

    void (async () => {
      try {
        const [
          clientData,
          planData,
        ] = await Promise.all([
          getSuperAdminClients(),
          getSuperAdminPlans(),
        ]);

        if (!active) {
          return;
        }

        setClients(clientData);
        setPlans(planData);
      } catch (error) {
        if (active) {
          setError(error instanceof Error ? error.message : "Erro ao carregar clientes.");
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

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (saving) {
      return;
    }

    setSaving(true);
    setError(null);
    setMessage(null);

    try {
      await createSuperAdminClient(form);
      setForm(emptyForm);
      setMessage("Cliente criado com plano pendente de pagamento.");
      await load();
    } catch (error) {
      setError(error instanceof Error ? error.message : "Erro ao criar cliente.");
    } finally {
      setSaving(false);
    }
  }

  const activePlans =
    plans.filter((plan) => plan.is_active);

  const filteredClients =
    clients.filter((client) => {
      const text =
        `${client.name} ${client.user?.email ?? ""}`.toLowerCase();
      const matchesSearch =
        text.includes(search.toLowerCase());
      const matchesStatus =
        statusFilter === "ALL" ||
        (statusFilter === "ACTIVE" && client.is_active) ||
        (statusFilter === "BLOCKED" && !client.is_active);

      return matchesSearch && matchesStatus;
    });

  return (
    <SuperAdminShell
      title="Clientes"
      subtitle="Contas operacionais da V1: Organization, usuário principal, assinatura e carteira."
    >
      <div className="grid gap-5 xl:grid-cols-[360px_1fr]">
        <AdminCard>
          <h2 className="mb-4 text-sm font-semibold text-[var(--maried-espresso)]">
            Novo cliente
          </h2>

          <form onSubmit={(event) => void handleSubmit(event)} className="space-y-3">
            <TextInput label="Nome" value={form.name} onChange={(name) => setForm({ ...form, name })} />
            <TextInput label="E-mail" type="email" value={form.email} onChange={(email) => setForm({ ...form, email })} />
            <TextInput label="Senha inicial" type="password" value={form.initial_password} onChange={(initial_password) => setForm({ ...form, initial_password })} />

            <label className="block text-sm">
              <span className="mb-1 block text-xs text-[var(--maried-cocoa)]">Plano</span>
              <select
                required
                value={form.plan_id}
                onChange={(event) => setForm({ ...form, plan_id: event.target.value })}
                className="h-10 w-full rounded-xl border border-[var(--maried-sand)] bg-white px-3 text-sm"
              >
                <option value="">Selecione</option>
                {activePlans.map((plan) => (
                  <option key={plan.id} value={plan.id}>
                    {plan.name} · {plan.credits_per_cycle} créditos
                  </option>
                ))}
              </select>
            </label>

            <button
              type="submit"
              disabled={saving}
              className="h-10 w-full rounded-xl bg-[var(--maried-coffee)] px-4 text-sm font-medium text-white disabled:opacity-60"
            >
              {saving ? "Criando..." : "Criar cliente"}
            </button>
          </form>
        </AdminCard>

        <div className="space-y-4">
          {error ? <StatusMessage text={error} /> : null}
          {message ? <StatusMessage text={message} tone="success" /> : null}

          <AdminCard>
            <div className="mb-4 flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
              <div className="text-sm font-semibold text-[var(--maried-espresso)]">
                Lista de clientes
              </div>
              <div className="flex flex-col gap-2 sm:flex-row">
                <input
                  value={search}
                  onChange={(event) => setSearch(event.target.value)}
                  placeholder="Buscar por nome ou e-mail"
                  className="h-10 rounded-xl border border-[var(--maried-sand)] px-3 text-sm"
                />
                <select
                  value={statusFilter}
                  onChange={(event) => setStatusFilter(event.target.value)}
                  className="h-10 rounded-xl border border-[var(--maried-sand)] bg-white px-3 text-sm"
                >
                  <option value="ALL">Todos</option>
                  <option value="ACTIVE">Ativos</option>
                  <option value="BLOCKED">Bloqueados</option>
                </select>
              </div>
            </div>

            {loading ? (
              <EmptyState>Carregando clientes...</EmptyState>
            ) : filteredClients.length > 0 ? (
              <div className="overflow-x-auto">
                <table className="w-full min-w-[760px] text-left text-sm">
                  <thead className="text-xs text-[var(--maried-cocoa)]">
                    <tr>
                      <th className="py-2">Nome</th>
                      <th>E-mail</th>
                      <th>Plano</th>
                      <th>Assinatura</th>
                      <th>Créditos</th>
                      <th>Conta</th>
                      <th></th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[var(--maried-sand)]">
                    {filteredClients.map((client) => (
                      <tr key={client.id}>
                        <td className="py-3 font-medium text-[var(--maried-espresso)]">{client.name}</td>
                        <td>{client.user?.email ?? "-"}</td>
                        <td>{client.subscription?.plan_name ?? "-"}</td>
                        <td>{client.subscription?.status ?? client.operational_status}</td>
                        <td>{client.wallet?.available_balance ?? 0}</td>
                        <td>{client.is_active ? "Ativa" : "Bloqueada"}</td>
                        <td className="text-right">
                          <Link className="font-medium text-[var(--maried-gold)]" href={`/superadmin/clientes/${client.id}`}>
                            Ver cliente
                          </Link>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <EmptyState>Nenhum cliente encontrado.</EmptyState>
            )}
          </AdminCard>
        </div>
      </div>
    </SuperAdminShell>
  );
}


function TextInput({
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
      <input
        required
        type={type}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className="h-10 w-full rounded-xl border border-[var(--maried-sand)] bg-white px-3 text-sm"
      />
    </label>
  );
}

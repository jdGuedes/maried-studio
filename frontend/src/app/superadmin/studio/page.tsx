"use client";

import { useEffect, useState, type FormEvent } from "react";

import {
  AdminCard,
  EmptyState,
  StatusMessage,
  SuperAdminShell,
} from "@/components/superadmin/superadmin-shell";
import {
  createSuperAdminSceneTemplate,
  getModelReferences,
  getSuperAdminSceneTemplates,
  updateSuperAdminSceneTemplate,
  type SuperAdminSceneTemplate,
} from "@/lib/api";
import type {
  ModelReference,
  ProductCategory,
} from "@/types/api";


const categories: ProductCategory[] = [
  "EARRING",
  "NECKLACE",
  "RING",
  "BRACELET",
  "ANKLET",
];


const emptyTemplate = {
  name: "",
  slug: "",
  generation_mode: "INSTAGRAM" as const,
  category: "EARRING" as ProductCategory,
  prompt_template: "",
  version: 1,
  is_active: true,
  sort_order: 10,
};


export default function SuperAdminStudioPage() {
  const [templates, setTemplates] = useState<SuperAdminSceneTemplate[]>([]);
  const [models, setModels] = useState<ModelReference[]>([]);
  const [form, setForm] = useState(emptyTemplate);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  async function load() {
    const [
      templateData,
      modelData,
    ] = await Promise.all([
      getSuperAdminSceneTemplates(),
      getModelReferences(),
    ]);

    setTemplates(templateData);
    setModels(modelData);
  }

  useEffect(() => {
    let active = true;

    void (async () => {
      try {
        const [
          templateData,
          modelData,
        ] = await Promise.all([
          getSuperAdminSceneTemplates(),
          getModelReferences(),
        ]);

        if (active) {
          setTemplates(templateData);
          setModels(modelData);
        }
      } catch (error) {
        if (active) {
          setError(error instanceof Error ? error.message : "Erro ao carregar Studio.");
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

  function edit(template: SuperAdminSceneTemplate) {
    setEditingId(template.id);
    setForm({
      name: template.name,
      slug: template.slug,
      generation_mode: "INSTAGRAM",
      category: template.category,
      prompt_template: template.prompt_template,
      version: template.version,
      is_active: template.is_active,
      sort_order: template.sort_order,
    });
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSaving(true);
    setError(null);
    setMessage(null);

    try {
      if (editingId) {
        await updateSuperAdminSceneTemplate(editingId, form);
        setMessage("SceneTemplate atualizado.");
      } else {
        await createSuperAdminSceneTemplate(form);
        setMessage("SceneTemplate criado.");
      }

      setEditingId(null);
      setForm(emptyTemplate);
      await load();
    } catch (error) {
      setError(error instanceof Error ? error.message : "Erro ao salvar SceneTemplate.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <SuperAdminShell title="Studio" subtitle="Configurações globais seguras do motor visual.">
      <div className="grid gap-5 xl:grid-cols-[360px_1fr]">
        <AdminCard>
          <h2 className="mb-4 text-sm font-semibold text-[var(--maried-espresso)]">
            {editingId ? "Editar SceneTemplate" : "Criar SceneTemplate"}
          </h2>

          <form onSubmit={(event) => void submit(event)} className="space-y-3">
            <Input label="Nome" value={form.name} onChange={(name) => setForm({ ...form, name })} />
            <Input label="Slug" value={form.slug} onChange={(slug) => setForm({ ...form, slug })} />
            <select value={form.category} onChange={(event) => setForm({ ...form, category: event.target.value as ProductCategory })} className="h-10 w-full rounded-xl border border-[var(--maried-sand)] bg-white px-3 text-sm">
              {categories.map((category) => (
                <option key={category} value={category}>{category}</option>
              ))}
            </select>
            <textarea required value={form.prompt_template} onChange={(event) => setForm({ ...form, prompt_template: event.target.value })} placeholder="Prompt template" className="min-h-28 w-full rounded-xl border border-[var(--maried-sand)] p-3 text-sm" />
            <Input label="Versão" type="number" value={String(form.version)} onChange={(value) => setForm({ ...form, version: Number(value) })} />
            <Input label="Ordem" type="number" value={String(form.sort_order)} onChange={(value) => setForm({ ...form, sort_order: Number(value) })} />
            <label className="flex items-center gap-2 text-sm text-[var(--maried-cocoa)]">
              <input type="checkbox" checked={form.is_active} onChange={(event) => setForm({ ...form, is_active: event.target.checked })} />
              Ativo
            </label>
            <button disabled={saving} type="submit" className="h-10 w-full rounded-xl bg-[var(--maried-coffee)] px-4 text-sm text-white disabled:opacity-60">
              Salvar cenário
            </button>
          </form>
        </AdminCard>

        <div className="space-y-5">
          {error ? <StatusMessage text={error} /> : null}
          {message ? <StatusMessage text={message} tone="success" /> : null}

          <AdminCard>
            <h2 className="mb-4 text-sm font-semibold text-[var(--maried-espresso)]">SceneTemplates</h2>
            {loading ? (
              <EmptyState>Carregando cenários...</EmptyState>
            ) : templates.length > 0 ? (
              <div className="overflow-x-auto">
                <table className="w-full min-w-[760px] text-left text-sm">
                  <thead className="text-xs text-[var(--maried-cocoa)]">
                    <tr>
                      <th className="py-2">Nome</th>
                      <th>Modo</th>
                      <th>Categoria</th>
                      <th>Versão</th>
                      <th>Ativo</th>
                      <th>Ordem</th>
                      <th></th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[var(--maried-sand)]">
                    {templates.map((template) => (
                      <tr key={template.id}>
                        <td className="py-3 font-medium text-[var(--maried-espresso)]">{template.name}</td>
                        <td>{template.generation_mode}</td>
                        <td>{template.category}</td>
                        <td>{template.version}</td>
                        <td>{template.is_active ? "Ativo" : "Inativo"}</td>
                        <td>{template.sort_order}</td>
                        <td className="text-right">
                          <button type="button" onClick={() => edit(template)} className="font-medium text-[var(--maried-gold)]">Editar</button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <EmptyState>Nenhum SceneTemplate cadastrado.</EmptyState>
            )}
          </AdminCard>

          <AdminCard>
            <h2 className="mb-4 text-sm font-semibold text-[var(--maried-espresso)]">ModelReferences</h2>
            {models.length > 0 ? (
              <div className="grid gap-3 md:grid-cols-2">
                {models.map((model) => (
                  <div key={model.id} className="rounded-xl border border-[var(--maried-sand)] p-3 text-sm">
                    <div className="font-medium text-[var(--maried-espresso)]">{model.name}</div>
                    <div className="mt-1 text-xs text-[var(--maried-cocoa)]">{model.skin_tone} · {model.hair_color} · {model.age_range}</div>
                  </div>
                ))}
              </div>
            ) : (
              <EmptyState>Nenhum ModelReference ativo encontrado.</EmptyState>
            )}
          </AdminCard>

          <AdminCard>
            <h2 className="mb-2 text-sm font-semibold text-[var(--maried-espresso)]">GenerationRules</h2>
            <EmptyState>Não há endpoint administrativo seguro de leitura para GenerationRules nesta tarefa.</EmptyState>
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

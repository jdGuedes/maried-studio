"use client";

import { CalendarDays, Download, ExternalLink, ImageIcon, LoaderCircle, RefreshCw, Search, Trash2, X } from "lucide-react";
import { motion } from "motion/react";
import Image from "next/image";
import { useCallback, useEffect, useMemo, useState } from "react";
import { deleteGeneratedImage, getGenerations, type Generation } from "@/lib/generations";
import { AppShell } from "@/components/layout/app-shell";

const MODES = [
  ["", "Todos os resultados"], ["STILL", "Still"], ["BODY_DETAIL", "Detalhe no Corpo"],
  ["INSTAGRAM", "Instagramável"], ["MODEL", "Na Modelo"],
];
const STATUSES = [
  ["", "Todos os status"], ["COMPLETED", "Concluídas"], ["PROCESSING", "Processando"],
  ["CREDIT_RESERVED", "Crédito reservado"], ["FAILED", "Falharam"],
];

function formatDate(value: string | null) {
  if (!value) return "—";
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return "—";
  return new Intl.DateTimeFormat("pt-BR", { day: "2-digit", month: "2-digit", year: "numeric" }).format(d);
}
function statusLabel(value: string) {
  return ({ CREATED:"Criada", CREDIT_RESERVED:"Crédito reservado", PROCESSING:"Processando", COMPLETED:"Concluída", FAILED:"Falhou" } as Record<string,string>)[value] ?? value;
}
function complement(g: Generation) {
  if (g.model_reference_name) return { label:"Modelo", value:g.model_reference_name };
  if (g.scene_template_name) return { label:"Estilo", value:g.scene_template_name };
  return null;
}
function Detail({ label, value }: { label:string; value:string }) {
  return <div><p className="text-[10px] uppercase tracking-[0.16em] text-[var(--maried-caramel)]">{label}</p><p className="mt-1 text-sm font-medium text-[var(--maried-espresso)]">{value}</p></div>;
}

export default function CreationsPage() {
  const [items,setItems] = useState<Generation[]>([]);
  const [count,setCount] = useState(0);
  const [loading,setLoading] = useState(true);
  const [error,setError] = useState<string|null>(null);
  const [search,setSearch] = useState("");
  const [q,setQ] = useState("");
  const [mode,setMode] = useState("");
  const [status,setStatus] = useState("");
  const [startDate,setStartDate] = useState("");
  const [endDate,setEndDate] = useState("");
  const [selected,setSelected] = useState<Generation|null>(null);
  const [deletingImageId,setDeletingImageId] = useState<string|null>(null);

  const prepareLoad = useCallback(() => {
    setLoading(true); setError(null);
  }, []);

  useEffect(() => {
    const timer = window.setTimeout(() => { prepareLoad(); setQ(search.trim()); }, 350);
    return () => window.clearTimeout(timer);
  }, [search, prepareLoad]);

  const requestGenerations = useCallback(() => {
    return getGenerations({
        q:q||undefined, mode:mode||undefined, status:status||undefined,
        startDate:startDate||undefined, endDate:endDate||undefined,
      });
  }, [q,mode,status,startDate,endDate]);

  const load = useCallback(async () => {
    try {
      const data = await requestGenerations();
      setItems(data.results); setCount(data.count);
    } catch (e) {
      console.error(e);
      setError(e instanceof Error ? e.message : "Não foi possível carregar suas criações.");
    } finally { setLoading(false); }
  }, [requestGenerations]);

  useEffect(() => {
    let active = true;
    requestGenerations()
      .then(data => {
        if (!active) return;
        setItems(data.results); setCount(data.count);
      })
      .catch(e => {
        if (!active) return;
        console.error(e);
        setError(e instanceof Error ? e.message : "Não foi possível carregar suas criações.");
      })
      .finally(() => {
        if (!active) return;
        setLoading(false);
      });
    return () => { active = false; };
  }, [requestGenerations]);
  useEffect(() => {
    if (!selected) return;
    const fn = (e:KeyboardEvent) => { if (e.key === "Escape") setSelected(null); };
    window.addEventListener("keydown",fn);
    return () => window.removeEventListener("keydown",fn);
  }, [selected]);

  const hasFilters = useMemo(() => Boolean(q||mode||status||startDate||endDate), [q,mode,status,startDate,endDate]);
  const clear = () => { prepareLoad(); setSearch(""); setQ(""); setMode(""); setStatus(""); setStartDate(""); setEndDate(""); };
  const download = (g:Generation) => {
    if (!g.image_url) return;
    const a=document.createElement("a"); a.href=g.image_url; a.download=`${g.product_name||"maried-studio"}.png`;
    a.target="_blank"; a.rel="noopener noreferrer"; document.body.appendChild(a); a.click(); a.remove();
  };
  const removeGeneratedImage = async (g:Generation) => {
    if (!g.generated_image_id) return;
    const confirmed = window.confirm("Excluir esta imagem permanentemente?\n\nEsta ação não poderá ser desfeita.");
    if (!confirmed) return;
    setDeletingImageId(g.generated_image_id);
    try {
      await deleteGeneratedImage(g.generated_image_id);
      setItems(current => current.filter(item => item.id !== g.id));
      setCount(current => Math.max(current - 1, 0));
      if (selected?.id === g.id) setSelected(null);
    } catch (e) {
      console.error(e);
      setError(e instanceof Error ? e.message : "Não foi possível excluir esta imagem.");
    } finally {
      setDeletingImageId(null);
    }
  };

  return (
    <AppShell>
      <div className="px-4 py-6 sm:px-6 lg:px-8 lg:py-8">
      <div className="mx-auto max-w-[1240px]">
        <section className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
          <div><h1 className="text-[30px] font-semibold tracking-[-0.035em] text-[var(--maried-espresso)] sm:text-[36px]">Minhas criações</h1>
          <p className="mt-2 text-sm text-[var(--maried-cocoa)]">Visualize todas as imagens criadas no MARIED STUDIO.</p></div>
          {!loading && <div className="text-xs text-[var(--maried-caramel)]">{count} {count===1?"criação":"criações"}</div>}
        </section>

        <section className="maried-card mt-7 p-3 sm:p-4">
          <div className="grid gap-2 lg:grid-cols-[minmax(240px,1fr)_190px_170px_150px_150px]">
            <label className="relative"><Search size={17} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-[var(--maried-caramel)]"/>
              <input type="search" value={search} onChange={e=>setSearch(e.target.value)} placeholder="Buscar por peça..." className="h-11 w-full rounded-xl border border-[var(--maried-sand)] bg-white pl-10 pr-3 text-sm outline-none focus:border-[var(--maried-gold)]"/></label>
            <select value={mode} onChange={e=>{ prepareLoad(); setMode(e.target.value); }} className="h-11 rounded-xl border border-[var(--maried-sand)] bg-white px-3 text-sm">{MODES.map(([v,l])=><option key={v} value={v}>{l}</option>)}</select>
            <select value={status} onChange={e=>{ prepareLoad(); setStatus(e.target.value); }} className="h-11 rounded-xl border border-[var(--maried-sand)] bg-white px-3 text-sm">{STATUSES.map(([v,l])=><option key={v} value={v}>{l}</option>)}</select>
            <label className="relative"><CalendarDays size={15} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-[var(--maried-caramel)]"/><input aria-label="Data inicial" type="date" value={startDate} onChange={e=>{ prepareLoad(); setStartDate(e.target.value); }} className="h-11 w-full rounded-xl border border-[var(--maried-sand)] bg-white pl-9 pr-2 text-xs"/></label>
            <label className="relative"><CalendarDays size={15} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-[var(--maried-caramel)]"/><input aria-label="Data final" type="date" value={endDate} onChange={e=>{ prepareLoad(); setEndDate(e.target.value); }} className="h-11 w-full rounded-xl border border-[var(--maried-sand)] bg-white pl-9 pr-2 text-xs"/></label>
          </div>
          {hasFilters && <div className="mt-3 flex justify-end"><button type="button" onClick={clear} className="flex items-center gap-1.5 text-xs font-medium text-[var(--maried-caramel)]"><X size={14}/>Limpar filtros</button></div>}
        </section>

        {error && <section className="mt-6 rounded-2xl border border-red-200 bg-red-50 px-4 py-4"><div className="flex items-center justify-between gap-3"><p className="text-sm text-red-700">{error}</p><button type="button" onClick={()=>{ prepareLoad(); void load(); }} className="flex items-center gap-2 text-xs font-semibold text-red-700"><RefreshCw size={14}/>Tentar novamente</button></div></section>}
        {loading && <section className="mt-7 flex min-h-[320px] items-center justify-center"><div className="flex flex-col items-center"><LoaderCircle size={32} className="animate-spin text-[var(--maried-gold)]"/><p className="mt-3 text-xs text-[var(--maried-cocoa)]">Carregando suas criações...</p></div></section>}
        {!loading&&!error&&items.length===0 && <section className="maried-card mt-7 flex min-h-[320px] flex-col items-center justify-center px-6 text-center"><div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-[var(--maried-soft-gold)]"><ImageIcon size={24} className="text-[var(--maried-gold)]"/></div><h2 className="mt-4 text-base font-semibold">Nenhuma criação encontrada</h2><p className="mt-2 text-sm text-[var(--maried-cocoa)]">{hasFilters?"Nenhum resultado corresponde aos filtros selecionados.":"Suas imagens geradas aparecerão aqui."}</p>{hasFilters&&<button type="button" onClick={clear} className="mt-5 text-sm font-medium text-[var(--maried-gold)]">Limpar filtros</button>}</section>}

        {!loading&&!error&&items.length>0 && <section className="mt-7 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          {items.map(g => {
            const extra=complement(g);
            return <motion.article key={g.id} whileHover={{y:-3}} className="overflow-hidden rounded-2xl border border-[var(--maried-sand)] bg-white shadow-sm">
              <button type="button" onClick={()=>setSelected(g)} className="block w-full text-left">
                <div className="relative aspect-square bg-[var(--maried-cream)]">
                  {g.image_url?<Image src={g.image_url} alt={g.product_name||"Criação MARIED STUDIO"} fill unoptimized className="object-cover" sizes="(max-width:640px) 100vw,25vw"/>:<div className="flex h-full items-center justify-center"><ImageIcon size={28}/></div>}
                </div>
                <div className="p-4">
                  <div className="flex items-start justify-between gap-2"><span className="rounded-full bg-[var(--maried-soft-gold)] px-2.5 py-1 text-[10px] font-medium">{g.mode_label}</span><span className="text-[10px] text-[var(--maried-caramel)]">{statusLabel(g.status)}</span></div>
                  <h2 className="mt-3 truncate text-sm font-semibold">{g.product_name||"Peça sem nome"}</h2>
                  <p className="mt-1 text-xs text-[var(--maried-cocoa)]">{g.category_label}</p>
                  {extra&&<p className="mt-2 truncate text-[11px] text-[var(--maried-caramel)]">{extra.label}: {extra.value}</p>}
                  <p className="mt-3 text-[10px] text-[var(--maried-caramel)]">{formatDate(g.completed_at??g.created_at)}</p>
                </div>
              </button>
            </motion.article>;
          })}
        </section>}
      </div>

      {selected && <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/50 p-4 backdrop-blur-sm" onMouseDown={()=>setSelected(null)} role="presentation">
        <motion.div initial={{opacity:0,scale:.97}} animate={{opacity:1,scale:1}} onMouseDown={e=>e.stopPropagation()} className="max-h-[92vh] w-full max-w-5xl overflow-hidden rounded-3xl bg-white shadow-2xl" role="dialog" aria-modal="true" aria-label="Detalhes da criação">
          <div className="flex items-center justify-between border-b border-[var(--maried-sand)] px-5 py-4">
            <div className="min-w-0"><h2 className="truncate text-lg font-semibold">{selected.product_name||"Peça sem nome"}</h2><p className="mt-0.5 text-xs text-[var(--maried-cocoa)]">{selected.mode_label}</p></div>
            <button type="button" onClick={()=>setSelected(null)} aria-label="Fechar" className="flex h-9 w-9 items-center justify-center rounded-full hover:bg-[var(--maried-cream)]"><X size={18}/></button>
          </div>
          <div className="grid max-h-[calc(92vh-72px)] overflow-y-auto lg:grid-cols-[minmax(0,1.25fr)_minmax(300px,0.75fr)]">
            <div className="relative min-h-[360px] bg-[var(--maried-cream)] sm:min-h-[520px]">
              {selected.image_url?<Image src={selected.image_url} alt={selected.product_name||"Criação MARIED STUDIO"} fill unoptimized className="object-contain p-4" sizes="(max-width:1024px) 100vw,65vw"/>:<div className="flex h-full items-center justify-center"><ImageIcon size={38}/></div>}
            </div>
            <div className="p-5 sm:p-6">
              <div className="space-y-5">
                <Detail label="Resultado" value={selected.mode_label}/>
                <Detail label="Categoria" value={selected.category_label}/>
                <Detail label="Status" value={statusLabel(selected.status)}/>
                {complement(selected)&&<Detail label={complement(selected)!.label} value={complement(selected)!.value}/>}
                <Detail label="Criada em" value={formatDate(selected.created_at)}/>
                <Detail label="Concluída em" value={formatDate(selected.completed_at)}/>
              </div>
              <div className="mt-8 grid gap-2">
                {selected.image_url ? <>
                  <a href={selected.image_url} target="_blank" rel="noopener noreferrer" className="flex h-11 items-center justify-center gap-2 rounded-xl border border-[var(--maried-sand)] text-sm font-medium text-[var(--maried-coffee)] hover:bg-[var(--maried-cream)]"><ExternalLink size={16}/>Abrir imagem</a>
                  <button type="button" onClick={()=>download(selected)} className="flex h-11 items-center justify-center gap-2 rounded-xl bg-[var(--maried-gold)] text-sm font-semibold text-white hover:opacity-90"><Download size={16}/>Baixar imagem</button>
                  <button type="button" disabled={!selected.generated_image_id||deletingImageId===selected.generated_image_id} onClick={()=>{ void removeGeneratedImage(selected); }} className="flex h-11 items-center justify-center gap-2 rounded-xl border border-red-200 text-sm font-semibold text-red-600 hover:bg-red-50 disabled:opacity-50"><Trash2 size={16}/>{deletingImageId===selected.generated_image_id?"Excluindo...":"Excluir imagem"}</button>
                </> : <div className="rounded-xl bg-[var(--maried-cream)] px-4 py-3 text-center text-xs">Esta criação ainda não possui uma imagem disponível.</div>}
              </div>
            </div>
          </div>
        </motion.div>
      </div>}
      </div>
    </AppShell>
  );
}

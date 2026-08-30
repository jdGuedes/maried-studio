"use client";

import {
  CalendarDays,
  Download,
  ExternalLink,
  ImageIcon,
  LoaderCircle,
  RefreshCw,
  Search,
  Trash2,
  X,
} from "lucide-react";

import {
  motion,
} from "motion/react";

import Image from "next/image";

import {
  useRouter,
  useSearchParams,
} from "next/navigation";

import {
  Suspense,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";

import {
  AppShell,
} from "@/components/layout/app-shell";

import {
  Pagination,
} from "@/components/pagination/pagination";

import {
  deleteGeneratedImage,
  GenerationsApiError,
  getGenerations,
  type Generation,
} from "@/lib/generations";

import {
  getTotalPages,
  normalizePage,
} from "@/lib/pagination";


const MODES = [
  ["", "Todos os resultados"],
  ["STILL", "Still"],
  ["BODY_DETAIL", "Detalhe no Corpo"],
  ["INSTAGRAM", "Instagramável"],
  ["MODEL", "Na Modelo"],
];


const STATUSES = [
  ["", "Todos os status"],
  ["COMPLETED", "Concluídas"],
  ["PROCESSING", "Processando"],
  ["CREDIT_RESERVED", "Crédito reservado"],
  ["FAILED", "Falharam"],
];


function formatDate(
  value: string | null
) {
  if (!value) {
    return "-";
  }

  const date =
    new Date(
      value
    );

  if (
    Number.isNaN(
      date.getTime()
    )
  ) {
    return "-";
  }

  return new Intl.DateTimeFormat(
    "pt-BR",
    {
      day:
        "2-digit",
      month:
        "2-digit",
      year:
        "numeric",
    }
  ).format(
    date
  );
}


function statusLabel(
  value: string
) {
  return (
    {
      CREATED:
        "Criada",
      CREDIT_RESERVED:
        "Crédito reservado",
      PROCESSING:
        "Processando",
      COMPLETED:
        "Concluída",
      FAILED:
        "Falhou",
    } as Record<string, string>
  )[value] ?? value;
}


function complement(
  generation: Generation
) {
  if (generation.model_reference_name) {
    return {
      label:
        "Modelo",
      value:
        generation.model_reference_name,
    };
  }

  if (generation.scene_template_name) {
    return {
      label:
        "Estilo",
      value:
        generation.scene_template_name,
    };
  }

  return null;
}


function Detail({
  label,
  value,
}: {
  label: string;
  value: string;
}) {
  return (
    <div>
      <p className="text-[10px] uppercase tracking-[0.16em] text-[var(--maried-caramel)]">
        {label}
      </p>

      <p className="mt-1 text-sm font-medium text-[var(--maried-espresso)]">
        {value}
      </p>
    </div>
  );
}


export default function CreationsPage() {
  return (
    <AppShell>
      <Suspense
        fallback={
          <CreationsLoading />
        }
      >
        <CreationsContent />
      </Suspense>
    </AppShell>
  );
}


function CreationsLoading() {
  return (
    <div className="px-4 py-6 sm:px-6 lg:px-8 lg:py-8">
      <div className="mx-auto flex min-h-[420px] max-w-[1240px] items-center justify-center">
        <LoaderCircle
          size={32}
          className="animate-spin text-[var(--maried-gold)]"
        />
      </div>
    </div>
  );
}


function CreationsContent() {
  const router =
    useRouter();

  const searchParams =
    useSearchParams();

  const page =
    normalizePage(
      searchParams.get(
        "page"
      )
    );

  const q =
    searchParams.get(
      "q"
    ) ?? "";

  const mode =
    searchParams.get(
      "mode"
    ) ?? "";

  const status =
    searchParams.get(
      "status"
    ) ?? "";

  const startDate =
    searchParams.get(
      "start_date"
    ) ?? "";

  const endDate =
    searchParams.get(
      "end_date"
    ) ?? "";

  const searchTimer =
    useRef<number | null>(
      null
    );

  const [
    items,
    setItems,
  ] = useState<Generation[]>(
    []
  );

  const [
    count,
    setCount,
  ] = useState(
    0
  );

  const [
    loading,
    setLoading,
  ] = useState(
    true
  );

  const [
    error,
    setError,
  ] = useState<string | null>(
    null
  );

  const [
    selected,
    setSelected,
  ] = useState<Generation | null>(
    null
  );

  const [
    deletingImageId,
    setDeletingImageId,
  ] = useState<string | null>(
    null
  );

  const totalPages =
    getTotalPages(
      count
    );

  const updateUrl =
    useCallback(
      (
        updates: Record<string, string | null>,
        nextPage = 1
      ) => {
        const params =
          new URLSearchParams(
            searchParams.toString()
          );

        Object.entries(
          updates
        ).forEach(
          ([
            key,
            value,
          ]) => {
            if (value) {
              params.set(
                key,
                value
              );
            } else {
              params.delete(
                key
              );
            }
          }
        );

        if (nextPage > 1) {
          params.set(
            "page",
            String(
              nextPage
            )
          );
        } else {
          params.delete(
            "page"
          );
        }

        const query =
          params.toString();

        router.push(
          query
            ? `/criacoes?${query}`
            : "/criacoes",
          {
            scroll:
              false,
          }
        );
      },
      [
        router,
        searchParams,
      ]
    );

  const requestGenerations =
    useCallback(
      () => getGenerations({
        q:
          q || undefined,
        mode:
          mode || undefined,
        status:
          status || undefined,
        startDate:
          startDate || undefined,
        endDate:
          endDate || undefined,
        page,
      }),
      [
        q,
        mode,
        status,
        startDate,
        endDate,
        page,
      ]
    );

  const load =
    useCallback(
      async () => {
        setLoading(
          true
        );

        setError(
          null
        );

        try {
          const data =
            await requestGenerations();

          setItems(
            data.results
          );

          setCount(
            data.count
          );
        } catch (error) {
          if (
            error instanceof GenerationsApiError &&
            error.status === 404 &&
            page > 1
          ) {
            updateUrl(
              {},
              1
            );

            return;
          }

          console.error(
            error
          );

          setError(
            error instanceof Error
              ? error.message
              : "Não foi possível carregar suas criações."
          );
        } finally {
          setLoading(
            false
          );
        }
      },
      [
        requestGenerations,
        page,
        updateUrl,
      ]
    );

  useEffect(() => {
    const timer =
      window.setTimeout(
        () => {
          void load();
        },
        0
      );

    return () => {
      window.clearTimeout(
        timer
      );
    };
  }, [
    load,
  ]);

  useEffect(() => {
    if (!selected) {
      return;
    }

    const onKeyDown = (
      event: KeyboardEvent
    ) => {
      if (event.key === "Escape") {
        setSelected(
          null
        );
      }
    };

    window.addEventListener(
      "keydown",
      onKeyDown
    );

    return () => {
      window.removeEventListener(
        "keydown",
        onKeyDown
      );
    };
  }, [
    selected,
  ]);

  useEffect(() => {
    return () => {
      if (searchTimer.current) {
        window.clearTimeout(
          searchTimer.current
        );
      }
    };
  }, []);

  const hasFilters =
    useMemo(
      () => Boolean(
        q ||
        mode ||
        status ||
        startDate ||
        endDate
      ),
      [
        q,
        mode,
        status,
        startDate,
        endDate,
      ]
    );

  function scheduleSearch(
    value: string
  ) {
    if (searchTimer.current) {
      window.clearTimeout(
        searchTimer.current
      );
    }

    searchTimer.current =
      window.setTimeout(
        () => {
          updateUrl(
            {
              q:
                value.trim() ||
                null,
            },
            1
          );
        },
        350
      );
  }

  function clear() {
    updateUrl(
      {
        q:
          null,
        mode:
          null,
        status:
          null,
        start_date:
          null,
        end_date:
          null,
      },
      1
    );
  }

  function download(
    generation: Generation
  ) {
    if (!generation.image_url) {
      return;
    }

    const anchor =
      document.createElement(
        "a"
      );

    anchor.href =
      generation.image_url;

    anchor.download =
      `${generation.product_name || "maried-studio"}.png`;

    anchor.target =
      "_blank";

    anchor.rel =
      "noopener noreferrer";

    document.body.appendChild(
      anchor
    );

    anchor.click();

    anchor.remove();
  }

  async function removeGeneratedImage(
    generation: Generation
  ) {
    if (!generation.generated_image_id) {
      return;
    }

    const confirmed =
      window.confirm(
        "Excluir esta imagem permanentemente?\n\nEsta ação não poderá ser desfeita."
      );

    if (!confirmed) {
      return;
    }

    setDeletingImageId(
      generation.generated_image_id
    );

    try {
      await deleteGeneratedImage(
        generation.generated_image_id
      );

      if (
        selected?.id ===
        generation.id
      ) {
        setSelected(
          null
        );
      }

      if (
        items.length === 1 &&
        page > 1
      ) {
        updateUrl(
          {},
          page - 1
        );
      } else {
        await load();
      }
    } catch (error) {
      console.error(
        error
      );

      setError(
        error instanceof Error
          ? error.message
          : "Não foi possível excluir esta imagem."
      );
    } finally {
      setDeletingImageId(
        null
      );
    }
  }

  return (
    <div className="px-4 py-6 sm:px-6 lg:px-8 lg:py-8">
      <div className="mx-auto max-w-[1240px]">
        <section className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <h1 className="text-[30px] font-semibold tracking-[-0.035em] text-[var(--maried-espresso)] sm:text-[36px]">
              Minhas criações
            </h1>

            <p className="mt-2 text-sm text-[var(--maried-cocoa)]">
              Visualize todas as imagens criadas no MARIED STUDIO.
            </p>
          </div>

          {!loading ? (
            <div className="text-xs text-[var(--maried-caramel)]">
              {count} {count === 1 ? "criação" : "criações"}
            </div>
          ) : null}
        </section>

        <section className="maried-card mt-7 p-3 sm:p-4">
          <div className="grid gap-2 lg:grid-cols-[minmax(240px,1fr)_190px_170px_150px_150px]">
            <label className="relative">
              <Search
                size={17}
                className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-[var(--maried-caramel)]"
              />

              <input
                key={q}
                type="search"
                defaultValue={q}
                onChange={(
                  event
                ) => {
                  scheduleSearch(
                    event.target.value
                  );
                }}
                placeholder="Buscar por peça..."
                className="h-11 w-full rounded-xl border border-[var(--maried-sand)] bg-white pl-10 pr-3 text-sm outline-none focus:border-[var(--maried-gold)]"
              />
            </label>

            <select
              value={mode}
              onChange={(
                event
              ) => {
                updateUrl(
                  {
                    mode:
                      event.target.value ||
                      null,
                  },
                  1
                );
              }}
              className="h-11 rounded-xl border border-[var(--maried-sand)] bg-white px-3 text-sm"
            >
              {MODES.map(
                ([
                  value,
                  label,
                ]) => (
                  <option
                    key={value}
                    value={value}
                  >
                    {label}
                  </option>
                )
              )}
            </select>

            <select
              value={status}
              onChange={(
                event
              ) => {
                updateUrl(
                  {
                    status:
                      event.target.value ||
                      null,
                  },
                  1
                );
              }}
              className="h-11 rounded-xl border border-[var(--maried-sand)] bg-white px-3 text-sm"
            >
              {STATUSES.map(
                ([
                  value,
                  label,
                ]) => (
                  <option
                    key={value}
                    value={value}
                  >
                    {label}
                  </option>
                )
              )}
            </select>

            <label className="relative">
              <CalendarDays
                size={15}
                className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-[var(--maried-caramel)]"
              />

              <input
                aria-label="Data inicial"
                type="date"
                value={startDate}
                onChange={(
                  event
                ) => {
                  updateUrl(
                    {
                      start_date:
                        event.target.value ||
                        null,
                    },
                    1
                  );
                }}
                className="h-11 w-full rounded-xl border border-[var(--maried-sand)] bg-white pl-9 pr-2 text-xs"
              />
            </label>

            <label className="relative">
              <CalendarDays
                size={15}
                className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-[var(--maried-caramel)]"
              />

              <input
                aria-label="Data final"
                type="date"
                value={endDate}
                onChange={(
                  event
                ) => {
                  updateUrl(
                    {
                      end_date:
                        event.target.value ||
                        null,
                    },
                    1
                  );
                }}
                className="h-11 w-full rounded-xl border border-[var(--maried-sand)] bg-white pl-9 pr-2 text-xs"
              />
            </label>
          </div>

          {hasFilters ? (
            <div className="mt-3 flex justify-end">
              <button
                type="button"
                onClick={clear}
                className="flex items-center gap-1.5 text-xs font-medium text-[var(--maried-caramel)]"
              >
                <X
                  size={14}
                />
                Limpar filtros
              </button>
            </div>
          ) : null}
        </section>

        {error ? (
          <section className="mt-6 rounded-2xl border border-red-200 bg-red-50 px-4 py-4">
            <div className="flex items-center justify-between gap-3">
              <p className="text-sm text-red-700">
                {error}
              </p>

              <button
                type="button"
                onClick={() => {
                  void load();
                }}
                className="flex items-center gap-2 text-xs font-semibold text-red-700"
              >
                <RefreshCw
                  size={14}
                />
                Tentar novamente
              </button>
            </div>
          </section>
        ) : null}

        {loading ? (
          <section className="mt-7 flex min-h-[320px] items-center justify-center">
            <div className="flex flex-col items-center">
              <LoaderCircle
                size={32}
                className="animate-spin text-[var(--maried-gold)]"
              />

              <p className="mt-3 text-xs text-[var(--maried-cocoa)]">
                Carregando suas criações...
              </p>
            </div>
          </section>
        ) : null}

        {!loading &&
        !error &&
        items.length === 0 ? (
          <section className="maried-card mt-7 flex min-h-[320px] flex-col items-center justify-center px-6 text-center">
            <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-[var(--maried-soft-gold)]">
              <ImageIcon
                size={24}
                className="text-[var(--maried-gold)]"
              />
            </div>

            <h2 className="mt-4 text-base font-semibold">
              Nenhuma criação encontrada
            </h2>

            <p className="mt-2 text-sm text-[var(--maried-cocoa)]">
              {hasFilters
                ? "Nenhum resultado corresponde aos filtros selecionados."
                : "Suas imagens geradas aparecerão aqui."}
            </p>

            {hasFilters ? (
              <button
                type="button"
                onClick={clear}
                className="mt-5 text-sm font-medium text-[var(--maried-gold)]"
              >
                Limpar filtros
              </button>
            ) : null}
          </section>
        ) : null}

        {!loading &&
        !error &&
        items.length > 0 ? (
          <>
            <section className="mt-7 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
              {items.map(
                (
                  generation
                ) => {
                  const extra =
                    complement(
                      generation
                    );

                  return (
                    <motion.article
                      key={generation.id}
                      whileHover={{
                        y:
                          -3,
                      }}
                      className="overflow-hidden rounded-2xl border border-[var(--maried-sand)] bg-white shadow-sm"
                    >
                      <button
                        type="button"
                        onClick={() => {
                          setSelected(
                            generation
                          );
                        }}
                        className="block w-full text-left"
                      >
                        <div className="relative aspect-square bg-[var(--maried-cream)]">
                          {generation.image_url ? (
                            <Image
                              src={generation.image_url}
                              alt={
                                generation.product_name ||
                                "Criação MARIED STUDIO"
                              }
                              fill
                              unoptimized
                              className="object-cover"
                              sizes="(max-width: 640px) 100vw, 25vw"
                            />
                          ) : (
                            <div className="flex h-full items-center justify-center">
                              <ImageIcon
                                size={28}
                              />
                            </div>
                          )}
                        </div>

                        <div className="p-4">
                          <div className="flex items-start justify-between gap-2">
                            <span className="rounded-full bg-[var(--maried-soft-gold)] px-2.5 py-1 text-[10px] font-medium">
                              {generation.mode_label}
                            </span>

                            <span className="text-[10px] text-[var(--maried-caramel)]">
                              {statusLabel(
                                generation.status
                              )}
                            </span>
                          </div>

                          <h2 className="mt-3 truncate text-sm font-semibold">
                            {generation.product_name || "Peça sem nome"}
                          </h2>

                          <p className="mt-1 text-xs text-[var(--maried-cocoa)]">
                            {generation.category_label}
                          </p>

                          {extra ? (
                            <p className="mt-2 truncate text-[11px] text-[var(--maried-caramel)]">
                              {extra.label}: {extra.value}
                            </p>
                          ) : null}

                          <p className="mt-3 text-[10px] text-[var(--maried-caramel)]">
                            {formatDate(
                              generation.completed_at ??
                              generation.created_at
                            )}
                          </p>
                        </div>
                      </button>
                    </motion.article>
                  );
                }
              )}
            </section>

            <Pagination
              page={page}
              totalPages={totalPages}
              loading={loading}
              onPageChange={(
                nextPage
              ) => {
                updateUrl(
                  {},
                  nextPage
                );
              }}
            />
          </>
        ) : null}
      </div>

      {selected ? (
        <div
          className="fixed inset-0 z-[100] flex items-center justify-center bg-black/50 p-4 backdrop-blur-sm"
          onMouseDown={() => {
            setSelected(
              null
            );
          }}
          role="presentation"
        >
          <motion.div
            initial={{
              opacity:
                0,
              scale:
                0.97,
            }}
            animate={{
              opacity:
                1,
              scale:
                1,
            }}
            onMouseDown={(
              event
            ) => {
              event.stopPropagation();
            }}
            className="max-h-[92vh] w-full max-w-5xl overflow-hidden rounded-3xl bg-white shadow-2xl"
            role="dialog"
            aria-modal="true"
            aria-label="Detalhes da criação"
          >
            <div className="flex items-center justify-between border-b border-[var(--maried-sand)] px-5 py-4">
              <div className="min-w-0">
                <h2 className="truncate text-lg font-semibold">
                  {selected.product_name || "Peça sem nome"}
                </h2>

                <p className="mt-0.5 text-xs text-[var(--maried-cocoa)]">
                  {selected.mode_label}
                </p>
              </div>

              <button
                type="button"
                onClick={() => {
                  setSelected(
                    null
                  );
                }}
                aria-label="Fechar"
                className="flex h-9 w-9 items-center justify-center rounded-full hover:bg-[var(--maried-cream)]"
              >
                <X
                  size={18}
                />
              </button>
            </div>

            <div className="grid max-h-[calc(92vh-72px)] overflow-y-auto lg:grid-cols-[minmax(0,1.25fr)_minmax(300px,0.75fr)]">
              <div className="relative min-h-[360px] bg-[var(--maried-cream)] sm:min-h-[520px]">
                {selected.image_url ? (
                  <Image
                    src={selected.image_url}
                    alt={
                      selected.product_name ||
                      "Criação MARIED STUDIO"
                    }
                    fill
                    unoptimized
                    className="object-contain p-4"
                    sizes="(max-width: 1024px) 100vw, 65vw"
                  />
                ) : (
                  <div className="flex h-full items-center justify-center">
                    <ImageIcon
                      size={38}
                    />
                  </div>
                )}
              </div>

              <div className="p-5 sm:p-6">
                <div className="space-y-5">
                  <Detail
                    label="Resultado"
                    value={selected.mode_label}
                  />

                  <Detail
                    label="Categoria"
                    value={selected.category_label}
                  />

                  <Detail
                    label="Status"
                    value={statusLabel(
                      selected.status
                    )}
                  />

                  {complement(
                    selected
                  ) ? (
                    <Detail
                      label={
                        complement(
                          selected
                        )!.label
                      }
                      value={
                        complement(
                          selected
                        )!.value
                      }
                    />
                  ) : null}

                  <Detail
                    label="Criada em"
                    value={formatDate(
                      selected.created_at
                    )}
                  />

                  <Detail
                    label="Concluída em"
                    value={formatDate(
                      selected.completed_at
                    )}
                  />
                </div>

                <div className="mt-8 grid gap-2">
                  {selected.image_url ? (
                    <>
                      <a
                        href={selected.image_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="flex h-11 items-center justify-center gap-2 rounded-xl border border-[var(--maried-sand)] text-sm font-medium text-[var(--maried-coffee)] hover:bg-[var(--maried-cream)]"
                      >
                        <ExternalLink
                          size={16}
                        />
                        Abrir imagem
                      </a>

                      <button
                        type="button"
                        onClick={() => {
                          download(
                            selected
                          );
                        }}
                        className="flex h-11 items-center justify-center gap-2 rounded-xl bg-[var(--maried-gold)] text-sm font-semibold text-white hover:opacity-90"
                      >
                        <Download
                          size={16}
                        />
                        Baixar imagem
                      </button>

                      <button
                        type="button"
                        disabled={
                          !selected.generated_image_id ||
                          deletingImageId ===
                            selected.generated_image_id
                        }
                        onClick={() => {
                          void removeGeneratedImage(
                            selected
                          );
                        }}
                        className="flex h-11 items-center justify-center gap-2 rounded-xl border border-red-200 text-sm font-semibold text-red-600 hover:bg-red-50 disabled:opacity-50"
                      >
                        <Trash2
                          size={16}
                        />
                        {deletingImageId ===
                        selected.generated_image_id
                          ? "Excluindo..."
                          : "Excluir imagem"}
                      </button>
                    </>
                  ) : (
                    <div className="rounded-xl bg-[var(--maried-cream)] px-4 py-3 text-center text-xs">
                      Esta criação ainda não possui uma imagem disponível.
                    </div>
                  )}
                </div>
              </div>
            </div>
          </motion.div>
        </div>
      ) : null}
    </div>
  );
}

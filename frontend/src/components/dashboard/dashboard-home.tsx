"use client";

import {
  ArrowRight,
  CalendarDays,
  Gem,
  ImageIcon,
  LoaderCircle,
  Plus,
  RefreshCw,
  X,
} from "lucide-react";

import {
  motion,
} from "motion/react";

import Image from "next/image";

import Link from "next/link";

import {
  useCallback,
  useEffect,
  useState,
} from "react";

import {
  getDashboard,
  type DashboardData,
} from "@/lib/dashboard";

import {
  useCreditWallet,
} from "@/providers/credit-wallet-provider";

import {
  useProfile,
} from "@/providers/profile-provider";


// ==========================================================
// TIPOS
// ==========================================================

type FilterTarget =
  | "generations"
  | "products";


type FilterPreset =
  | "TODAY"
  | "LAST_7_DAYS"
  | "THIS_MONTH"
  | "LAST_MONTH"
  | "CUSTOM";


// ==========================================================
// UTILITÁRIOS DE DATA
// ==========================================================

function toDateInput(
  date: Date
) {
  const year =
    date.getFullYear();

  const month =
    String(
      date.getMonth() + 1
    ).padStart(
      2,
      "0"
    );

  const day =
    String(
      date.getDate()
    ).padStart(
      2,
      "0"
    );

  return `${year}-${month}-${day}`;
}


function getPeriodFromPreset(
  preset:
    Exclude<
      FilterPreset,
      "CUSTOM"
    >
) {
  const today =
    new Date();

  const end =
    new Date(
      today
    );

  let start =
    new Date(
      today
    );


  if (
    preset ===
    "TODAY"
  ) {
    return {
      start:
        toDateInput(
          today
        ),

      end:
        toDateInput(
          today
        ),
    };
  }


  if (
    preset ===
    "LAST_7_DAYS"
  ) {
    start.setDate(
      today.getDate() -
        6
    );

    return {
      start:
        toDateInput(
          start
        ),

      end:
        toDateInput(
          end
        ),
    };
  }


  if (
    preset ===
    "THIS_MONTH"
  ) {
    start =
      new Date(
        today.getFullYear(),
        today.getMonth(),
        1
      );

    end.setMonth(
      today.getMonth() +
        1,
      0
    );

    return {
      start:
        toDateInput(
          start
        ),

      end:
        toDateInput(
          end
        ),
    };
  }


  const firstDayLastMonth =
    new Date(
      today.getFullYear(),
      today.getMonth() -
        1,
      1
    );


  const lastDayLastMonth =
    new Date(
      today.getFullYear(),
      today.getMonth(),
      0
    );


  return {
    start:
      toDateInput(
        firstDayLastMonth
      ),

    end:
      toDateInput(
        lastDayLastMonth
      ),
  };
}


// ==========================================================
// LABEL DO PERÍODO
// ==========================================================

function formatDateBR(
  value: string
) {
  const [
    year,
    month,
    day,
  ] =
    value.split(
      "-"
    );

  return `${day}/${month}/${year}`;
}


function formatPeriodLabel(
  startDate: string,
  endDate: string
) {
  return `${formatDateBR(
    startDate
  )} → ${formatDateBR(
    endDate
  )}`;
}


// ==========================================================
// COMPONENTE
// ==========================================================

export function DashboardHome() {

  // ========================================================
  // PERFIL REAL
  // ========================================================

  const {
    firstName,

    loading:
      loadingProfile,
  } =
    useProfile();


  // ========================================================
  // CARTEIRA
  // ========================================================

  const {
    availableCredits,
    refreshWallet,
  } =
    useCreditWallet();


  // ========================================================
  // DASHBOARD
  // ========================================================

  const [
    dashboard,
    setDashboard,
  ] = useState<DashboardData | null>(
    null
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


  // ========================================================
  // SAUDAÇÃO DINÂMICA
  // ========================================================

  const [
    greeting,
    setGreeting,
  ] = useState(
    "Olá"
  );


  useEffect(() => {

    function updateGreeting() {

      const hour =
        new Date()
          .getHours();


      if (
        hour < 12
      ) {
        setGreeting(
          "Bom dia"
        );

        return;
      }


      if (
        hour < 18
      ) {
        setGreeting(
          "Boa tarde"
        );

        return;
      }


      setGreeting(
        "Boa noite"
      );
    }


    updateGreeting();


    const timer =
      window.setInterval(
        updateGreeting,
        60 * 1000
      );


    return () => {
      window.clearInterval(
        timer
      );
    };

  }, []);


  // ========================================================
  // FILTRO ABERTO
  // ========================================================

  const [
    openFilter,
    setOpenFilter,
  ] = useState<FilterTarget | null>(
    null
  );


  // ========================================================
  // CRIAÇÕES
  // ========================================================

  const [
    generationStartDate,
    setGenerationStartDate,
  ] = useState<string | null>(
    null
  );


  const [
    generationEndDate,
    setGenerationEndDate,
  ] = useState<string | null>(
    null
  );


  // ========================================================
  // PEÇAS
  // ========================================================

  const [
    productStartDate,
    setProductStartDate,
  ] = useState<string | null>(
    null
  );


  const [
    productEndDate,
    setProductEndDate,
  ] = useState<string | null>(
    null
  );


  // ========================================================
  // CARREGAR DASHBOARD
  // ========================================================

  const loadDashboard =
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
            await getDashboard({
              generationStartDate,
              generationEndDate,
              productStartDate,
              productEndDate,
            });


          setDashboard(
            data
          );


          await refreshWallet();

        } catch (error) {

          console.error(
            "Erro ao carregar dashboard:",
            error
          );


          setError(
            error instanceof Error
              ? error.message
              : "Não foi possível carregar o Dashboard."
          );

        } finally {

          setLoading(
            false
          );

        }

      },
      [
        generationStartDate,
        generationEndDate,
        productStartDate,
        productEndDate,
        refreshWallet,
      ]
    );


  // ========================================================
  // PRIMEIRO CARREGAMENTO
  // ========================================================

  useEffect(() => {
    const timer =
      window.setTimeout(
        () => {
          void loadDashboard();
        },
        0
      );

    return () => {
      window.clearTimeout(
        timer
      );
    };
  }, [
    loadDashboard,
  ]);


  // ========================================================
  // APLICAR PRESET
  // ========================================================

  function applyPreset(
    target:
      FilterTarget,

    preset:
      Exclude<
        FilterPreset,
        "CUSTOM"
      >
  ) {

    const period =
      getPeriodFromPreset(
        preset
      );


    if (
      target ===
      "generations"
    ) {

      setGenerationStartDate(
        period.start
      );

      setGenerationEndDate(
        period.end
      );

    } else {

      setProductStartDate(
        period.start
      );

      setProductEndDate(
        period.end
      );

    }


    setOpenFilter(
      null
    );
  }


  // ========================================================
  // LIMPAR FILTRO
  // ========================================================

  function clearFilter(
    target:
      FilterTarget
  ) {

    if (
      target ===
      "generations"
    ) {

      setGenerationStartDate(
        null
      );

      setGenerationEndDate(
        null
      );

    } else {

      setProductStartDate(
        null
      );

      setProductEndDate(
        null
      );

    }


    setOpenFilter(
      null
    );
  }


  // ========================================================
  // LABELS
  // ========================================================

  const generationPeriodLabel =
    dashboard
      ? formatPeriodLabel(
          dashboard
            .generations
            .start_date,

          dashboard
            .generations
            .end_date
        )
      : "Este mês";


  const productPeriodLabel =
    dashboard
      ? formatPeriodLabel(
          dashboard
            .products
            .start_date,

          dashboard
            .products
            .end_date
        )
      : "Este mês";


  // ========================================================
  // NOME EXIBIDO
  // ========================================================

  const dashboardName =
    loadingProfile
      ? "..."
      : firstName;


  return (
    <div className="px-4 py-6 sm:px-6 lg:px-8 lg:py-8">

      <div className="mx-auto max-w-[1240px]">

        {/* =================================================
            CABEÇALHO
        ================================================= */}

        <section className="flex flex-col gap-5 lg:flex-row lg:items-start lg:justify-between">

          <div>

            <motion.h1
              initial={{
                opacity:
                  0,

                y:
                  8,
              }}

              animate={{
                opacity:
                  1,

                y:
                  0,
              }}

              className="max-w-xl text-[29px] font-semibold leading-tight tracking-[-0.03em] text-[var(--maried-espresso)] sm:text-[34px]"
            >

              {greeting},{" "}
              {dashboardName}{" "}

              <span className="text-[var(--maried-gold)]">
                ✦
              </span>

            </motion.h1>


            <p className="mt-2 max-w-xl text-sm leading-6 text-[var(--maried-cocoa)]">
              Crie imagens profissionais
              que destacam a beleza e
              o valor das suas semijoias.
            </p>

          </div>


          <motion.a
            href="/criar"

            whileHover={{
              y:
                -1,
            }}

            whileTap={{
              scale:
                0.98,
            }}

            className="hidden h-11 items-center gap-2 rounded-xl bg-[var(--maried-gold)] px-5 text-sm font-medium text-white shadow-[0_10px_28px_rgba(163,141,92,0.20)] lg:flex"
          >

            <Plus
              size={
                17
              }
            />

            Nova criação

          </motion.a>

        </section>


        {/* =================================================
            ERRO
        ================================================= */}

        {error ? (

          <div className="mt-6 flex items-center justify-between gap-4 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-xs text-red-700">

            <span>
              {
                error
              }
            </span>


            <button
              type="button"

              onClick={() => {
                void loadDashboard();
              }}

              className="flex shrink-0 items-center gap-1 font-semibold"
            >

              <RefreshCw
                size={
                  14
                }
              />

              Tentar novamente

            </button>

          </div>

        ) : null}


        {/* =================================================
            CARDS
        ================================================= */}

        <section className="mt-7 grid grid-cols-1 gap-3 sm:grid-cols-3">

          {/* ===============================================
              CRÉDITOS
          =============================================== */}

          <motion.article
            initial={{
              opacity:
                0,

              y:
                12,
            }}

            animate={{
              opacity:
                1,

              y:
                0,
            }}

            className="maried-card p-5"
          >

            <p className="text-xs text-[var(--maried-cocoa)]">
              Créditos disponíveis
            </p>


            <div className="mt-3 min-h-[44px]">

              {loading ? (

                <LoaderCircle
                  size={
                    28
                  }

                  className="animate-spin text-[var(--maried-gold)]"
                />

              ) : (

                <div className="text-4xl font-semibold tracking-[-0.04em]">

                  {
                    availableCredits ??
                    dashboard
                      ?.available_credits ??
                    0
                  }

                </div>

              )}

            </div>


            <button
              type="button"

              className="mt-4 flex items-center gap-1 text-xs font-medium text-[var(--maried-gold)]"
            >

              Adicionar créditos

              <ArrowRight
                size={
                  13
                }
              />

            </button>

          </motion.article>


          {/* ===============================================
              CRIAÇÕES
          =============================================== */}

          <motion.article
            initial={{
              opacity:
                0,

              y:
                12,
            }}

            animate={{
              opacity:
                1,

              y:
                0,
            }}

            transition={{
              delay:
                0.06,
            }}

            className="relative maried-card p-5"
          >

            <div className="flex items-start justify-between gap-3">

              <div>

                <p className="text-xs text-[var(--maried-cocoa)]">
                  Criações
                </p>


                <div className="mt-3 text-4xl font-semibold tracking-[-0.04em]">

                  {loading
                    ? "..."
                    : dashboard
                        ?.generations
                        .count ??
                      0}

                </div>

              </div>


              <button
                type="button"

                onClick={() => {

                  setOpenFilter(
                    openFilter ===
                      "generations"
                      ? null
                      : "generations"
                  );

                }}

                className="flex h-9 w-9 items-center justify-center rounded-xl border border-[var(--maried-sand)] bg-white text-[var(--maried-gold)]"
              >

                <CalendarDays
                  size={
                    17
                  }
                />

              </button>

            </div>


            <div className="mt-4 text-[10px] text-[var(--maried-caramel)]">
              {
                generationPeriodLabel
              }
            </div>


            {openFilter ===
            "generations" ? (

              <FilterPopover
                startDate={
                  generationStartDate
                }

                endDate={
                  generationEndDate
                }

                onStartDate={
                  setGenerationStartDate
                }

                onEndDate={
                  setGenerationEndDate
                }

                onPreset={(
                  preset
                ) => {
                  applyPreset(
                    "generations",
                    preset
                  );
                }}

                onApply={() => {
                  setOpenFilter(
                    null
                  );
                }}

                onClear={() => {
                  clearFilter(
                    "generations"
                  );
                }}

                onClose={() => {
                  setOpenFilter(
                    null
                  );
                }}
              />

            ) : null}

          </motion.article>


          {/* ===============================================
              PEÇAS
          =============================================== */}

          <motion.article
            initial={{
              opacity:
                0,

              y:
                12,
            }}

            animate={{
              opacity:
                1,

              y:
                0,
            }}

            transition={{
              delay:
                0.12,
            }}

            className="relative maried-card p-5"
          >

            <div className="flex items-start justify-between gap-3">

              <div>

                <p className="text-xs text-[var(--maried-cocoa)]">
                  Peças cadastradas
                </p>


                <div className="mt-3 text-4xl font-semibold tracking-[-0.04em]">

                  {loading
                    ? "..."
                    : dashboard
                        ?.products
                        .count ??
                      0}

                </div>

              </div>


              <button
                type="button"

                onClick={() => {

                  setOpenFilter(
                    openFilter ===
                      "products"
                      ? null
                      : "products"
                  );

                }}

                className="flex h-9 w-9 items-center justify-center rounded-xl border border-[var(--maried-sand)] bg-white text-[var(--maried-gold)]"
              >

                <CalendarDays
                  size={
                    17
                  }
                />

              </button>

            </div>


            <div className="mt-4 text-[10px] text-[var(--maried-caramel)]">
              {
                productPeriodLabel
              }
            </div>


            {openFilter ===
            "products" ? (

              <FilterPopover
                startDate={
                  productStartDate
                }

                endDate={
                  productEndDate
                }

                onStartDate={
                  setProductStartDate
                }

                onEndDate={
                  setProductEndDate
                }

                onPreset={(
                  preset
                ) => {
                  applyPreset(
                    "products",
                    preset
                  );
                }}

                onApply={() => {
                  setOpenFilter(
                    null
                  );
                }}

                onClear={() => {
                  clearFilter(
                    "products"
                  );
                }}

                onClose={() => {
                  setOpenFilter(
                    null
                  );
                }}
              />

            ) : null}

          </motion.article>

        </section>


        {/* =================================================
            ÚLTIMAS CRIAÇÕES
        ================================================= */}

        <section className="mt-7">

          <div className="mb-3 flex items-center justify-between">

            <div>

              <h2 className="text-base font-semibold">
                Últimas criações
              </h2>


              <p className="mt-1 text-xs text-[var(--maried-cocoa)]">
                Seus resultados mais recentes.
              </p>

            </div>


            <Link
              href="/criacoes"
              className="text-xs font-medium text-[var(--maried-gold)]"
            >
              Ver todas
            </Link>

          </div>


          {loading ? (

            <div className="maried-card flex min-h-[220px] items-center justify-center">

              <LoaderCircle
                size={
                  30
                }

                className="animate-spin text-[var(--maried-gold)]"
              />

            </div>

          ) : dashboard &&
          dashboard
            .recent_generations
            .length >
            0 ? (

            <div className="grid grid-cols-2 gap-3 md:grid-cols-4">

              {dashboard
                .recent_generations
                .map(
                  (
                    item,
                    index
                  ) => (

                    <motion.article
                      key={
                        item.id
                      }

                      initial={{
                        opacity:
                          0,
                      }}

                      animate={{
                        opacity:
                          1,
                      }}

                      transition={{
                        delay:
                          index *
                          0.05,
                      }}

                      whileHover={{
                        y:
                          -2,
                      }}

                      className="overflow-hidden rounded-[18px] border border-[var(--maried-sand)] bg-white"
                    >

                      <div className="relative aspect-square bg-[var(--maried-cream)]">

                        {item.image_url ? (

                          <Image
                            src={
                              item.image_url
                            }

                            alt={
                              item.product_name
                            }

                            fill

                            unoptimized

                            className="object-cover"
                          />

                        ) : (

                          <div className="flex h-full items-center justify-center">

                            <ImageIcon
                              size={
                                42
                              }

                              strokeWidth={
                                1.15
                              }

                              className="text-[var(--maried-gold)]"
                            />

                          </div>

                        )}

                      </div>


                      <div className="p-3">

                        <div className="inline-flex rounded-full bg-[var(--maried-soft-gold)] px-2 py-1 text-[9px] font-medium text-[var(--maried-coffee)]">
                          {
                            item.mode_label
                          }
                        </div>


                        <h3 className="mt-2 truncate text-xs font-medium leading-5">
                          {
                            item.product_name
                          }
                        </h3>


                        {item.style_name ? (

                          <p className="mt-1 text-[10px] text-[var(--maried-caramel)]">
                            {
                              item.style_name
                            }
                          </p>

                        ) : null}

                      </div>

                    </motion.article>

                  )
                )}

            </div>

          ) : (

            <div className="maried-card flex min-h-[220px] flex-col items-center justify-center px-6 text-center">

              <Gem
                size={
                  34
                }

                className="text-[var(--maried-gold)]"
              />


              <h3 className="mt-4 text-sm font-semibold">
                Nenhuma criação concluída
              </h3>


              <p className="mt-2 text-xs text-[var(--maried-cocoa)]">
                Suas imagens aparecerão aqui
                quando forem geradas.
              </p>

            </div>

          )}

        </section>

      </div>

    </div>
  );
}


// ==========================================================
// POPOVER DE FILTRO
// ==========================================================

type FilterPopoverProps = {
  startDate:
    string | null;

  endDate:
    string | null;

  onStartDate:
    (
      value:
        string
    ) => void;

  onEndDate:
    (
      value:
        string
    ) => void;

  onPreset:
    (
      preset:
        Exclude<
          FilterPreset,
          "CUSTOM"
        >
    ) => void;

  onApply:
    () => void;

  onClear:
    () => void;

  onClose:
    () => void;
};


function FilterPopover({
  startDate,
  endDate,
  onStartDate,
  onEndDate,
  onPreset,
  onApply,
  onClear,
  onClose,
}: FilterPopoverProps) {

  const canApply =
    Boolean(
      startDate &&
      endDate
    );


  return (
    <motion.div
      initial={{
        opacity:
          0,

        y:
          -6,

        scale:
          0.98,
      }}

      animate={{
        opacity:
          1,

        y:
          0,

        scale:
          1,
      }}

      className="absolute right-0 top-[76px] z-40 w-[290px] rounded-[18px] border border-[var(--maried-sand)] bg-white p-4 shadow-[0_20px_60px_rgba(73,53,45,0.16)]"
    >

      <div className="flex items-center justify-between">

        <div>

          <div className="text-sm font-semibold">
            Período
          </div>


          <div className="mt-1 text-[10px] text-[var(--maried-caramel)]">
            Escolha um intervalo.
          </div>

        </div>


        <button
          type="button"

          onClick={
            onClose
          }

          className="flex h-8 w-8 items-center justify-center rounded-lg hover:bg-[var(--maried-cream)]"
        >

          <X
            size={
              15
            }
          />

        </button>

      </div>


      <div className="mt-4 grid grid-cols-2 gap-2">

        <PresetButton
          label="Hoje"

          onClick={() => {
            onPreset(
              "TODAY"
            );
          }}
        />


        <PresetButton
          label="Últimos 7 dias"

          onClick={() => {
            onPreset(
              "LAST_7_DAYS"
            );
          }}
        />


        <PresetButton
          label="Este mês"

          onClick={() => {
            onPreset(
              "THIS_MONTH"
            );
          }}
        />


        <PresetButton
          label="Mês passado"

          onClick={() => {
            onPreset(
              "LAST_MONTH"
            );
          }}
        />

      </div>


      <div className="my-4 h-px bg-[var(--maried-sand)]" />


      <div className="text-[10px] font-medium uppercase tracking-[0.12em] text-[var(--maried-caramel)]">
        Personalizado
      </div>


      <div className="mt-3 grid grid-cols-2 gap-2">

        <label>

          <span className="text-[10px] text-[var(--maried-cocoa)]">
            Início
          </span>


          <input
            type="date"

            value={
              startDate ??
              ""
            }

            onChange={(
              event
            ) => {
              onStartDate(
                event.target.value
              );
            }}

            className="mt-1 h-10 w-full rounded-lg border border-[var(--maried-sand)] px-2 text-[11px] outline-none focus:border-[var(--maried-gold)]"
          />

        </label>


        <label>

          <span className="text-[10px] text-[var(--maried-cocoa)]">
            Fim
          </span>


          <input
            type="date"

            value={
              endDate ??
              ""
            }

            onChange={(
              event
            ) => {
              onEndDate(
                event.target.value
              );
            }}

            className="mt-1 h-10 w-full rounded-lg border border-[var(--maried-sand)] px-2 text-[11px] outline-none focus:border-[var(--maried-gold)]"
          />

        </label>

      </div>


      <div className="mt-4 flex gap-2">

        <button
          type="button"

          onClick={
            onClear
          }

          className="h-10 flex-1 rounded-lg border border-[var(--maried-sand)] text-xs text-[var(--maried-cocoa)]"
        >
          Limpar
        </button>


        <button
          type="button"

          disabled={
            !canApply
          }

          onClick={
            onApply
          }

          className={[
            "h-10 flex-1 rounded-lg text-xs font-medium",

            canApply
              ? "bg-[var(--maried-gold)] text-white"
              : "cursor-not-allowed bg-[var(--maried-sand)] text-[var(--maried-caramel)]",
          ].join(
            " "
          )}
        >
          Aplicar
        </button>

      </div>

    </motion.div>
  );
}


// ==========================================================
// BOTÃO DE PRESET
// ==========================================================

type PresetButtonProps = {
  label: string;

  onClick:
    () => void;
};


function PresetButton({
  label,
  onClick,
}: PresetButtonProps) {

  return (
    <button
      type="button"

      onClick={
        onClick
      }

      className="min-h-[38px] rounded-lg border border-[var(--maried-sand)] bg-white px-2 text-[10px] font-medium text-[var(--maried-cocoa)] transition hover:border-[var(--maried-gold)] hover:bg-[var(--maried-soft-gold)]"
    >
      {
        label
      }
    </button>
  );
}

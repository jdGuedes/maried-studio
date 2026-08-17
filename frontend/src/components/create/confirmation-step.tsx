"use client";

import {
  ArrowLeft,
  Gem,
  LoaderCircle,
  Sparkles,
} from "lucide-react";

import {
  motion,
} from "motion/react";

import Image from "next/image";

import type {
  GenerationMode,
} from "./result-mode-step";

import {
  useCreditWallet,
} from "@/providers/credit-wallet-provider";


// =========================================================
// PROPS
// =========================================================

type ConfirmationStepProps = {
  preview: string | null;

  productName: string;

  category: string;

  mode: GenerationMode | null;

  selectionLabel: string;

  selectionName: string | null;

  isGenerating: boolean;

  error: string | null;

  onBack: () => void;

  onGenerate: () => void;
};


// =========================================================
// LABELS DE CATEGORIA
// =========================================================

const categoryLabels:
  Record<string, string> = {
    EARRING: "Brinco",
    NECKLACE: "Colar",
    RING: "Anel",
    BRACELET: "Pulseira",
    ANKLET: "Tornozeleira",
  };


// =========================================================
// LABELS DOS MODOS
// =========================================================

const modeLabels:
  Record<GenerationMode, string> = {
    STILL:
      "Still",

    BODY_DETAIL:
      "Detalhe no Corpo",

    MODEL:
      "Na Modelo",

    INSTAGRAM:
      "Instagramável",
  };


// =========================================================
// COMPONENTE
// =========================================================

export function ConfirmationStep({
  preview,
  productName,
  category,
  mode,
  selectionLabel,
  selectionName,
  isGenerating,
  error,
  onBack,
  onGenerate,
}: ConfirmationStepProps) {

  // =======================================================
  // CARTEIRA REAL
  // =======================================================

  const {
    availableCredits,
    loading:
      loadingCredits,
    error:
      creditsError,
    refreshWallet,
  } =
    useCreditWallet();


  // =======================================================
  // SALDO
  // =======================================================

  const hasEnoughCredits =
    availableCredits !== null &&
    availableCredits >= 1;


  const canGenerate =
    !isGenerating &&
    !loadingCredits &&
    hasEnoughCredits;


  return (
    <motion.section
      initial={{
        opacity: 0,
        x: 18,
      }}

      animate={{
        opacity: 1,
        x: 0,
      }}

      exit={{
        opacity: 0,
        x: -18,
      }}

      transition={{
        duration: 0.28,
      }}
    >

      {/* ===================================================
          VOLTAR
      =================================================== */}

      <button
        type="button"

        onClick={
          onBack
        }

        disabled={
          isGenerating
        }

        className="mb-6 flex items-center gap-2 text-sm text-[var(--maried-cocoa)] transition-opacity disabled:cursor-not-allowed disabled:opacity-50"
      >

        <ArrowLeft
          size={
            17
          }
        />

        Voltar

      </button>


      {/* ===================================================
          CABEÇALHO
      =================================================== */}

      <h1 className="text-[30px] font-semibold leading-tight tracking-[-0.035em] text-[var(--maried-espresso)] sm:text-[38px]">
        Confira sua criação.
      </h1>


      <p className="mt-3 max-w-xl text-sm leading-6 text-[var(--maried-cocoa)]">
        Revise as informações
        antes de gerar sua imagem.
      </p>


      {/* ===================================================
          CONTEÚDO
      =================================================== */}

      <div className="mt-8 grid gap-5 lg:grid-cols-[0.85fr_1.15fr]">

        {/* =================================================
            PREVIEW DA PEÇA
        ================================================= */}

        <div className="maried-card overflow-hidden p-4">

          <div className="relative aspect-square overflow-hidden rounded-[16px] bg-[var(--maried-cream)]">

            {preview ? (

              <Image
                src={
                  preview
                }

                alt="Peça selecionada"

                fill

                unoptimized

                className="object-contain p-4"
              />

            ) : (

              <div className="flex h-full items-center justify-center">

                <Gem
                  size={
                    42
                  }

                  strokeWidth={
                    1.2
                  }

                  className="text-[var(--maried-gold)]"
                />

              </div>

            )}

          </div>


          {/* INFORMAÇÕES */}

          <div className="px-1 pb-1 pt-4">

            <div className="text-sm font-semibold text-[var(--maried-espresso)]">
              {productName ||
                "Sua peça"}
            </div>


            <div className="mt-1 text-xs text-[var(--maried-cocoa)]">
              {categoryLabels[
                category
              ] || category}
            </div>

          </div>

        </div>


        {/* =================================================
            RESUMO
        ================================================= */}

        <div className="space-y-4">

          {/* ===============================================
              RESULTADO + ESTILO
          =============================================== */}

          <div className="maried-card p-5">

            <div className="grid gap-5 sm:grid-cols-2">

              {/* RESULTADO */}

              <div>

                <div className="text-[11px] uppercase tracking-[0.12em] text-[var(--maried-caramel)]">
                  Resultado
                </div>


                <div className="mt-2 text-sm font-semibold text-[var(--maried-espresso)]">
                  {mode
                    ? modeLabels[
                        mode
                      ]
                    : "-"}
                </div>

              </div>


              {/* SELEÇÃO VISUAL */}

              <div>

                <div className="text-[11px] uppercase tracking-[0.12em] text-[var(--maried-caramel)]">
                  {
                    mode ===
                    "STILL"
                      ? "Seleção"
                      : selectionLabel
                  }
                </div>


                <div className="mt-2 text-sm font-semibold text-[var(--maried-espresso)]">

                  {mode ===
                  "STILL"
                    ? "Não se aplica"
                    : selectionName ??
                      "-"}

                </div>

              </div>

            </div>

          </div>


          {/* ===============================================
              CRÉDITOS
          =============================================== */}

          <div className="maried-card p-5">

            <div className="flex items-center justify-between gap-5">

              {/* CUSTO */}

              <div>

                <div className="text-xs text-[var(--maried-cocoa)]">
                  Custo da criação
                </div>


                <div className="mt-2 flex items-center gap-2 text-lg font-semibold text-[var(--maried-espresso)]">

                  <Sparkles
                    size={
                      18
                    }

                    className="text-[var(--maried-gold)]"
                  />

                  1 crédito

                </div>

              </div>


              {/* SALDO REAL */}

              <div className="text-right">

                <div className="text-xs text-[var(--maried-cocoa)]">
                  Saldo disponível
                </div>


                {loadingCredits ? (

                  <div className="mt-2 flex justify-end">

                    <LoaderCircle
                      size={
                        24
                      }

                      className="animate-spin text-[var(--maried-gold)]"
                    />

                  </div>

                ) : (

                  <div className="mt-2 text-2xl font-semibold text-[var(--maried-espresso)]">

                    {
                      availableCredits ??
                      0
                    }

                  </div>

                )}

              </div>

            </div>


            {/* ERRO DA CARTEIRA */}

            {creditsError ? (

              <div className="mt-4 flex items-center justify-between gap-3 rounded-xl bg-amber-50 px-3 py-2 text-xs text-amber-800">

                <span>
                  Não foi possível atualizar
                  o saldo agora.
                </span>


                <button
                  type="button"

                  onClick={() => {
                    void refreshWallet();
                  }}

                  className="shrink-0 font-semibold underline"
                >
                  Tentar novamente
                </button>

              </div>

            ) : null}


            {/* SEM CRÉDITOS */}

            {!loadingCredits &&
            availableCredits !== null &&
            availableCredits < 1 ? (

              <div className="mt-4 rounded-xl border border-amber-200 bg-amber-50 px-3 py-3 text-xs leading-5 text-amber-800">

                Você não possui créditos
                disponíveis para gerar
                esta imagem.

              </div>

            ) : null}

          </div>


          {/* ===============================================
              ERRO DA GERAÇÃO
          =============================================== */}

          {error ? (

            <motion.div
              initial={{
                opacity: 0,
                y: -4,
              }}

              animate={{
                opacity: 1,
                y: 0,
              }}

              className="rounded-xl border border-red-200 bg-red-50 p-3 text-center text-xs leading-5 text-red-700"
            >

              {error}

            </motion.div>

          ) : null}


          {/* ===============================================
              BOTÃO GERAR
          =============================================== */}

          <motion.button
            type="button"

            whileHover={
              canGenerate
                ? {
                    y: -1,
                  }
                : undefined
            }

            whileTap={
              canGenerate
                ? {
                    scale:
                      0.985,
                  }
                : undefined
            }

            disabled={
              !canGenerate
            }

            onClick={
              onGenerate
            }

            className={[
              "flex h-[56px] w-full items-center justify-center gap-2 rounded-xl px-6 text-sm font-semibold transition-all",

              canGenerate
                ? "bg-[var(--maried-gold)] text-white shadow-[0_14px_32px_rgba(163,141,92,0.24)]"
                : "cursor-not-allowed bg-[var(--maried-sand)] text-[var(--maried-caramel)]",
            ].join(
              " "
            )}
          >

            {isGenerating ? (

              <>
                <motion.span
                  animate={{
                    rotate:
                      360,
                  }}

                  transition={{
                    duration:
                      0.8,

                    ease:
                      "linear",

                    repeat:
                      Infinity,
                  }}

                  className="h-4 w-4 rounded-full border-2 border-white/40 border-t-white"
                />


                <span>
                  Gerando sua imagem...
                </span>
              </>

            ) : loadingCredits ? (

              <>
                <LoaderCircle
                  size={
                    17
                  }

                  className="animate-spin"
                />

                Verificando créditos...
              </>

            ) : !hasEnoughCredits ? (

              <>
                <Sparkles
                  size={
                    18
                  }
                />

                Sem créditos disponíveis
              </>

            ) : (

              <>
                <Sparkles
                  size={
                    18
                  }
                />


                <span>
                  Gerar imagem
                </span>


                <span className="font-normal opacity-80">
                  • 1 crédito
                </span>
              </>

            )}

          </motion.button>


          {/* ===============================================
              TEXTO INFORMATIVO
          =============================================== */}

          <p className="text-center text-[10px] leading-4 text-[var(--maried-caramel)]">

            {isGenerating
              ? "Sua criação está sendo processada."
              : "O crédito será consumido somente se a geração for concluída."}

          </p>

        </div>

      </div>

    </motion.section>
  );
}

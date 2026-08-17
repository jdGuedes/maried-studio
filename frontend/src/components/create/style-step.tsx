"use client";

import {
  Check,
  LoaderCircle,
} from "lucide-react";

import {
  motion,
} from "motion/react";

import type {
  SceneTemplate,
} from "@/types/api";

type StyleStepProps = {
  templates: SceneTemplate[];
  selectedTemplateId: string | null;

  loading: boolean;
  error: string | null;

  onChange: (
    templateId: string
  ) => void;

  onBack: () => void;
  onContinue: () => void;
};

export function StyleStep({
  templates,
  selectedTemplateId,
  loading,
  error,
  onChange,
  onBack,
  onContinue,
}: StyleStepProps) {
  const canContinue =
    Boolean(
      selectedTemplateId
    );

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
      {/* CABEÇALHO */}
      <div>
        <h1 className="text-[30px] font-semibold leading-tight tracking-[-0.035em] text-[var(--maried-espresso)] sm:text-[38px]">
          Escolha o estilo
          da sua imagem.
        </h1>

        <p className="mt-3 max-w-xl text-sm leading-6 text-[var(--maried-cocoa)]">
          Selecione a direção
          visual que deseja
          aplicar à fotografia.
        </p>
      </div>

      {/* ================================================
          CARREGAMENTO
      ================================================ */}
      {loading ? (
        <div className="maried-card mt-8 flex min-h-[250px] flex-col items-center justify-center p-8 text-center">
          <motion.div
            animate={{
              rotate: 360,
            }}
            transition={{
              duration: 1,
              ease: "linear",
              repeat: Infinity,
            }}
          >
            <LoaderCircle
              size={30}
              strokeWidth={1.5}
              className="text-[var(--maried-gold)]"
            />
          </motion.div>

          <h2 className="mt-5 text-sm font-semibold">
            Carregando estilos
          </h2>

          <p className="mt-2 text-xs text-[var(--maried-cocoa)]">
            Buscando as opções
            disponíveis para
            esta peça.
          </p>
        </div>
      ) : null}

      {/* ================================================
          ERRO
      ================================================ */}
      {!loading && error ? (
        <div className="mt-8 rounded-[18px] border border-[var(--status-critical)]/20 bg-white p-6">
          <div className="text-sm font-semibold text-[var(--status-critical)]">
            Não foi possível
            carregar os estilos.
          </div>

          <p className="mt-2 text-xs leading-5 text-[var(--maried-cocoa)]">
            {error}
          </p>
        </div>
      ) : null}

      {/* ================================================
          SEM TEMPLATES
      ================================================ */}
      {!loading &&
      !error &&
      templates.length === 0 ? (
        <div className="maried-card mt-8 p-6">
          <h2 className="text-sm font-semibold">
            Nenhum estilo disponível
          </h2>

          <p className="mt-2 text-xs leading-5 text-[var(--maried-cocoa)]">
            Não existem templates
            ativos para esta categoria
            e modo no momento.
          </p>
        </div>
      ) : null}

      {/* ================================================
          TEMPLATES REAIS DO BACKEND
      ================================================ */}
      {!loading &&
      !error &&
      templates.length > 0 ? (
        <div className="mt-8 grid gap-3 sm:grid-cols-2">
          {templates.map(
            (
              template
            ) => {
              const selected =
                selectedTemplateId ===
                template.id;

              return (
                <motion.button
                  key={
                    template.id
                  }
                  type="button"
                  whileTap={{
                    scale:
                      0.985,
                  }}
                  onClick={() => {
                    onChange(
                      template.id
                    );
                  }}
                  className={[
                    "relative min-h-[160px] rounded-[18px] border p-5 text-left transition-all",
                    selected
                      ? "border-[var(--maried-gold)] bg-[var(--maried-soft-gold)] shadow-[0_12px_30px_rgba(163,141,92,0.10)]"
                      : "border-[var(--maried-sand)] bg-white hover:border-[var(--maried-champagne)]",
                  ].join(
                    " "
                  )}
                >
                  {selected ? (
                    <div className="absolute right-4 top-4 flex h-6 w-6 items-center justify-center rounded-full bg-[var(--maried-gold)] text-white">
                      <Check
                        size={
                          13
                        }
                      />
                    </div>
                  ) : null}

                  <div className="text-[10px] font-medium uppercase tracking-[0.15em] text-[var(--maried-gold)]">
                    MARIED STUDIO
                  </div>

                  <h2 className="mt-4 text-lg font-semibold text-[var(--maried-espresso)]">
                    {
                      template.name
                    }
                  </h2>

                  <p className="mt-2 text-xs leading-5 text-[var(--maried-cocoa)]">
                    Estilo{" "}
                    {
                      template.name
                    }{" "}
                    para esta
                    composição.
                  </p>
                </motion.button>
              );
            }
          )}
        </div>
      ) : null}

      {/* BOTÕES */}
      <div className="mt-8 flex flex-col-reverse gap-3 sm:flex-row sm:justify-between">
        <button
          type="button"
          onClick={
            onBack
          }
          className="h-12 rounded-xl border border-[var(--maried-sand)] bg-white px-5 text-sm font-medium text-[var(--maried-cocoa)] transition hover:border-[var(--maried-champagne)]"
        >
          Voltar
        </button>

        <motion.button
          type="button"
          whileTap={
            canContinue
              ? {
                  scale:
                    0.985,
                }
              : undefined
          }
          disabled={
            !canContinue ||
            loading
          }
          onClick={
            onContinue
          }
          className={[
            "h-12 rounded-xl px-6 text-sm font-medium transition",
            canContinue &&
            !loading
              ? "bg-[var(--maried-gold)] text-white shadow-[0_12px_28px_rgba(163,141,92,0.22)]"
              : "cursor-not-allowed bg-[var(--maried-sand)] text-[var(--maried-caramel)]",
          ].join(
            " "
          )}
        >
          Continuar
        </motion.button>
      </div>
    </motion.section>
  );
}
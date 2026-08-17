"use client";

import {
  Camera,
  Image as ImageIcon,
  ScanFace,
  Sparkles,
} from "lucide-react";

import { motion } from "motion/react";

export type GenerationMode =
  | "STILL"
  | "BODY_DETAIL"
  | "MODEL"
  | "INSTAGRAM";

type ResultModeStepProps = {
  value: GenerationMode | null;
  onChange: (mode: GenerationMode) => void;
  onBack: () => void;
  onContinue: () => void;
};

const modes = [
  {
    value: "STILL" as const,
    title: "Still",
    description:
      "Foto de catálogo com fundo branco e foco total na peça.",
    icon: ImageIcon,
  },
  {
    value: "BODY_DETAIL" as const,
    title: "Detalhe no Corpo",
    description:
      "Aplicação realista da joia na região correta do corpo.",
    icon: ScanFace,
  },
  {
    value: "MODEL" as const,
    title: "Na Modelo",
    description:
      "Fotografia profissional com modelo usando a sua peça.",
    icon: Sparkles,
  },
  {
    value: "INSTAGRAM" as const,
    title: "Instagramável",
    description:
      "Composição comercial e lifestyle para redes sociais.",
    icon: Camera,
  },
];

export function ResultModeStep({
  value,
  onChange,
  onBack,
  onContinue,
}: ResultModeStepProps) {
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
      <div>
        <h1 className="text-[30px] font-semibold leading-tight tracking-[-0.035em] text-[var(--maried-espresso)] sm:text-[38px]">
          Como você quer apresentar sua peça?
        </h1>

        <p className="mt-3 max-w-xl text-sm leading-6 text-[var(--maried-cocoa)]">
          Escolha o tipo de imagem que deseja criar.
        </p>
      </div>

      <div className="mt-8 grid gap-3 sm:grid-cols-2">
        {modes.map((mode) => {
          const Icon = mode.icon;

          const selected =
            value === mode.value;

          return (
            <motion.button
              key={mode.value}
              type="button"
              whileTap={{
                scale: 0.985,
              }}
              onClick={() => {
                onChange(mode.value);
              }}
              className={[
                "group relative min-h-[190px] rounded-[18px] border p-5 text-left transition-all",
                selected
                  ? "border-[var(--maried-gold)] bg-[var(--maried-soft-gold)] shadow-[0_12px_30px_rgba(163,141,92,0.10)]"
                  : "border-[var(--maried-sand)] bg-white hover:border-[var(--maried-champagne)]",
              ].join(" ")}
            >
              <div
                className={[
                  "flex h-11 w-11 items-center justify-center rounded-xl transition-colors",
                  selected
                    ? "bg-[var(--maried-gold)] text-white"
                    : "bg-[var(--maried-cream)] text-[var(--maried-gold)]",
                ].join(" ")}
              >
                <Icon
                  size={21}
                  strokeWidth={1.5}
                />
              </div>

              <h2 className="mt-5 text-base font-semibold text-[var(--maried-espresso)]">
                {mode.title}
              </h2>

              <p className="mt-2 max-w-[280px] text-xs leading-5 text-[var(--maried-cocoa)]">
                {mode.description}
              </p>

              {selected ? (
                <div className="absolute right-4 top-4 h-2.5 w-2.5 rounded-full bg-[var(--maried-gold)]" />
              ) : null}
            </motion.button>
          );
        })}
      </div>

      <div className="mt-8 flex flex-col-reverse gap-3 sm:flex-row sm:justify-between">
        <button
          type="button"
          onClick={onBack}
          className="h-12 rounded-xl border border-[var(--maried-sand)] bg-white px-5 text-sm font-medium text-[var(--maried-cocoa)] transition hover:border-[var(--maried-champagne)]"
        >
          Voltar
        </button>

        <motion.button
          type="button"
          whileTap={
            value
              ? {
                  scale: 0.985,
                }
              : undefined
          }
          disabled={!value}
          onClick={onContinue}
          className={[
            "h-12 rounded-xl px-6 text-sm font-medium transition",
            value
              ? "bg-[var(--maried-gold)] text-white shadow-[0_12px_28px_rgba(163,141,92,0.22)]"
              : "cursor-not-allowed bg-[var(--maried-sand)] text-[var(--maried-caramel)]",
          ].join(" ")}
        >
          Continuar
        </motion.button>
      </div>
    </motion.section>
  );
}

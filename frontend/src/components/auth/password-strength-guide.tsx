"use client";

import {
  CheckCircle2,
  Circle,
} from "lucide-react";


type PasswordLevel =
  | "empty"
  | "very-weak"
  | "weak"
  | "fair"
  | "good"
  | "strong";


type PasswordCheck = {
  label: string;
  met: boolean;
  required: boolean;
};


type PasswordStrength = {
  level: PasswordLevel;
  label: string;
  checks: PasswordCheck[];
};


const LEVEL_CLASSES:
  Record<PasswordLevel, string> = {
    empty:
      "bg-[var(--maried-sand)]",
    "very-weak":
      "bg-red-400",
    weak:
      "bg-orange-400",
    fair:
      "bg-amber-400",
    good:
      "bg-[var(--maried-gold)]",
    strong:
      "bg-emerald-500",
  };


function hasSimpleSequence(
  password: string
) {
  const normalized =
    password.toLowerCase();

  return [
    "1234",
    "2345",
    "3456",
    "4567",
    "5678",
    "6789",
    "abcd",
    "bcde",
    "cdef",
    "qwer",
    "asdf",
  ].some(
    (sequence) =>
      normalized.includes(
        sequence
      )
  );
}


function hasObviousRepetition(
  password: string
) {
  return /(.)\1{2,}/.test(
    password
  );
}


export function evaluatePasswordStrength(
  password: string
): PasswordStrength {
  const hasStarted =
    password.length > 0;

  const checks: PasswordCheck[] = [
    {
      label:
        "Comprimento mínimo exigido",
      met:
        password.length >= 8,
      required:
        true,
    },
    {
      label:
        "Letras maiúsculas e minúsculas",
      met:
        /[a-z]/.test(password) &&
        /[A-Z]/.test(password),
      required:
        false,
    },
    {
      label:
        "Número",
      met:
        /\d/.test(password),
      required:
        false,
    },
    {
      label:
        "Caractere especial",
      met:
        /[^A-Za-z0-9]/.test(password),
      required:
        false,
    },
    {
      label:
        "Evite sequências e repetições previsíveis",
      met:
        hasStarted &&
        !hasSimpleSequence(password) &&
        !hasObviousRepetition(password) &&
        !/^\d+$/.test(password),
      required:
        false,
    },
  ];

  if (!hasStarted) {
    return {
      level:
        "empty",
      label:
        "Digite uma senha para ver a orientação.",
      checks,
    };
  }

  let score = 0;

  for (const check of checks) {
    if (check.met) {
      score += check.required
        ? 2
        : 1;
    }
  }

  if (
    password.length >= 12
  ) {
    score += 1;
  }

  if (
    password.length < 8 ||
    /^\d+$/.test(password)
  ) {
    return {
      level:
        "very-weak",
      label:
        "Muito fraca",
      checks,
    };
  }

  if (score <= 3) {
    return {
      level:
        "weak",
      label:
        "Fraca",
      checks,
    };
  }

  if (score <= 4) {
    return {
      level:
        "fair",
      label:
        "Razoável",
      checks,
    };
  }

  if (score <= 6) {
    return {
      level:
        "good",
      label:
        "Boa",
      checks,
    };
  }

  return {
    level:
      "strong",
    label:
      "Forte",
    checks,
  };
}


type PasswordStrengthGuideProps = {
  password: string;
};


export function PasswordStrengthGuide({
  password,
}: PasswordStrengthGuideProps) {
  const strength =
    evaluatePasswordStrength(
      password
    );

  const activeSegments =
    {
      empty: 0,
      "very-weak": 1,
      weak: 2,
      fair: 3,
      good: 4,
      strong: 5,
    }[strength.level];

  return (
    <div className="rounded-xl border border-[var(--maried-sand)] bg-[var(--maried-cream)] px-4 py-3">
      <div className="flex items-center justify-between gap-3">
        <div className="text-xs font-medium text-[var(--maried-coffee)]">
          Força da senha
        </div>

        <div
          aria-live="polite"
          className="text-xs font-medium text-[var(--maried-espresso)]"
        >
          {strength.label}
        </div>
      </div>

      <div className="mt-3 grid grid-cols-5 gap-1">
        {[0, 1, 2, 3, 4].map(
          (index) => (
            <div
              key={index}
              className={[
                "h-1.5 rounded-full",
                index < activeSegments
                  ? LEVEL_CLASSES[
                      strength.level
                    ]
                  : "bg-white",
              ].join(" ")}
            />
          )
        )}
      </div>

      <div className="mt-3 space-y-2">
        {strength.checks.map(
          (check) => (
            <div
              key={check.label}
              className="flex items-start gap-2 text-xs text-[var(--maried-cocoa)]"
            >
              {check.met ? (
                <CheckCircle2
                  size={14}
                  className="mt-0.5 shrink-0 text-emerald-600"
                />
              ) : (
                <Circle
                  size={14}
                  className="mt-0.5 shrink-0 text-[var(--maried-caramel)]"
                />
              )}

              <span>
                {check.label}
                {check.required
                  ? ""
                  : " (recomendação)"}
              </span>
            </div>
          )
        )}
      </div>

      <p className="mt-3 text-xs leading-5 text-[var(--maried-cocoa)]">
        Prefira uma frase longa e exclusiva. O Django ainda valida regras como senha comum ou parecida com seus dados.
      </p>
    </div>
  );
}

"use client";

import {
  ChevronLeft,
  ChevronRight,
} from "lucide-react";


type PaginationProps = {
  page: number;
  totalPages: number;
  loading?: boolean;
  onPageChange: (page: number) => void;
};


type PageItem =
  | number
  | "left"
  | "right";


function getPageItems(
  page: number,
  totalPages: number
): PageItem[] {
  if (totalPages <= 7) {
    return Array.from(
      {
        length:
          totalPages,
      },
      (
        _,
        index
      ) => index + 1
    );
  }

  const items: PageItem[] = [
    1,
  ];

  const start = Math.max(
    2,
    page - 1
  );

  const end = Math.min(
    totalPages - 1,
    page + 1
  );

  if (start > 2) {
    items.push(
      "left"
    );
  }

  for (
    let current = start;
    current <= end;
    current += 1
  ) {
    items.push(
      current
    );
  }

  if (end < totalPages - 1) {
    items.push(
      "right"
    );
  }

  items.push(
    totalPages
  );

  return items;
}


export function Pagination({
  page,
  totalPages,
  loading = false,
  onPageChange,
}: PaginationProps) {
  if (totalPages <= 1) {
    return null;
  }

  const items = getPageItems(
    page,
    totalPages
  );

  return (
    <nav
      aria-label="Paginação"
      className="mt-7 flex items-center justify-center gap-1.5"
    >
      <button
        type="button"
        aria-label="Página anterior"
        disabled={
          loading ||
          page <= 1
        }
        onClick={() => {
          onPageChange(
            page - 1
          );
        }}
        className="flex h-9 w-9 items-center justify-center rounded-xl border border-[var(--maried-sand)] bg-white text-[var(--maried-coffee)] disabled:cursor-not-allowed disabled:opacity-45"
      >
        <ChevronLeft
          size={16}
        />
      </button>

      {items.map(
        (
          item,
          index
        ) => {
          if (
            item === "left" ||
            item === "right"
          ) {
            return (
              <span
                key={`${item}-${index}`}
                className="flex h-9 w-9 items-center justify-center text-xs text-[var(--maried-caramel)]"
              >
                ...
              </span>
            );
          }

          const selected =
            item === page;

          return (
            <button
              key={item}
              type="button"
              aria-current={
                selected
                  ? "page"
                  : undefined
              }
              disabled={
                loading ||
                selected
              }
              onClick={() => {
                onPageChange(
                  item
                );
              }}
              className={[
                "flex h-9 min-w-9 items-center justify-center rounded-xl px-3 text-xs font-medium",
                selected
                  ? "bg-[var(--maried-gold)] text-white"
                  : "border border-[var(--maried-sand)] bg-white text-[var(--maried-coffee)] hover:bg-[var(--maried-cream)]",
              ].join(
                " "
              )}
            >
              {item}
            </button>
          );
        }
      )}

      <button
        type="button"
        aria-label="Próxima página"
        disabled={
          loading ||
          page >= totalPages
        }
        onClick={() => {
          onPageChange(
            page + 1
          );
        }}
        className="flex h-9 w-9 items-center justify-center rounded-xl border border-[var(--maried-sand)] bg-white text-[var(--maried-coffee)] disabled:cursor-not-allowed disabled:opacity-45"
      >
        <ChevronRight
          size={16}
        />
      </button>
    </nav>
  );
}

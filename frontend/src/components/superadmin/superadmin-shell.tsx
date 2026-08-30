"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import {
  Activity,
  BarChart3,
  ClipboardList,
  CreditCard,
  Gem,
  Layers3,
  LoaderCircle,
  ReceiptText,
  ShieldCheck,
  Users,
} from "lucide-react";

import type { ReactNode } from "react";

import { AppShell } from "@/components/layout/app-shell";
import { useProfile } from "@/providers/profile-provider";


type SuperAdminShellProps = {
  title: string;
  subtitle?: string;
  children: ReactNode;
};


const superAdminNav = [
  {
    label: "Dashboard",
    href: "/superadmin",
    icon: BarChart3,
  },
  {
    label: "Clientes",
    href: "/superadmin/clientes",
    icon: Users,
  },
  {
    label: "Assinaturas",
    href: "/superadmin/assinaturas",
    icon: ReceiptText,
  },
  {
    label: "Planos",
    href: "/superadmin/planos",
    icon: ClipboardList,
  },
  {
    label: "Créditos",
    href: "/superadmin/creditos",
    icon: CreditCard,
  },
  {
    label: "Gerações",
    href: "/superadmin/geracoes",
    icon: Gem,
  },
  {
    label: "Studio",
    href: "/superadmin/studio",
    icon: Layers3,
  },
  {
    label: "Auditoria",
    href: "/superadmin/auditoria",
    icon: Activity,
  },
];


function isActive(
  pathname: string,
  href: string
) {
  if (href === "/superadmin") {
    return pathname === href;
  }

  return (
    pathname === href ||
    pathname.startsWith(`${href}/`)
  );
}


export function SuperAdminShell({
  title,
  subtitle,
  children,
}: SuperAdminShellProps) {
  const pathname =
    usePathname();

  const {
    loading,
    isSuperAdmin,
  } = useProfile();

  return (
    <AppShell>
      <main className="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8">
        <header className="mb-5">
          <div className="flex items-center gap-2 text-xs font-semibold uppercase text-[var(--maried-gold)]">
            <ShieldCheck size={16} />
            SUPERADMIN
          </div>
          <div className="mt-2 flex flex-col gap-2 lg:flex-row lg:items-end lg:justify-between">
            <div>
              <h1 className="text-2xl font-semibold text-[var(--maried-espresso)]">
                {title}
              </h1>
              {subtitle ? (
                <p className="mt-1 text-sm text-[var(--maried-cocoa)]">
                  {subtitle}
                </p>
              ) : null}
            </div>
            <Link
              href="/"
              className="text-sm font-medium text-[var(--maried-gold)]"
            >
              Voltar ao Studio
            </Link>
          </div>
        </header>

        <nav className="mb-6 overflow-x-auto rounded-2xl border border-[var(--maried-sand)] bg-white p-2">
          <div className="flex min-w-max gap-1">
            {superAdminNav.map((item) => {
              const Icon = item.icon;
              const active =
                isActive(
                  pathname,
                  item.href
                );

              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={[
                    "inline-flex h-10 items-center gap-2 rounded-xl px-3 text-sm transition-colors",
                    active
                      ? "bg-[var(--maried-soft-gold)] text-[var(--maried-coffee)]"
                      : "text-[var(--maried-cocoa)] hover:bg-[var(--maried-ivory)]",
                  ].join(" ")}
                >
                  <Icon size={16} />
                  {item.label}
                </Link>
              );
            })}
          </div>
        </nav>

        {loading ? (
          <div className="flex items-center gap-2 rounded-2xl border border-[var(--maried-sand)] bg-white p-5 text-sm text-[var(--maried-cocoa)]">
            <LoaderCircle className="animate-spin text-[var(--maried-gold)]" size={17} />
            Carregando sessão...
          </div>
        ) : isSuperAdmin ? (
          children
        ) : (
          <section className="rounded-2xl border border-red-100 bg-red-50 p-5 text-sm text-red-700">
            Acesso restrito ao SuperAdmin.
          </section>
        )}
      </main>
    </AppShell>
  );
}


export function AdminCard({
  children,
  className = "",
}: {
  children: ReactNode;
  className?: string;
}) {
  return (
    <section className={`rounded-2xl border border-[var(--maried-sand)] bg-white p-5 ${className}`}>
      {children}
    </section>
  );
}


export function MetricCard({
  label,
  value,
}: {
  label: string;
  value: string | number;
}) {
  return (
    <div className="rounded-xl border border-[var(--maried-sand)] bg-[var(--maried-ivory)] px-4 py-3">
      <div className="text-xs text-[var(--maried-cocoa)]">
        {label}
      </div>
      <div className="mt-1 text-xl font-semibold text-[var(--maried-espresso)]">
        {value}
      </div>
    </div>
  );
}


export function StatusMessage({
  text,
  tone = "error",
}: {
  text: string;
  tone?: "error" | "success";
}) {
  return (
    <div
      className={[
        "rounded-2xl border px-4 py-3 text-sm",
        tone === "error"
          ? "border-red-100 bg-red-50 text-red-700"
          : "border-emerald-100 bg-emerald-50 text-emerald-700",
      ].join(" ")}
    >
      {text}
    </div>
  );
}


export function EmptyState({
  children,
}: {
  children: ReactNode;
}) {
  return (
    <div className="rounded-xl border border-dashed border-[var(--maried-sand)] bg-[var(--maried-ivory)] p-5 text-sm text-[var(--maried-cocoa)]">
      {children}
    </div>
  );
}

"use client";

import Link from "next/link";
import {
  usePathname,
} from "next/navigation";

import {
  CreditCard,
  Gem,
  Home,
  Images,
  LoaderCircle,
  LogOut,
  Plus,
  ShieldCheck,
  Sparkles,
  UserRound,
} from "lucide-react";

import {
  motion,
} from "motion/react";

import type {
  ReactNode,
} from "react";

import {
  useCreditWallet,
} from "@/providers/credit-wallet-provider";

import {
  useBillingAccess,
} from "@/providers/billing-access-provider";

import {
  useProfile,
} from "@/providers/profile-provider";

import {
  useLogout,
} from "@/lib/logout";


type AppShellProps = {
  children: ReactNode;
};


// ==========================================================
// MENU DESKTOP
// ==========================================================

const navItems = [
  {
    label: "Início",
    icon: Home,
    href: "/",
  },

  {
    label: "Criar imagem",
    icon: Sparkles,
    href: "/criar",
  },

  {
    label: "Minhas criações",
    icon: Images,
    href: "/criacoes",
  },

  {
    label: "Minhas peças",
    icon: Gem,
    href: "/pecas",
  },

  {
    label: "Créditos",
    icon: CreditCard,
    href: "/creditos",
  },

  {
    label: "Assinatura",
    icon: CreditCard,
    href: "/assinatura",
  },
];


// ==========================================================
// AUXILIAR DE ROTA ATIVA
// ==========================================================

function isRouteActive(
  pathname: string,
  href: string
) {
  if (
    href === "/"
  ) {
    return pathname === "/";
  }

  if (
    href === "#"
  ) {
    return false;
  }

  return (
    pathname === href ||
    pathname.startsWith(
      `${href}/`
    )
  );
}


// ==========================================================
// APP SHELL
// ==========================================================

export function AppShell({
  children,
}: AppShellProps) {

  const pathname =
    usePathname();


  // ========================================================
  // PERFIL REAL
  // ========================================================

  const {
    profile,

    loading:
      loadingProfile,

    error:
      profileError,

    refreshProfile,

    organizationName,

    initials,

    isSuperAdmin,
  } =
    useProfile();


  const {
    loggingOut,
    logoutError,
    performLogout,
  } =
    useLogout();


  const {
    canOperateStudio,
  } =
    useBillingAccess();


  // ========================================================
  // CARTEIRA REAL
  // ========================================================

  const {
    availableCredits,

    loading:
      loadingCredits,

    error:
      creditsError,

    refreshWallet,
  } =
    useCreditWallet();


  // ========================================================
  // LABEL DO SALDO
  // ========================================================

  const creditsLabel =
    loadingCredits
      ? "..."
      : String(
          availableCredits ??
          0
        );


  // ========================================================
  // LABEL DO PERFIL
  // ========================================================

  const profileRoleLabel =
    loadingProfile
      ? "Carregando..."
      : profile?.role_label ??
        "Usuário";


  if (
    loadingProfile
  ) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-[var(--maried-ivory)] px-6">
        <div className="flex items-center gap-3 text-sm text-[var(--maried-cocoa)]">
          <LoaderCircle
            size={
              18
            }
            className="animate-spin text-[var(--maried-gold)]"
          />
          Carregando sessão...
        </div>
      </main>
    );
  }


  if (
    !profile
  ) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-[var(--maried-ivory)] px-6">
        <div className="text-sm text-[var(--maried-cocoa)]">
          Redirecionando para login...
        </div>
      </main>
    );
  }


  return (
    <div className="min-h-screen bg-[var(--maried-ivory)]">

      <div className="mx-auto flex min-h-screen max-w-[1600px]">

        {/* =====================================================
            SIDEBAR DESKTOP
        ===================================================== */}

        <aside className="fixed left-0 top-0 z-40 hidden h-screen w-[250px] border-r border-[var(--maried-sand)] bg-[rgba(255,255,255,0.72)] px-5 py-7 backdrop-blur-xl lg:flex lg:flex-col">

          {/* LOGO */}

          <Link
            href="/"
            className="block px-3"
          >

            <div className="text-[30px] font-light tracking-[0.12em] text-[var(--maried-gold)]">
              MARIED
            </div>

            <div className="mt-1 text-[11px] tracking-[0.45em] text-[var(--maried-coffee)]">
              STUDIO
            </div>

          </Link>


          {/* MENU */}

          <nav className="mt-12 flex flex-col gap-2">

            {(canOperateStudio
              ? navItems
              : navItems.filter(
                  (
                    item
                  ) =>
                    item.href !== "/criar"
                )).map(
              (
                item
              ) => {

                const Icon =
                  item.icon;


                const active =
                  isRouteActive(
                    pathname,
                    item.href
                  );


                if (
                  item.href === "#"
                ) {

                  return (
                    <button
                      key={
                        item.label
                      }

                      type="button"

                      className="flex h-11 items-center gap-3 rounded-xl px-3 text-left text-sm text-[var(--maried-cocoa)] transition-colors hover:bg-[rgba(237,227,200,0.55)]"
                    >

                      <Icon
                        size={
                          18
                        }

                        strokeWidth={
                          1.7
                        }
                      />

                      <span>
                        {
                          item.label
                        }
                      </span>

                    </button>
                  );

                }


                return (
                  <Link
                    key={
                      item.label
                    }

                    href={
                      item.href
                    }

                    className={[
                      "flex h-11 items-center gap-3 rounded-xl px-3 text-left text-sm transition-colors",

                      active
                        ? "bg-[var(--maried-soft-gold)] text-[var(--maried-coffee)]"
                        : "text-[var(--maried-cocoa)] hover:bg-[rgba(237,227,200,0.55)]",
                    ].join(
                      " "
                    )}
                  >

                    <Icon
                      size={
                        18
                      }

                      strokeWidth={
                        1.7
                      }
                    />

                    <span>
                      {
                        item.label
                      }
                    </span>

                  </Link>
                );

              }
            )}

          </nav>


          {/* =================================================
              ÁREA SUPERADMIN
          ================================================= */}

          {isSuperAdmin ? (

            <Link
              href="/superadmin"
              className={[
                "mt-5 block rounded-[14px] border px-3 py-2.5 transition-colors",

                isRouteActive(
                  pathname,
                  "/superadmin"
                )
                  ? "border-[var(--maried-gold)] bg-[var(--maried-soft-gold)]"
                  : "border-[var(--maried-sand)] bg-[var(--maried-soft-gold)] hover:bg-[var(--maried-cream)]",
              ].join(
                " "
              )}
            >

              <div className="flex items-center gap-2">

                <ShieldCheck
                  size={
                    15
                  }

                  strokeWidth={
                    1.8
                  }

                  className="text-[var(--maried-gold)]"
                />


                <div>

                  <div className="text-[10px] font-semibold uppercase tracking-[0.08em] text-[var(--maried-coffee)]">
                    SuperAdmin
                  </div>


                  <div className="mt-0.5 text-[9px] text-[var(--maried-cocoa)]">
                    Administração da plataforma
                  </div>

                </div>

              </div>

            </Link>

          ) : null}


          {/* =================================================
              SALDO DESKTOP
          ================================================= */}

          <div className="mt-5 rounded-[16px] border border-[var(--maried-sand)] bg-white/80 p-4">

            <div className="flex items-center gap-2">

              <Sparkles
                size={
                  16
                }

                className="text-[var(--maried-gold)]"
              />

              <span className="text-[11px] font-medium uppercase tracking-[0.08em] text-[var(--maried-caramel)]">
                Créditos
              </span>

            </div>


            <div className="mt-3 flex items-end justify-between gap-3">

              <div>

                {loadingCredits ? (

                  <LoaderCircle
                    size={
                      22
                    }

                    className="animate-spin text-[var(--maried-gold)]"
                  />

                ) : (

                  <div className="text-3xl font-semibold tracking-[-0.04em] text-[var(--maried-espresso)]">
                    {
                      creditsLabel
                    }
                  </div>

                )}


                <div className="mt-1 text-[10px] text-[var(--maried-cocoa)]">
                  disponíveis
                </div>

              </div>


              {!loadingCredits &&
              creditsError ? (

                <button
                  type="button"

                  onClick={() => {
                    void refreshWallet();
                  }}

                  className="text-[10px] font-medium text-[var(--maried-gold)]"
                >
                  Atualizar
                </button>

              ) : null}

            </div>

          </div>


          {/* =================================================
              PERFIL DESKTOP
          ================================================= */}

          <div className="mt-auto">

            <Link
              href="/perfil"

              className={[
                "maried-card mb-3 block p-3 transition",

                isRouteActive(
                  pathname,
                  "/perfil"
                )
                  ? "border-[var(--maried-gold)]"
                  : "hover:border-[var(--maried-champagne)]",
              ].join(
                " "
              )}
            >

              <div className="flex items-center gap-3">

                {/* AVATAR */}

                <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-[var(--maried-soft-gold)] text-sm font-semibold text-[var(--maried-coffee)]">

                  {loadingProfile
                    ? (
                        <LoaderCircle
                          size={
                            15
                          }

                          className="animate-spin"
                        />
                      )
                    : initials}

                </div>


                {/* DADOS */}

                <div className="min-w-0 flex-1">

                  <div className="truncate text-sm font-medium">
                    {loadingProfile
                      ? "Carregando..."
                      : organizationName}
                  </div>


                  <div className="mt-0.5 flex items-center gap-1.5 text-xs text-[var(--maried-cocoa)]">

                    <span className="truncate">
                      {
                        profileRoleLabel
                      }
                    </span>


                    {isSuperAdmin ? (

                      <ShieldCheck
                        size={
                          12
                        }

                        className="shrink-0 text-[var(--maried-gold)]"
                      />

                    ) : null}

                  </div>

                </div>


                <UserRound
                  size={
                    16
                  }

                  strokeWidth={
                    1.6
                  }

                  className="shrink-0 text-[var(--maried-caramel)]"
                />

              </div>

            </Link>


            {/* ERRO DO PERFIL */}

            {!loadingProfile &&
            profileError ? (

              <button
                type="button"

                onClick={() => {
                  void refreshProfile();
                }}

                className="mb-2 w-full rounded-xl bg-red-50 px-3 py-2 text-left text-[10px] text-red-700"
              >
                Perfil não atualizado. Toque para tentar novamente.
              </button>

            ) : null}


            {logoutError ? (

              <div className="mb-2 rounded-xl bg-red-50 px-3 py-2 text-left text-[10px] text-red-700">
                {logoutError}
              </div>

            ) : null}


            <button
              type="button"

              disabled={
                loggingOut
              }

              onClick={() => {
                void performLogout();
              }}

              className="flex h-11 w-full items-center gap-3 rounded-xl px-3 text-sm text-[var(--maried-cocoa)] transition-colors hover:bg-[var(--maried-cream)]"
            >

              {loggingOut ? (

                <LoaderCircle
                  size={
                    18
                  }

                  className="animate-spin"
                />

              ) : (

                <LogOut
                  size={
                    18
                  }

                  strokeWidth={
                    1.7
                  }
                />

              )}

              {loggingOut
                ? "Saindo..."
                : "Sair"}

            </button>

          </div>

        </aside>


        {/* =====================================================
            CONTEÚDO PRINCIPAL
        ===================================================== */}

        <main className="min-w-0 flex-1 pb-28 lg:ml-[250px] lg:pb-8">

          {/* ===================================================
              HEADER MOBILE
          =================================================== */}

          <header className="sticky top-0 z-30 flex h-16 items-center justify-between border-b border-[rgba(232,222,207,0.8)] bg-[rgba(250,248,239,0.82)] px-4 backdrop-blur-xl lg:hidden">

            <Link
              href="/"
            >

              <div className="text-[20px] font-light tracking-[0.14em] text-[var(--maried-gold)]">
                MARIED
              </div>

              <div className="text-[8px] tracking-[0.38em] text-[var(--maried-coffee)]">
                STUDIO
              </div>

            </Link>


            <motion.button
              type="button"

              whileTap={{
                scale:
                  0.97,
              }}

              onClick={() => {
                void refreshWallet();
              }}

              className="flex items-center gap-2 rounded-xl border border-[var(--maried-sand)] bg-white px-3 py-2 shadow-sm"
            >

              {loadingCredits ? (

                <LoaderCircle
                  size={
                    15
                  }

                  className="animate-spin text-[var(--maried-gold)]"
                />

              ) : (

                <Sparkles
                  size={
                    15
                  }

                  className="text-[var(--maried-gold)]"
                />

              )}


              <div className="leading-tight">

                <div className="text-sm font-semibold">

                  {loadingCredits
                    ? "Carregando"
                    : `${creditsLabel} ${
                        availableCredits ===
                        1
                          ? "crédito"
                          : "créditos"
                      }`}

                </div>


                <div className="text-[10px] text-[var(--maried-cocoa)]">

                  {creditsError
                    ? "toque para atualizar"
                    : "disponíveis"}

                </div>

              </div>

            </motion.button>

          </header>


          {children}

        </main>

      </div>


      {/* =====================================================
          NAVEGAÇÃO MOBILE
      ===================================================== */}

      <nav className="fixed bottom-0 left-0 right-0 z-50 border-t border-[var(--maried-sand)] bg-[rgba(255,255,255,0.96)] px-2 pb-[calc(env(safe-area-inset-bottom)+8px)] pt-2 backdrop-blur-xl lg:hidden">

        <div className="mx-auto grid max-w-lg grid-cols-5 items-end">

          <MobileNavItem
            href="/"

            label="Início"

            icon={
              Home
            }

            active={
              pathname === "/"
            }
          />


          <MobileNavItem
            href="/criacoes"

            label="Criações"

            icon={
              Images
            }

            active={
              isRouteActive(
                pathname,
                "/criacoes"
              )
            }
          />


          {/* CRIAR */}

          {canOperateStudio ? (

          <div className="flex justify-center">

            <motion.div
              whileTap={{
                scale:
                  0.95,
              }}

              className="-mt-7"
            >

              <Link
                href="/criar"

                aria-label="Criar nova imagem"

                className={[
                  "flex h-14 w-14 items-center justify-center rounded-full text-white shadow-[0_10px_30px_rgba(73,53,45,0.28)] transition-colors",

                  isRouteActive(
                    pathname,
                    "/criar"
                  )
                    ? "bg-[var(--maried-gold)]"
                    : "bg-[var(--maried-coffee)]",
                ].join(
                  " "
                )}
              >

                <Plus
                  size={
                    25
                  }

                  strokeWidth={
                    1.8
                  }
                />

              </Link>


              <div className="mt-1 text-center text-[9px] font-medium text-[var(--maried-cocoa)]">
                Criar
              </div>

            </motion.div>

          </div>

          ) : (

          <MobileNavItem
            href="/assinatura"

            label="Assinar"

            icon={
              CreditCard
            }

            active={
              isRouteActive(
                pathname,
                "/assinatura"
              )
            }
          />

          )}


          <MobileNavItem
            href="/pecas"

            label="Peças"

            icon={
              Gem
            }

            active={
              isRouteActive(
                pathname,
                "/pecas"
              )
            }
          />


          <MobileNavItem
            href="/perfil"

            label="Perfil"

            icon={
              UserRound
            }

            active={
              isRouteActive(
                pathname,
                "/perfil"
              )
            }
          />

        </div>

      </nav>

    </div>
  );
}


// ==========================================================
// ITEM DO MENU MOBILE
// ==========================================================

type MobileNavItemProps = {
  href: string;

  label: string;

  icon:
    React.ComponentType<{
      size?: number;
      strokeWidth?: number;
      className?: string;
    }>;

  active: boolean;
};


function MobileNavItem({
  href,
  label,
  icon: Icon,
  active,
}: MobileNavItemProps) {

  return (
    <motion.div
      whileTap={{
        scale:
          0.96,
      }}
    >

      <Link
        href={
          href
        }

        className={[
          "flex min-h-[50px] flex-col items-center justify-center gap-1 rounded-xl py-1 transition-colors",

          active
            ? "text-[var(--maried-gold)]"
            : "text-[var(--maried-cocoa)]",
        ].join(
          " "
        )}
      >

        <Icon
          size={
            20
          }

          strokeWidth={
            active
              ? 2
              : 1.7
          }
        />


        <span className="text-[9px] font-medium">
          {
            label
          }
        </span>

      </Link>

    </motion.div>
  );
}

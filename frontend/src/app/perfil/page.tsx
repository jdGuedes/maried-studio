"use client";

import {
  Building2,
  CalendarDays,
  Check,
  CreditCard,
  LoaderCircle,
  LogOut,
  Mail,
  Pencil,
  Save,
  ShieldCheck,
  UserRound,
  X,
} from "lucide-react";

import {
  motion,
} from "motion/react";

import Link from "next/link";

import {
  useEffect,
  useState,
} from "react";

import {
  getProfile,
  updateProfile,
  type UserProfile,
} from "@/lib/profile";

import {
  getCurrentSubscription,
  type ClientSubscription,
} from "@/lib/subscription";

import {
  useLogout,
} from "@/lib/logout";

import {
  useCreditWallet,
} from "@/providers/credit-wallet-provider";

import {
  useProfile,
} from "@/providers/profile-provider";


function formatDate(
  value: string | null
) {
  if (!value) {
    return "Não informado";
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
    new Date(
      value
    )
  );
}


function getSubscriptionStatusLabel(
  subscription: ClientSubscription | null
) {
  if (!subscription?.status) {
    return "Sem assinatura ativa";
  }

  if (
    subscription.operational_status ===
    "GRACE"
  ) {
    return "Em período de tolerância";
  }

  if (
    subscription.operational_status ===
    "BLOCKED"
  ) {
    return "Assinatura bloqueada";
  }

  return "Ativa";
}


export default function ProfilePage() {

  const {
    availableCredits,
    error:
      walletError,
    loading:
      loadingWallet,
    wallet,
  } =
    useCreditWallet();

  const {
    refreshProfile,
  } =
    useProfile();

  const {
    loggingOut,
    logoutError,
    performLogout,
  } =
    useLogout();


  const [
    profile,
    setProfile,
  ] = useState<UserProfile | null>(
    null
  );


  const [
    loading,
    setLoading,
  ] = useState(
    true
  );


  const [
    saving,
    setSaving,
  ] = useState(
    false
  );


  const [
    editing,
    setEditing,
  ] = useState(
    false
  );


  const [
    error,
    setError,
  ] = useState<string | null>(
    null
  );


  const [
    subscription,
    setSubscription,
  ] = useState<ClientSubscription | null>(
    null
  );


  const [
    loadingSubscription,
    setLoadingSubscription,
  ] = useState(
    true
  );


  const [
    subscriptionError,
    setSubscriptionError,
  ] = useState<string | null>(
    null
  );


  const [
    success,
    setSuccess,
  ] = useState<string | null>(
    null
  );


  const [
    name,
    setName,
  ] = useState(
    ""
  );


  const [
    organizationName,
    setOrganizationName,
  ] = useState(
    ""
  );


  // ========================================================
  // CARREGAR PERFIL
  // ========================================================

  useEffect(() => {

    async function load() {

      setLoading(
        true
      );

      setError(
        null
      );


      try {

        const data =
          await getProfile();


        setProfile(
          data
        );


        setName(
          data.name
        );


        setOrganizationName(
          data.organization?.name ??
          ""
        );

      } catch (error) {

        setError(
          error instanceof Error
            ? error.message
            : "Não foi possível carregar seu perfil."
        );

      } finally {

        setLoading(
          false
        );

      }

    }


    void load();

  }, []);


  // ========================================================
  // CARREGAR ASSINATURA
  // ========================================================

  useEffect(() => {

    async function loadSubscription() {
      setLoadingSubscription(
        true
      );

      setSubscriptionError(
        null
      );

      try {
        const data =
          await getCurrentSubscription();

        setSubscription(
          data
        );
      } catch (error) {
        setSubscriptionError(
          error instanceof Error
            ? error.message
            : "Não foi possível carregar sua assinatura."
        );
      } finally {
        setLoadingSubscription(
          false
        );
      }
    }

    void loadSubscription();

  }, []);


  // ========================================================
  // SALVAR PERFIL
  // ========================================================

  async function handleSave() {

    if (
      !profile
    ) {
      return;
    }


    setSaving(
      true
    );

    setError(
      null
    );

    setSuccess(
      null
    );


    try {

      const payload: {
        name?: string;
        organization_name?: string;
      } = {};


      if (
        name.trim() !==
        profile.name
      ) {
        payload.name =
          name.trim();
      }


      if (
        profile.role ===
          "OWNER" &&
        organizationName.trim() !==
          (
            profile.organization
              ?.name ??
            ""
          )
      ) {
        payload.organization_name =
          organizationName.trim();
      }


      if (
        Object.keys(
          payload
        ).length === 0
      ) {
        setEditing(
          false
        );

        return;
      }


      const updated =
        await updateProfile(
          payload
        );

      const syncedProfile =
        await refreshProfile();

      const nextProfile =
        syncedProfile ??
        updated;

      setProfile(
        nextProfile
      );


      setName(
        nextProfile.name
      );


      setOrganizationName(
        nextProfile.organization
          ?.name ??
        ""
      );


      setEditing(
        false
      );


      setSuccess(
        "Perfil atualizado com sucesso."
      );

    } catch (error) {

      setError(
        error instanceof Error
          ? error.message
          : "Não foi possível atualizar seu perfil."
      );

    } finally {

      setSaving(
        false
      );

    }
  }


  // ========================================================
  // LOADING
  // ========================================================

  if (
    loading
  ) {
    return (
      <main className="flex min-h-[420px] items-center justify-center px-4 py-8">

        <LoaderCircle
          size={
            30
          }

          className="animate-spin text-[var(--maried-gold)]"
        />

      </main>
    );
  }


  // ========================================================
  // ERRO SEM PERFIL
  // ========================================================

  if (
    !profile
  ) {
    return (
      <main className="px-4 py-8 sm:px-6 lg:px-8">

        <div className="mx-auto max-w-[900px] rounded-xl border border-red-200 bg-red-50 p-5 text-sm text-red-700">
          {error ??
            "Perfil não encontrado."}
        </div>

      </main>
    );
  }


  const initial =
    (
      profile.name?.trim()?.[0] ??
      profile.email?.trim()?.[0] ??
      "U"
    ).toUpperCase();


  return (
    <main className="px-4 py-6 sm:px-6 lg:px-8 lg:py-8">

      <div className="mx-auto max-w-[1000px]">

        {/* =================================================
            CABEÇALHO
        ================================================= */}

        <section className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">

          <div>

            <h1 className="text-[30px] font-semibold tracking-[-0.035em] text-[var(--maried-espresso)] sm:text-[36px]">
              Meu perfil
            </h1>


            <p className="mt-2 text-sm text-[var(--maried-cocoa)]">
              Gerencie seus dados pessoais
              e informações da sua conta.
            </p>

          </div>


          {!editing ? (

            <div className="flex flex-col gap-2 sm:flex-row">

              <motion.button
                type="button"

                whileTap={{
                  scale:
                    0.98,
                }}

                onClick={() => {
                  setEditing(
                    true
                  );

                  setSuccess(
                    null
                  );
                }}

                className="flex h-11 items-center justify-center gap-2 rounded-xl border border-[var(--maried-sand)] bg-white px-4 text-sm font-medium text-[var(--maried-coffee)]"
              >

                <Pencil
                  size={
                    16
                  }
                />

                Editar perfil

              </motion.button>


              <button
                type="button"

                disabled={
                  loggingOut ||
                  saving
                }

                onClick={() => {
                  void performLogout();
                }}

                className="flex h-11 items-center justify-center gap-2 rounded-xl border border-[var(--maried-sand)] bg-white px-4 text-sm font-medium text-[var(--maried-cocoa)] transition-colors hover:bg-[var(--maried-cream)] disabled:opacity-60"
              >

                {loggingOut ? (

                  <LoaderCircle
                    size={
                      16
                    }

                    className="animate-spin"
                  />

                ) : (

                  <LogOut
                    size={
                      16
                    }
                  />

                )}

                {loggingOut
                  ? "Saindo..."
                  : "Sair"}

              </button>

            </div>

          ) : (

            <div className="flex gap-2">

              <button
                type="button"

                disabled={
                  saving
                }

                onClick={() => {

                  setEditing(
                    false
                  );

                  setName(
                    profile.name
                  );

                  setOrganizationName(
                    profile.organization
                      ?.name ??
                    ""
                  );

                }}

                className="flex h-11 items-center gap-2 rounded-xl border border-[var(--maried-sand)] bg-white px-4 text-sm"
              >

                <X
                  size={
                    16
                  }
                />

                Cancelar

              </button>


              <button
                type="button"

                disabled={
                  saving
                }

                onClick={() => {
                  void handleSave();
                }}

                className="flex h-11 items-center gap-2 rounded-xl bg-[var(--maried-gold)] px-4 text-sm font-medium text-white disabled:opacity-60"
              >

                {saving ? (

                  <LoaderCircle
                    size={
                      16
                    }

                    className="animate-spin"
                  />

                ) : (

                  <Save
                    size={
                      16
                    }
                  />

                )}

                Salvar

              </button>

            </div>

          )}

        </section>


        {/* =================================================
            FEEDBACK
        ================================================= */}

        {success ? (

          <div className="mt-5 flex items-center gap-2 rounded-xl border border-green-200 bg-green-50 px-4 py-3 text-xs text-green-700">

            <Check
              size={
                15
              }
            />

            {
              success
            }

          </div>

        ) : null}


        {error ? (

          <div className="mt-5 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-xs text-red-700">
            {
              error
            }
          </div>

        ) : null}


        {logoutError ? (

          <div className="mt-5 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-xs text-red-700">
            {logoutError}
          </div>

        ) : null}


        {/* =================================================
            CARTÃO PRINCIPAL
        ================================================= */}

        <section className="maried-card mt-7 p-5 sm:p-6">

          <div className="flex flex-col gap-5 sm:flex-row sm:items-center">

            <div className="flex h-16 w-16 items-center justify-center rounded-full bg-[var(--maried-soft-gold)] text-xl font-semibold text-[var(--maried-coffee)]">
              {
                initial
              }
            </div>


            <div className="min-w-0">

              <h2 className="truncate text-xl font-semibold text-[var(--maried-espresso)]">
                {
                  profile.name
                }
              </h2>


              <div className="mt-1 flex items-center gap-2 text-xs text-[var(--maried-cocoa)]">

                <Mail
                  size={
                    14
                  }
                />

                {
                  profile.email
                }

              </div>


              <div className="mt-2 inline-flex rounded-full bg-[var(--maried-soft-gold)] px-3 py-1 text-[10px] font-medium text-[var(--maried-coffee)]">
                {
                  profile.role_label
                }
              </div>

            </div>

          </div>

        </section>


        {/* =================================================
            DADOS
        ================================================= */}

        <div className="mt-5 grid gap-5 lg:grid-cols-2">

          {/* PERFIL */}

          <section className="maried-card p-5">

            <div className="flex items-center gap-2">

              <UserRound
                size={
                  17
                }

                className="text-[var(--maried-gold)]"
              />

              <h2 className="text-sm font-semibold">
                Dados pessoais
              </h2>

            </div>


            <div className="mt-5">

              <label className="text-[11px] text-[var(--maried-cocoa)]">
                Nome
              </label>


              <input
                value={
                  name
                }

                disabled={
                  !editing
                }

                onChange={(
                  event
                ) => {
                  setName(
                    event.target.value
                  );
                }}

                className="mt-2 h-11 w-full rounded-xl border border-[var(--maried-sand)] bg-white px-3 text-sm outline-none disabled:bg-[var(--maried-cream)] disabled:text-[var(--maried-cocoa)] focus:border-[var(--maried-gold)]"
              />

            </div>


            <div className="mt-4">

              <label className="text-[11px] text-[var(--maried-cocoa)]">
                E-mail
              </label>


              <input
                value={
                  profile.email
                }

                disabled

                className="mt-2 h-11 w-full rounded-xl border border-[var(--maried-sand)] bg-[var(--maried-cream)] px-3 text-sm text-[var(--maried-cocoa)]"
              />


              <p className="mt-2 text-[10px] text-[var(--maried-caramel)]">
                Alteração de e-mail ficará disponível
                em uma etapa com confirmação de segurança.
              </p>

            </div>

          </section>


          {/* EMPRESA */}

          <section className="maried-card p-5">

            <div className="flex items-center gap-2">

              <Building2
                size={
                  17
                }

                className="text-[var(--maried-gold)]"
              />

              <h2 className="text-sm font-semibold">
                Empresa
              </h2>

            </div>


            <div className="mt-5">

              <label className="text-[11px] text-[var(--maried-cocoa)]">
                Nome da organização
              </label>


              <input
                value={
                  organizationName
                }

                disabled={
                  !editing ||
                  profile.role !==
                    "OWNER"
                }

                onChange={(
                  event
                ) => {
                  setOrganizationName(
                    event.target.value
                  );
                }}

                className="mt-2 h-11 w-full rounded-xl border border-[var(--maried-sand)] bg-white px-3 text-sm outline-none disabled:bg-[var(--maried-cream)] disabled:text-[var(--maried-cocoa)] focus:border-[var(--maried-gold)]"
              />

            </div>


            <div className="mt-4">

              <div className="text-[11px] text-[var(--maried-cocoa)]">
                Status
              </div>


              <div className="mt-2 inline-flex rounded-full bg-green-50 px-3 py-1 text-[10px] font-medium text-green-700">
                {profile.organization
                  ?.is_active
                    ? "Ativa"
                    : "Inativa"}
              </div>

            </div>

          </section>

        </div>


        {/* =================================================
            CONTA
        ================================================= */}

        <div className="mt-5 grid gap-5 lg:grid-cols-2">

          {/* CRÉDITOS */}

          <section className="maried-card p-5">

            <div className="flex items-center gap-2">

              <CreditCard
                size={
                  17
                }

                className="text-[var(--maried-gold)]"
              />

              <h2 className="text-sm font-semibold">
                Créditos
              </h2>

            </div>

            {loadingWallet ? (

              <div className="mt-5 flex min-h-[120px] items-center">
                <LoaderCircle
                  size={
                    22
                  }

                  className="animate-spin text-[var(--maried-gold)]"
                />
              </div>

            ) : (

              <>
                <div className="mt-5 text-4xl font-semibold tracking-[-0.04em] text-[var(--maried-espresso)]">
                  {
                    availableCredits ??
                    0
                  }
                </div>


                <div className="mt-1 text-xs text-[var(--maried-cocoa)]">
                  total disponível
                </div>


                <div className="mt-5 grid gap-3 sm:grid-cols-2">

                  <div className="rounded-xl border border-[var(--maried-sand)] bg-white px-3 py-3">
                    <div className="text-[10px] font-medium uppercase text-[var(--maried-caramel)]">
                      Plano
                    </div>

                    <div className="mt-1 text-xl font-semibold text-[var(--maried-espresso)]">
                      {
                        wallet?.available_plan_balance ??
                        0
                      }
                    </div>

                    <p className="mt-1 text-[10px] leading-4 text-[var(--maried-cocoa)]">
                      Não acumulam entre ciclos.
                    </p>
                  </div>


                  <div className="rounded-xl border border-[var(--maried-sand)] bg-white px-3 py-3">
                    <div className="text-[10px] font-medium uppercase text-[var(--maried-caramel)]">
                      Comprados
                    </div>

                    <div className="mt-1 text-xl font-semibold text-[var(--maried-espresso)]">
                      {
                        wallet?.available_purchased_balance ??
                        0
                      }
                    </div>

                    <p className="mt-1 text-[10px] leading-4 text-[var(--maried-cocoa)]">
                      Não expiram.
                    </p>
                  </div>

                </div>


                {walletError ? (

                  <div className="mt-4 rounded-xl border border-red-200 bg-red-50 px-3 py-2 text-xs text-red-700">
                    {walletError}
                  </div>

                ) : null}


                <div className="mt-5 flex flex-col gap-2 sm:flex-row">

                  <Link
                    href="/creditos"

                    className="flex h-10 items-center justify-center rounded-xl border border-[var(--maried-sand)] bg-white px-4 text-xs font-medium text-[var(--maried-gold)]"
                  >
                    Ver meus créditos
                  </Link>


                  <button
                    type="button"

                    className="h-10 rounded-xl border border-[var(--maried-sand)] bg-white px-4 text-xs font-medium text-[var(--maried-gold)]"
                  >
                    Adicionar créditos
                  </button>

                </div>
              </>

            )}

          </section>


          {/* SEGURANÇA */}

          <section className="maried-card p-5">

            <div className="flex items-center gap-2">

              <ShieldCheck
                size={
                  17
                }

                className="text-[var(--maried-gold)]"
              />

              <h2 className="text-sm font-semibold">
                Segurança
              </h2>

            </div>


            <p className="mt-4 text-xs leading-5 text-[var(--maried-cocoa)]">
              Em breve você poderá alterar sua senha
              e gerenciar sessões abertas diretamente
              por aqui.
            </p>


            <button
              type="button"

              disabled

              className="mt-5 h-10 rounded-xl border border-[var(--maried-sand)] bg-[var(--maried-cream)] px-4 text-xs text-[var(--maried-caramel)]"
            >
              Alterar senha
            </button>

          </section>

        </div>


        {/* =================================================
            ASSINATURA
        ================================================= */}

        <section className="maried-card mt-5 p-5">

          <div className="flex items-center gap-2">

            <CalendarDays
              size={
                17
              }

              className="text-[var(--maried-gold)]"
            />

            <h2 className="text-sm font-semibold">
              Assinatura
            </h2>

          </div>


          {loadingSubscription ? (

            <div className="mt-5 flex min-h-[120px] items-center">
              <LoaderCircle
                size={
                  22
                }

                className="animate-spin text-[var(--maried-gold)]"
              />
            </div>

          ) : subscriptionError ? (

            <div className="mt-5 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-xs text-red-700">
              {subscriptionError}
            </div>

          ) : (

            <>
              <div className="mt-5 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">

                <div>

                  <div className="text-[11px] text-[var(--maried-cocoa)]">
                    Plano
                  </div>

                  <div className="mt-1 text-xl font-semibold text-[var(--maried-espresso)]">
                    {subscription?.plan_name ??
                      "Sem assinatura ativa"}
                  </div>

                </div>


                <div
                  className={[
                    "inline-flex w-fit rounded-full px-3 py-1 text-[10px] font-medium",

                    !subscription?.status
                      ? "bg-[var(--maried-cream)] text-[var(--maried-cocoa)]"
                      : subscription.operational_status ===
                      "BLOCKED"
                      ? "bg-red-50 text-red-700"
                      : subscription.operational_status ===
                          "GRACE"
                        ? "bg-amber-50 text-amber-700"
                        : "bg-green-50 text-green-700",
                  ].join(
                    " "
                  )}
                >
                  {
                    getSubscriptionStatusLabel(
                      subscription
                    )
                  }
                </div>

              </div>


              {subscription?.status ? (

                <>
                  <div className="mt-5 grid gap-4 sm:grid-cols-3">

                    <div>
                      <div className="text-[11px] text-[var(--maried-cocoa)]">
                        Ciclo atual
                      </div>

                      <div className="mt-1 text-xs font-medium text-[var(--maried-coffee)]">
                        {formatDate(
                          subscription.current_period_start
                        )}{" "}
                        →{" "}
                        {formatDate(
                          subscription.current_period_end
                        )}
                      </div>
                    </div>


                    <div>
                      <div className="text-[11px] text-[var(--maried-cocoa)]">
                        Próxima renovação
                      </div>

                      <div className="mt-1 text-xs font-medium text-[var(--maried-coffee)]">
                        {formatDate(
                          subscription.next_billing_at
                        )}
                      </div>
                    </div>


                    <div>
                      <div className="text-[11px] text-[var(--maried-cocoa)]">
                        Créditos do plano
                      </div>

                      <div className="mt-1 text-xs font-medium text-[var(--maried-coffee)]">
                        {subscription.credits_per_cycle ??
                          0}{" "}
                        por ciclo mensal
                      </div>
                    </div>

                  </div>


                  {subscription.operational_status ===
                  "GRACE" ? (

                    <p className="mt-5 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-xs leading-5 text-amber-800">
                      Regularize sua assinatura até{" "}
                      {formatDate(
                        subscription.grace_until
                      )}{" "}
                      para evitar interrupção do Studio.
                    </p>

                  ) : null}


                  {subscription.operational_status ===
                  "BLOCKED" ? (

                    <p className="mt-5 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-xs leading-5 text-red-700">
                      Regularize sua assinatura para voltar
                      a criar imagens. Seus dados e créditos
                      permanecem preservados.
                    </p>

                  ) : null}
                </>

              ) : (

                <p className="mt-4 text-xs leading-5 text-[var(--maried-cocoa)]">
                  Nenhum plano ativo está vinculado à sua conta.
                </p>

              )}
            </>

          )}

        </section>

      </div>

    </main>
  );
}

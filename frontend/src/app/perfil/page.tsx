"use client";

import {
  Building2,
  Check,
  CreditCard,
  LoaderCircle,
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
  useCreditWallet,
} from "@/providers/credit-wallet-provider";

import {
  useProfile,
} from "@/providers/profile-provider";


export default function ProfilePage() {

  const {
    availableCredits,
  } =
    useCreditWallet();

  const {
    refreshProfile,
  } =
    useProfile();


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


            <div className="mt-5 text-4xl font-semibold tracking-[-0.04em] text-[var(--maried-espresso)]">
              {
                availableCredits ??
                0
              }
            </div>


            <div className="mt-1 text-xs text-[var(--maried-cocoa)]">
              créditos disponíveis
            </div>


            <button
              type="button"

              className="mt-5 h-10 rounded-xl border border-[var(--maried-sand)] bg-white px-4 text-xs font-medium text-[var(--maried-gold)]"
            >
              Adicionar créditos
            </button>

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

          <h2 className="text-sm font-semibold">
            Assinatura
          </h2>


          <p className="mt-2 text-xs leading-5 text-[var(--maried-cocoa)]">
            A estrutura de assinatura será adicionada
            quando conectarmos os planos e cobranças.
            Nenhuma informação fictícia está sendo exibida.
          </p>

        </section>

      </div>

    </main>
  );
}

"use client";

import {
  usePathname,
  useRouter,
} from "next/navigation";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

import {
  ProfileApiError,
  getProfile,
  type UserProfile,
} from "@/lib/profile";


// ==========================================================
// TIPO DO CONTEXTO
// ==========================================================

type ProfileContextValue = {
  profile: UserProfile | null;

  loading: boolean;

  error: string | null;

  refreshProfile:
    () => Promise<UserProfile | null>;

  setAuthenticatedProfile:
    (profile: UserProfile | null) => void;

  isSuperAdmin: boolean;

  isOwner: boolean;

  displayName: string;

  firstName: string;

  organizationName: string;

  initials: string;
};


// ==========================================================
// CONTEXTO
// ==========================================================

const ProfileContext =
  createContext<
    ProfileContextValue | undefined
  >(
    undefined
  );


// ==========================================================
// PROPS
// ==========================================================

type ProfileProviderProps = {
  children: ReactNode;
};


// ==========================================================
// PROVIDER
// ==========================================================

export function ProfileProvider({
  children,
}: ProfileProviderProps) {

  const pathname =
    usePathname();

  const router =
    useRouter();

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
    error,
    setError,
  ] = useState<string | null>(
    null
  );


  // ========================================================
  // CARREGAR PERFIL
  // ========================================================

  const refreshProfile =
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
            await getProfile();


          setProfile(
            data
          );


          return data;

        } catch (error) {

          console.error(
            "Erro ao carregar perfil:",
            error
          );

          if (
            error instanceof
              ProfileApiError &&
            (
              error.status === 401 ||
              error.status === 403
            )
          ) {
            setProfile(
              null
            );

            if (
              pathname !==
              "/login"
            ) {
              const next =
                encodeURIComponent(
                  pathname || "/"
                );

              router.replace(
                `/login?next=${next}`
              );
            }
          }


          const message =
            error instanceof Error
              ? error.message
              : "Não foi possível carregar o perfil.";


          setError(
            message
          );


          return null;

        } finally {

          setLoading(
            false
          );

        }

      },
      [
        pathname,
        router,
      ]
    );


  const setAuthenticatedProfile =
    useCallback(
      (
        profile:
          UserProfile | null
      ) => {
        setProfile(
          profile
        );

        setError(
          null
        );

        setLoading(
          false
        );
      },
      []
    );


  // ========================================================
  // PRIMEIRO CARREGAMENTO
  // ========================================================

  useEffect(() => {

    const timer =
      window.setTimeout(
        () => {
          void refreshProfile();
        },
        0
      );

    return () => {
      window.clearTimeout(
        timer
      );
    };

  }, [
    refreshProfile,
  ]);


  // ========================================================
  // DADOS DERIVADOS
  // ========================================================

  const displayName =
    profile?.name?.trim()
    ||
    profile?.email
    ||
    "Usuário";


  const firstName =
    displayName
      .split(/\s+/)
      .filter(Boolean)[0]
    ||
    "Usuário";


  const organizationName =
    profile
      ?.organization
      ?.name
    ||
    "Organização não vinculada";


  const initials =
    displayName
      .split(/\s+/)
      .filter(Boolean)
      .slice(
        0,
        2
      )
      .map(
        (
          part
        ) =>
          part
            .charAt(0)
            .toUpperCase()
      )
      .join("")
    ||
    "U";


  // ========================================================
  // PERMISSÕES
  // ========================================================

  const isSuperAdmin =
    profile?.is_superuser ===
    true;


  const isOwner =
    profile?.role ===
    "OWNER";


  // ========================================================
  // VALUE
  // ========================================================

  const value =
    useMemo<
      ProfileContextValue
    >(
      () => ({
        profile,

        loading,

        error,

        refreshProfile,

        setAuthenticatedProfile,

        isSuperAdmin,

        isOwner,

        displayName,

        firstName,

        organizationName,

        initials,
      }),

      [
        profile,
        loading,
        error,
        refreshProfile,
        setAuthenticatedProfile,
        isSuperAdmin,
        isOwner,
        displayName,
        firstName,
        organizationName,
        initials,
      ]
    );


  return (
    <ProfileContext.Provider
      value={
        value
      }
    >
      {
        children
      }
    </ProfileContext.Provider>
  );
}


// ==========================================================
// HOOK
// ==========================================================

export function useProfile() {

  const context =
    useContext(
      ProfileContext
    );


  if (
    !context
  ) {
    throw new Error(
      "useProfile deve ser usado dentro de ProfileProvider."
    );
  }


  return context;
}

"use client";

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
  getCreditWallet,
  type CreditWallet,
} from "@/lib/credit-wallet";

import {
  useProfile,
} from "@/providers/profile-provider";


// ==========================================================
// CONTEXTO
// ==========================================================

type CreditWalletContextValue = {
  wallet: CreditWallet | null;

  availableCredits: number | null;

  loading: boolean;

  error: string | null;

  refreshWallet: () => Promise<void>;

  clearWallet: () => void;

  setWalletFromGeneration: (
    availableCredits: number
  ) => void;
};


const CreditWalletContext =
  createContext<CreditWalletContextValue | null>(
    null
  );


// ==========================================================
// PROPS
// ==========================================================

type CreditWalletProviderProps = {
  children: ReactNode;
};


// ==========================================================
// PROVIDER
// ==========================================================

export function CreditWalletProvider({
  children,
}: CreditWalletProviderProps) {
  const {
    profile,
    loading:
      loadingProfile,
  } =
    useProfile();

  const [
    wallet,
    setWallet,
  ] = useState<CreditWallet | null>(
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
  // BUSCAR CARTEIRA REAL
  // ========================================================

  const refreshWallet =
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
            await getCreditWallet();

          setWallet(
            data
          );

        } catch (error) {
          console.error(
            "Erro ao carregar carteira de créditos:",
            error
          );

          setError(
            error instanceof Error
              ? error.message
              : "Não foi possível carregar seus créditos."
          );

        } finally {
          setLoading(
            false
          );
        }
      },
      []
    );


  const clearWallet =
    useCallback(
      () => {
        setWallet(
          null
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
          if (
            loadingProfile
          ) {
            return;
          }

          if (
            !profile
          ) {
            clearWallet();
            return;
          }

          if (
            !profile.is_superuser &&
            profile.recovery_configured ===
              false
          ) {
            clearWallet();
            return;
          }

          void refreshWallet();
        },
        0
      );

    return () => {
      window.clearTimeout(
        timer
      );
    };
  }, [
    clearWallet,
    loadingProfile,
    profile,
    refreshWallet,
  ]);


  // ========================================================
  // ATUALIZAÇÃO RÁPIDA APÓS GERAÇÃO
  //
  // Podemos usar available_credits retornado pela Generation
  // e depois, se quisermos, sincronizar novamente com o backend.
  // ========================================================

  const setWalletFromGeneration =
    useCallback(
      (
        availableCredits: number
      ) => {
        setWallet(
          (
            currentWallet
          ) => {
            if (!currentWallet) {
              return currentWallet;
            }

            return {
              ...currentWallet,

              available_balance:
                availableCredits,

              // Em uma geração concluída,
              // normalmente não deve restar
              // reserva daquela geração.
              reserved_balance:
                0,

              // O balance real também tende
              // a refletir o saldo disponível
              // quando não há reservas.
              balance:
                availableCredits,
            };
          }
        );
      },
      []
    );


  // ========================================================
  // SALDO DISPONÍVEL
  // ========================================================

  const availableCredits =
    wallet?.available_balance ??
    null;


  // ========================================================
  // VALUE
  // ========================================================

  const value =
    useMemo<CreditWalletContextValue>(
      () => ({
        wallet,

        availableCredits,

        loading,

        error,

        refreshWallet,

        clearWallet,

        setWalletFromGeneration,
      }),
      [
        wallet,
        availableCredits,
        loading,
        error,
        refreshWallet,
        clearWallet,
        setWalletFromGeneration,
      ]
    );


  return (
    <CreditWalletContext.Provider
      value={
        value
      }
    >
      {children}
    </CreditWalletContext.Provider>
  );
}


// ==========================================================
// HOOK
// ==========================================================

export function useCreditWallet() {
  const context =
    useContext(
      CreditWalletContext
    );

  if (!context) {
    throw new Error(
      "useCreditWallet precisa ser usado dentro de CreditWalletProvider."
    );
  }

  return context;
}

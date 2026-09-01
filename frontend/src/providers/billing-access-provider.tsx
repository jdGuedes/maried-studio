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
  canOperateStudioFromSubscription,
  getBillingAccessCtaLabel,
  getBillingAccessMessage,
  getCurrentSubscription,
  type ClientSubscription,
} from "@/lib/subscription";

import {
  useProfile,
} from "@/providers/profile-provider";


type BillingAccessContextValue = {
  subscription:
    ClientSubscription | null;

  loading: boolean;

  error:
    string | null;

  canOperateStudio: boolean;

  accessMessage: string;

  accessCtaLabel: string;

  refreshBillingAccess:
    () => Promise<ClientSubscription | null>;
};


const BillingAccessContext =
  createContext<BillingAccessContextValue | null>(
    null
  );


type BillingAccessProviderProps = {
  children: ReactNode;
};


export function BillingAccessProvider({
  children,
}: BillingAccessProviderProps) {
  const {
    profile,
    isSuperAdmin,
  } =
    useProfile();

  const [
    subscription,
    setSubscription,
  ] = useState<ClientSubscription | null>(
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

  const refreshBillingAccess =
    useCallback(
      async () => {
        if (
          !profile ||
          isSuperAdmin
        ) {
          setSubscription(
            null
          );
          setError(
            null
          );
          setLoading(
            false
          );

          return null;
        }

        setLoading(
          true
        );
        setError(
          null
        );

        try {
          const data =
            await getCurrentSubscription();

          setSubscription(
            data
          );

          return data;
        } catch (error) {
          setSubscription(
            null
          );

          setError(
            error instanceof Error
              ? error.message
              : "Não foi possível consultar sua assinatura."
          );

          return null;
        } finally {
          setLoading(
            false
          );
        }
      },
      [
        profile,
        isSuperAdmin,
      ]
    );

  useEffect(() => {
    const timer =
      window.setTimeout(
        () => {
          void refreshBillingAccess();
        },
        0
      );

    return () => {
      window.clearTimeout(
        timer
      );
    };
  }, [
    refreshBillingAccess,
  ]);

  const canOperateStudio =
    isSuperAdmin ||
    canOperateStudioFromSubscription(
      subscription
    );

  const value =
    useMemo<BillingAccessContextValue>(
      () => ({
        subscription,
        loading,
        error,
        canOperateStudio,
        accessMessage:
          getBillingAccessMessage(
            subscription
          ),
        accessCtaLabel:
          getBillingAccessCtaLabel(
            subscription
          ),
        refreshBillingAccess,
      }),
      [
        subscription,
        loading,
        error,
        canOperateStudio,
        refreshBillingAccess,
      ]
    );

  return (
    <BillingAccessContext.Provider
      value={
        value
      }
    >
      {children}
    </BillingAccessContext.Provider>
  );
}


export function useBillingAccess() {
  const context =
    useContext(
      BillingAccessContext
    );

  if (!context) {
    throw new Error(
      "useBillingAccess precisa ser usado dentro de BillingAccessProvider."
    );
  }

  return context;
}

"use client";

import {
  useRouter,
} from "next/navigation";

import {
  useState,
} from "react";

import {
  ApiError,
  logoutUser,
} from "@/lib/api";
import {
  useCreditWallet,
} from "@/providers/credit-wallet-provider";
import {
  useProfile,
} from "@/providers/profile-provider";


export function useLogout() {
  const router =
    useRouter();

  const {
    setAuthenticatedProfile,
  } = useProfile();

  const {
    clearWallet,
  } = useCreditWallet();

  const [
    loggingOut,
    setLoggingOut,
  ] = useState(false);

  const [
    logoutError,
    setLogoutError,
  ] = useState<string | null>(null);

  async function performLogout() {
    if (loggingOut) {
      return;
    }

    setLoggingOut(true);
    setLogoutError(null);

    try {
      await logoutUser();

      setAuthenticatedProfile(null);
      clearWallet();
      router.replace("/login");
    } catch (error) {
      if (
        error instanceof ApiError &&
        [401, 403].includes(error.status)
      ) {
        setAuthenticatedProfile(null);
        clearWallet();
        router.replace("/login");
        return;
      }

      setLogoutError(
        error instanceof Error
          ? error.message
          : "Não foi possível encerrar sua sessão."
      );
    } finally {
      setLoggingOut(false);
    }
  }

  return {
    loggingOut,
    logoutError,
    performLogout,
  };
}

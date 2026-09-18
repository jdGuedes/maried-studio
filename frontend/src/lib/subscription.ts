import {
  ensureCsrfCookie,
} from "@/lib/api";

import {
  API_URL,
} from "@/lib/api-url";


// ==========================================================
// MARIED STUDIO
// ASSINATURA DO CLIENTE
// ==========================================================


// ==========================================================
// TIPOS
// ==========================================================

export type ClientSubscriptionPlan = {
  id: string;

  name: string;

  credits_per_cycle: number;

  extra_credit_limit_per_cycle: number;

  billing_cycle: string;
};


export type ClientSubscription = {
  status: string | null;

  operational_status:
    | "ACTIVE"
    | "GRACE"
    | "BLOCKED"
    | string;

  plan_name: string | null;

  plan: ClientSubscriptionPlan | null;

  billing_cycle: string | null;

  credits_per_cycle: number | null;

  current_period_start: string | null;

  current_period_end: string | null;

  next_billing_at: string | null;

  cancel_at_period_end: boolean;

  grace_until: string | null;

  days_remaining_in_grace: number | null;

  can_create: boolean;

  can_purchase_credits: boolean;

  can_start_subscription: boolean;

  financial_blocked: boolean;

  access_reason: string;

  extra_credit_limit_per_cycle: number;

  paid_credits_this_cycle: number;

  pending_credits_this_cycle: number;

  remaining_extra_credits: number;
};


export function canOperateStudioFromSubscription(
  subscription:
    ClientSubscription | null
) {
  return (
    subscription?.can_create ??
    false
  );
}


export function isPendingFirstPayment(
  subscription:
    ClientSubscription | null
) {
  return (
    subscription?.status ===
      "PENDING"
  );
}


export function getBillingAccessMessage(
  subscription:
    ClientSubscription | null
) {
  if (
    subscription?.financial_blocked
  ) {
    return "Sua conta possui uma contestação financeira em análise.";
  }

  if (
    isPendingFirstPayment(
      subscription
    )
  ) {
    return "Ative sua assinatura para começar a criar.";
  }

  return "Sua assinatura precisa ser regularizada para criar novas imagens.";
}


export function getBillingAccessCtaLabel(
  subscription:
    ClientSubscription | null
) {
  if (
    subscription?.financial_blocked
  ) {
    return "Ver assinatura";
  }

  if (
    isPendingFirstPayment(
      subscription
    )
  ) {
    return "Ver planos";
  }

  return "Ver assinatura";
}


export type AvailablePlan = {
  id: string;

  name: string;

  description: string;

  price: string;

  billing_cycle: string;

  credits_per_cycle: number;

  stripe_ready_for_checkout: boolean;
};


export type SubscriptionCheckoutResponse = {
  checkout_session_id: string;

  url: string;
};


export type CreditPackage = {
  id: string;

  name: string;

  description: string;

  credits: number;

  price: string;

  currency: string;

  stripe_ready_for_checkout: boolean;

  checkout_available: boolean;

  checkout_unavailable_reason: string;

  pending_purchase: {
    id: string;
    status: string;
    checkout_session_id: string;
    checkout_url: string;
    expires_at: string | null;
    credits_snapshot: number;
  } | null;
};


export type CreditCheckoutResponse = {
  purchase_id: string;

  checkout_session_id: string;

  url: string;

  status: string;
};


export type CreditPurchase = {
  id: string;

  package_name: string;

  status: string;

  credits_snapshot: number;

  price_snapshot: string;

  currency_snapshot: string;

  stripe_checkout_session_id: string;

  cycle_start: string;

  cycle_end: string;

  paid_at: string | null;

  created_at: string;

  updated_at: string;
};


// ==========================================================
// ERRO DA API
// ==========================================================

type ApiErrorData = {
  detail?: string;

  [key: string]:
    unknown;
};


export class SubscriptionApiError
  extends Error {

  status: number;

  data:
    ApiErrorData | null;


  constructor(
    message: string,
    status: number,
    data:
      ApiErrorData | null =
      null
  ) {
    super(message);

    this.name =
      "SubscriptionApiError";

    this.status =
      status;

    this.data =
      data;
  }
}


// ==========================================================
// PARSE DA RESPOSTA
// ==========================================================

async function parseResponse<T>(
  response: Response
): Promise<T> {
  let data:
    unknown = null;

  try {
    data =
      await response.json();
  } catch {
    data = null;
  }

  if (!response.ok) {
    const errorData =
      data &&
      typeof data === "object"
        ? (
            data as
              ApiErrorData
          )
        : null;

    throw new SubscriptionApiError(
      errorData?.detail ??
        `Erro ao consultar assinatura (${response.status}).`,
      response.status,
      errorData
    );
  }

  return data as T;
}


function getCookie(
  name: string
): string | null {
  if (
    typeof document === "undefined"
  ) {
    return null;
  }

  const cookie =
    document.cookie
      .split("; ")
      .find(
        (
          row
        ) =>
          row.startsWith(
            `${name}=`
          )
      );

  if (!cookie) {
    return null;
  }

  return decodeURIComponent(
    cookie.substring(
      name.length + 1
    )
  );
}


function getCsrfHeaders():
  Record<string, string> {
  const token =
    getCookie(
      "csrftoken"
    );

  if (!token) {
    return {};
  }

  return {
    "X-CSRFToken": token,
  };
}


// ==========================================================
// PLANOS DISPONIVEIS
// ==========================================================

export async function getAvailablePlans():
  Promise<AvailablePlan[]> {

  const response =
    await fetch(
      `${API_URL}/api/billing/plans/`,
      {
        method:
          "GET",

        credentials:
          "include",

        headers: {
          Accept:
            "application/json",
        },

        cache:
          "no-store",
      }
    );

  const data =
    await parseResponse<
      | AvailablePlan[]
      | {
          results: AvailablePlan[];
        }
    >(
      response
    );

  if (
    Array.isArray(data)
  ) {
    return data;
  }

  return data.results;
}


// ==========================================================
// GET ASSINATURA ATUAL
// ==========================================================

export async function getCurrentSubscription():
  Promise<ClientSubscription> {

  const response =
    await fetch(
      `${API_URL}/api/billing/subscription/`,
      {
        method:
          "GET",

        credentials:
          "include",

        headers: {
          Accept:
            "application/json",
        },

        cache:
          "no-store",
      }
    );

  return parseResponse<ClientSubscription>(
    response
  );
}


// ==========================================================
// CHECKOUT DE ASSINATURA
// ==========================================================

export async function createSubscriptionCheckout(
  planId: string
): Promise<SubscriptionCheckoutResponse> {

  await ensureCsrfCookie();

  const response =
    await fetch(
      `${API_URL}/api/billing/checkout/subscription/`,
      {
        method:
          "POST",

        credentials:
          "include",

        headers: {
          Accept:
            "application/json",

          "Content-Type":
            "application/json",

          ...getCsrfHeaders(),
        },

        body:
          JSON.stringify({
            plan_id:
              planId,
          }),
      }
    );

  return parseResponse<SubscriptionCheckoutResponse>(
    response
  );
}


export async function cancelSubscription():
  Promise<ClientSubscription> {

  await ensureCsrfCookie();

  const response =
    await fetch(
      `${API_URL}/api/billing/subscription/cancel/`,
      {
        method:
          "POST",

        credentials:
          "include",

        headers: {
          Accept:
            "application/json",

          "Content-Type":
            "application/json",

          ...getCsrfHeaders(),
        },

        body:
          JSON.stringify({}),
      }
    );

  return parseResponse<ClientSubscription>(
    response
  );
}


export async function resumeSubscription():
  Promise<ClientSubscription> {

  await ensureCsrfCookie();

  const response =
    await fetch(
      `${API_URL}/api/billing/subscription/resume/`,
      {
        method:
          "POST",

        credentials:
          "include",

        headers: {
          Accept:
            "application/json",

          "Content-Type":
            "application/json",

          ...getCsrfHeaders(),
        },

        body:
          JSON.stringify({}),
      }
    );

  return parseResponse<ClientSubscription>(
    response
  );
}


// ==========================================================
// PACOTES DE CRÉDITO
// ==========================================================

export async function getCreditPackages():
  Promise<CreditPackage[]> {

  const response =
    await fetch(
      `${API_URL}/api/billing/credit-packages/`,
      {
        method:
          "GET",

        credentials:
          "include",

        headers: {
          Accept:
            "application/json",
        },

        cache:
          "no-store",
      }
    );

  const data =
    await parseResponse<
      | CreditPackage[]
      | {
          results: CreditPackage[];
        }
    >(
      response
    );

  if (
    Array.isArray(data)
  ) {
    return data;
  }

  return data.results;
}


export async function createCreditCheckout(
  packageId: string
): Promise<CreditCheckoutResponse> {

  await ensureCsrfCookie();

  const response =
    await fetch(
      `${API_URL}/api/billing/checkout/credits/`,
      {
        method:
          "POST",

        credentials:
          "include",

        headers: {
          Accept:
            "application/json",

          "Content-Type":
            "application/json",

          ...getCsrfHeaders(),
        },

        body:
          JSON.stringify({
            package_id:
              packageId,
          }),
      }
    );

  return parseResponse<CreditCheckoutResponse>(
    response
  );
}


export async function getCreditPurchaseBySession(
  sessionId: string
): Promise<CreditPurchase> {

  const response =
    await fetch(
      `${API_URL}/api/billing/credit-purchases/by-session/${encodeURIComponent(sessionId)}/`,
      {
        method:
          "GET",

        credentials:
          "include",

        headers: {
          Accept:
            "application/json",
        },

        cache:
          "no-store",
      }
    );

  return parseResponse<CreditPurchase>(
    response
  );
}


export async function cancelCreditPurchase(
  purchaseId: string
): Promise<CreditPurchase> {

  await ensureCsrfCookie();

  const response =
    await fetch(
      `${API_URL}/api/billing/credit-purchases/${purchaseId}/cancel/`,
      {
        method:
          "POST",

        credentials:
          "include",

        headers: {
          Accept:
            "application/json",

          "Content-Type":
            "application/json",

          ...getCsrfHeaders(),
        },

        body:
          JSON.stringify({}),
      }
    );

  return parseResponse<CreditPurchase>(
    response
  );
}

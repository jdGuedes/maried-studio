import {
  ensureCsrfCookie,
} from "@/lib/api";


// ==========================================================
// MARIED STUDIO
// ASSINATURA DO CLIENTE
// ==========================================================

const API_URL =
  process.env.NEXT_PUBLIC_API_URL ??
  "http://localhost:8000";


// ==========================================================
// TIPOS
// ==========================================================

export type ClientSubscriptionPlan = {
  id: string;

  name: string;

  credits_per_cycle: number;

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

  grace_until: string | null;

  days_remaining_in_grace: number | null;
};


export function canOperateStudioFromSubscription(
  subscription:
    ClientSubscription | null
) {
  return (
    subscription?.operational_status ===
      "ACTIVE" ||
    subscription?.operational_status ===
      "GRACE"
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

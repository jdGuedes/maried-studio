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

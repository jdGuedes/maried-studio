// ==========================================================
// MARIED STUDIO
// CARTEIRA DE CRÉDITOS
// ==========================================================

const API_URL =
  process.env.NEXT_PUBLIC_API_URL ??
  "http://localhost:8000";


// ==========================================================
// TIPOS
// ==========================================================

export type CreditWallet = {
  id: string;

  balance: number;

  reserved_balance: number;

  available_balance: number;

  created_at: string;

  updated_at: string;
};


// ==========================================================
// ERRO DA API
// ==========================================================

type ApiErrorData = {
  detail?: string;

  [key: string]: unknown;
};


export class CreditWalletApiError
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
      "CreditWalletApiError";

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


  if (
    !response.ok
  ) {

    const errorData =
      data &&
      typeof data ===
        "object"
        ? (
            data as
              ApiErrorData
          )
        : null;


    const message =
      errorData?.detail ??
      `Erro ao consultar créditos (${response.status}).`;


    throw new CreditWalletApiError(
      message,
      response.status,
      errorData
    );

  }


  return data as T;
}


// ==========================================================
// GET DA CARTEIRA
// ==========================================================

export async function getCreditWallet():
  Promise<CreditWallet> {

  const response =
    await fetch(
      `${API_URL}/api/credits/wallet/`,
      {
        method:
          "GET",

        credentials:
          "include",

        headers: {
          Accept:
            "application/json",
        },

        // O saldo financeiro não deve
        // ficar preso em cache antigo.
        cache:
          "no-store",
      }
    );


  return parseResponse<CreditWallet>(
    response
  );
}
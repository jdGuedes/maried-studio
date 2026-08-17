const API_URL =
  process.env.NEXT_PUBLIC_API_URL ??
  "http://localhost:8000";


// ==========================================================
// TIPOS
// ==========================================================

export type DashboardPeriod = {
  count: number;

  start_date: string;

  end_date: string;
};


export type DashboardRecentGeneration = {
  id: string;

  product_id: string;

  product_name: string;

  category: string;

  mode: string;

  mode_label: string;

  style_name: string | null;

  image_url: string | null;

  created_at: string;
};


export type DashboardData = {
  available_credits: number;

  products: DashboardPeriod;

  generations: DashboardPeriod;

  recent_generations:
    DashboardRecentGeneration[];
};


// ==========================================================
// FILTROS
// ==========================================================

export type DashboardFilters = {
  generationStartDate?:
    string | null;

  generationEndDate?:
    string | null;

  productStartDate?:
    string | null;

  productEndDate?:
    string | null;
};


// ==========================================================
// ERRO
// ==========================================================

type ApiErrorData = {
  detail?: string;

  filter?: string;

  [key: string]:
    unknown;
};


export class DashboardApiError
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
    super(
      message
    );

    this.name =
      "DashboardApiError";

    this.status =
      status;

    this.data =
      data;
  }
}


// ==========================================================
// PARSE
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

    data =
      null;

  }


  if (
    !response.ok
  ) {

    const errorData =
      data &&
      typeof data ===
        "object"
        ? data as ApiErrorData
        : null;


    const message =
      errorData?.detail ??
      `Erro ao carregar dashboard (${response.status}).`;


    throw new DashboardApiError(
      message,
      response.status,
      errorData
    );
  }


  return data as T;
}


// ==========================================================
// DASHBOARD
// ==========================================================

export async function getDashboard(
  filters:
    DashboardFilters = {}
): Promise<DashboardData> {

  const params =
    new URLSearchParams();


  // ========================================================
  // CRIAÇÕES
  // ========================================================

  if (
    filters
      .generationStartDate
  ) {
    params.set(
      "generation_start_date",
      filters
        .generationStartDate
    );
  }


  if (
    filters
      .generationEndDate
  ) {
    params.set(
      "generation_end_date",
      filters
        .generationEndDate
    );
  }


  // ========================================================
  // PEÇAS
  // ========================================================

  if (
    filters
      .productStartDate
  ) {
    params.set(
      "product_start_date",
      filters
        .productStartDate
    );
  }


  if (
    filters
      .productEndDate
  ) {
    params.set(
      "product_end_date",
      filters
        .productEndDate
    );
  }


  const query =
    params.toString();


  const url =
    query
      ? `${API_URL}/api/studio/dashboard/?${query}`
      : `${API_URL}/api/studio/dashboard/`;


  const response =
    await fetch(
      url,
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


  return parseResponse<DashboardData>(
    response
  );
}
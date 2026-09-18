import {
  type PaginatedResponse,
} from "@/lib/pagination";

import {
  API_URL,
} from "@/lib/api-url";


// ==========================================================
// TIPOS
// ==========================================================

export type Generation = {
  id: string;

  product_id: string;
  product_name: string;

  category: string;
  category_label: string;

  mode: string;
  mode_label: string;

  status: string;

  scene_template: string | null;
  scene_template_name: string | null;

  model_reference: string | null;
  model_reference_name: string | null;

  image_url: string | null;
  generated_image_id: string | null;

  created_at: string;
  started_at: string | null;
  completed_at: string | null;
};


export type GenerationListResponse =
  PaginatedResponse<Generation>;


export type GenerationFilters = {
  q?: string;

  mode?: string;

  status?: string;

  startDate?: string;

  endDate?: string;

  page?: number;
};


// ==========================================================
// ERRO
// ==========================================================

type ApiErrorData = {
  detail?: string;

  [key: string]: unknown;
};


// ==========================================================
// CSRF
// ==========================================================

function getCsrfToken():
  string {

  if (
    typeof document ===
    "undefined"
  ) {
    return "";
  }


  const cookie =
    document.cookie
      .split("; ")
      .find(
        (
          row
        ) =>
          row.startsWith(
            "csrftoken="
          )
      );


  if (
    !cookie
  ) {
    return "";
  }


  return decodeURIComponent(
    cookie.substring(
      "csrftoken=".length
    )
  );
}


export class GenerationsApiError extends Error {
  status: number;

  data: ApiErrorData | null;


  constructor(
    message: string,
    status: number,
    data: ApiErrorData | null = null
  ) {
    super(message);

    this.name =
      "GenerationsApiError";

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
  let data: unknown = null;

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
            data as ApiErrorData
          )
        : null;


    const message =
      errorData?.detail ??
      `Erro na API (${response.status}).`;


    throw new GenerationsApiError(
      message,
      response.status,
      errorData
    );
  }


  return data as T;
}


// ==========================================================
// LISTAR GERAÇÕES
// ==========================================================

export async function getGenerations(
  filters: GenerationFilters = {}
): Promise<GenerationListResponse> {
  const params =
    new URLSearchParams();


  if (filters.q?.trim()) {
    params.set(
      "q",
      filters.q.trim()
    );
  }


  if (filters.mode) {
    params.set(
      "mode",
      filters.mode
    );
  }


  if (filters.status) {
    params.set(
      "status",
      filters.status
    );
  }


  if (filters.startDate) {
    params.set(
      "start_date",
      filters.startDate
    );
  }


  if (filters.endDate) {
    params.set(
      "end_date",
      filters.endDate
    );
  }


  if (
    filters.page &&
    filters.page > 1
  ) {
    params.set(
      "page",
      String(filters.page)
    );
  }


  const query =
    params.toString();


  const response =
    await fetch(
      query
        ? `${API_URL}/api/studio/generations/?${query}`
        : `${API_URL}/api/studio/generations/`,
      {
        method:
          "GET",

        credentials:
          "include",

        cache:
          "no-store",

        headers: {
          Accept:
            "application/json",
        },
      }
    );


  return parseResponse<GenerationListResponse>(
    response
  );
}


// ==========================================================
// DETALHE
// ==========================================================

export async function getGeneration(
  generationId: string
): Promise<Generation> {
  const response =
    await fetch(
      `${API_URL}/api/studio/generations/${generationId}/`,
      {
        method:
          "GET",

        credentials:
          "include",

        cache:
          "no-store",

        headers: {
          Accept:
            "application/json",
        },
      }
    );


  return parseResponse<Generation>(
    response
  );
}


// ==========================================================
// EXCLUIR IMAGEM GERADA
// ==========================================================

export async function deleteGeneratedImage(
  generatedImageId: string
): Promise<void> {
  const csrfToken =
    getCsrfToken();


  if (
    !csrfToken
  ) {
    throw new GenerationsApiError(
      "Token CSRF não encontrado no navegador.",
      403,
      null
    );
  }


  const response =
    await fetch(
      `${API_URL}/api/studio/images/${generatedImageId}/`,
      {
        method:
          "DELETE",

        credentials:
          "include",

        headers: {
          Accept:
            "application/json",

          "X-CSRFToken":
            csrfToken,
        },
      }
    );


  await parseResponse<void>(
    response
  );
}

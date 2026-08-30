import {
  type PaginatedResponse,
} from "@/lib/pagination";

const API_URL =
  process.env.NEXT_PUBLIC_API_URL ??
  "http://localhost:8000";


// ==========================================================
// TIPOS
// ==========================================================

export type ProductGeneration = {
  id: string;

  mode: string;

  mode_label: string;

  style_name: string | null;

  image_url: string | null;

  generated_image_id: string | null;

  created_at: string;

  completed_at: string | null;
};


export type ProductAsset = {
  id: string;

  asset_type: string;

  file?: string;

  file_url: string | null;

  mime_type: string;

  width: number | null;

  height: number | null;

  file_size: number | null;

  created_at: string;
};


export type Product = {
  id: string;

  name: string;

  category: string;

  category_label: string;

  status: string;

  original_image_url: string | null;

  assets: ProductAsset[];

  generations_count: number;

  generations: ProductGeneration[];

  created_at: string;

  updated_at: string;
};


export type ProductListResponse =
  PaginatedResponse<Product>;


export type ProductFilters = {
  q?: string;

  category?: string;

  startDate?: string;

  endDate?: string;

  page?: number;
};


// ==========================================================
// ERRO
// ==========================================================

type ApiErrorData = {
  detail?: string;

  [key: string]:
    unknown;
};


export class ProductsApiError
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
      "ProductsApiError";

    this.status =
      status;

    this.data =
      data;
  }
}


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
        ? (
            data as
              ApiErrorData
          )
        : null;


    const message =
      errorData?.detail ??
      `Erro na API (${response.status}).`;


    throw new ProductsApiError(
      message,
      response.status,
      errorData
    );
  }


  return data as T;
}


// ==========================================================
// LISTAR
// ==========================================================

export async function getProducts(
  filters:
    ProductFilters = {}
): Promise<ProductListResponse> {

  const params =
    new URLSearchParams();


  if (
    filters.q?.trim()
  ) {
    params.set(
      "q",
      filters.q.trim()
    );
  }


  if (
    filters.category
  ) {
    params.set(
      "category",
      filters.category
    );
  }


  if (
    filters.startDate
  ) {
    params.set(
      "start_date",
      filters.startDate
    );
  }


  if (
    filters.endDate
  ) {
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
      String(
        filters.page
      )
    );
  }


  const query =
    params.toString();


  const response =
    await fetch(
      query
        ? `${API_URL}/api/products/?${query}`
        : `${API_URL}/api/products/`,
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


  const data =
    await parseResponse<
      ProductListResponse
    >(
      response
    );


  if (
    Array.isArray(
      data
    )
  ) {
    return {
      count:
        data.length,
      next:
        null,
      previous:
        null,
      results:
        data,
    };
  }


  return data;
}


// ==========================================================
// DETALHE
// ==========================================================

export async function getProduct(
  productId: string
): Promise<Product> {

  const response =
    await fetch(
      `${API_URL}/api/products/${productId}/`,
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


  return parseResponse<Product>(
    response
  );
}


// ==========================================================
// RENOMEAR
// ==========================================================

export async function renameProduct(
  productId: string,
  name: string
): Promise<Product> {

  const csrfToken =
    getCsrfToken();


  console.log(
    "MARIED STUDIO - CSRF RENAME:",
    {
      present:
        Boolean(
          csrfToken
        ),

      length:
        csrfToken.length,
    }
  );


  if (
    !csrfToken
  ) {
    throw new ProductsApiError(
      "Token CSRF não encontrado no navegador.",
      403,
      null
    );
  }


  const response =
    await fetch(
      `${API_URL}/api/products/${productId}/rename/`,
      {
        method:
          "PATCH",

        credentials:
          "include",

        headers: {
          Accept:
            "application/json",

          "Content-Type":
            "application/json",

          "X-CSRFToken":
            csrfToken,
        },

        body:
          JSON.stringify({
            name:
              name.trim(),
          }),
      }
    );


  return parseResponse<Product>(
    response
  );
}


// ==========================================================
// EXCLUIR
// ==========================================================

export async function deleteProduct(
  productId: string
): Promise<void> {

  const csrfToken =
    getCsrfToken();


  console.log(
    "MARIED STUDIO - CSRF DELETE:",
    {
      present:
        Boolean(
          csrfToken
        ),

      length:
        csrfToken.length,
    }
  );


  if (
    !csrfToken
  ) {
    throw new ProductsApiError(
      "Token CSRF não encontrado no navegador.",
      403,
      null
    );
  }


  const response =
    await fetch(
      `${API_URL}/api/products/${productId}/`,
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

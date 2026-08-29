import type {
  Generation,
  GenerationMode,
  ModelReference,
  Product,
  ProductCategory,
  SceneTemplate,
} from "@/types/api";

import type {
  UserProfile,
} from "@/lib/profile";


// ==========================================================
// CONFIGURAÇÃO DA API
// ==========================================================

const API_URL =
  process.env.NEXT_PUBLIC_API_URL ??
  "http://localhost:8000";


// ==========================================================
// CSRF
// ==========================================================

function getCookie(
  name: string
): string | null {
  if (
    typeof document === "undefined"
  ) {
    return null;
  }

  const cookies =
    document.cookie.split(";");

  for (const cookie of cookies) {
    const [
      key,
      ...valueParts
    ] = cookie
      .trim()
      .split("=");

    if (key === name) {
      return decodeURIComponent(
        valueParts.join("=")
      );
    }
  }

  return null;
}


function getCsrfHeaders():
  Record<string, string> {
  const csrfToken =
    getCookie("csrftoken");

  if (!csrfToken) {
    return {};
  }

  return {
    "X-CSRFToken":
      csrfToken,
  };
}


export async function ensureCsrfCookie():
  Promise<void> {
  const response =
    await fetch(
      `${API_URL}/api/accounts/csrf/`,
      {
        method:
          "GET",

        credentials:
          "include",

        cache:
          "no-store",
      }
    );

  await parseResponse<{
    detail: string;
  }>(
    response
  );
}


// ==========================================================
// ERROS
// ==========================================================

type ApiErrorData = {
  detail?: string;

  [key: string]:
    unknown;
};


export class ApiError
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
      "ApiError";

    this.status =
      status;

    this.data =
      data;
  }
}


export type LoginInput = {
  email: string;

  password: string;
};


export type LoginResponse = {
  user: UserProfile;
};


// ==========================================================
// PARSE DA RESPOSTA
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
        ? (data as ApiErrorData)
        : null;

    let message =
      errorData?.detail ??
      `Erro na API (${response.status}).`;

    if (
      errorData &&
      !errorData.detail
    ) {
      const fieldErrors =
        Object.entries(errorData)
          .map(([field, value]) => {
            const text =
              Array.isArray(value)
                ? value.join(" ")
                : String(value);

            return `${field}: ${text}`;
          })
          .join(" | ");

      if (fieldErrors) {
        message =
          fieldErrors;
      }
    }

    console.error(
      "RESPOSTA DE ERRO DA API:",
      {
        status:
          response.status,

        data:
          errorData,
      }
    );

    throw new ApiError(
      message,
      response.status,
      errorData
    );
  }

  return data as T;
}


// ==========================================================
// AUTENTICAÇÃO
// ==========================================================

export async function loginUser({
  email,
  password,
}: LoginInput):
  Promise<LoginResponse> {

  await ensureCsrfCookie();

  const response =
    await fetch(
      `${API_URL}/api/accounts/login/`,
      {
        method:
          "POST",

        credentials:
          "include",

        cache:
          "no-store",

        headers: {
          "Content-Type":
            "application/json",

          ...getCsrfHeaders(),
        },

        body:
          JSON.stringify({
            email,
            password,
          }),
      }
    );

  return parseResponse<LoginResponse>(
    response
  );
}


export async function logoutUser():
  Promise<void> {

  await ensureCsrfCookie();

  const response =
    await fetch(
      `${API_URL}/api/accounts/logout/`,
      {
        method:
          "POST",

        credentials:
          "include",

        cache:
          "no-store",

        headers: {
          "Content-Type":
            "application/json",

          ...getCsrfHeaders(),
        },

        body:
          JSON.stringify({}),
      }
    );

  await parseResponse<{
    detail: string;
  }>(
    response
  );
}


// ==========================================================
// PRODUTOS
// ==========================================================

type CreateProductInput = {
  name: string;

  category:
    ProductCategory;

  file: File;
};


export async function createProduct({
  name,
  category,
  file,
}: CreateProductInput):
  Promise<Product> {

  const formData =
    new FormData();


  formData.append(
    "name",
    name ||
      "Peça sem nome"
  );


  formData.append(
    "category",
    category
  );


  formData.append(
    "status",
    "ACTIVE"
  );


  formData.append(
    "original_image",
    file
  );


  const csrfHeaders =
    getCsrfHeaders();


  const response =
    await fetch(
      `${API_URL}/api/products/`,
      {
        method:
          "POST",

        // IMPORTANTE:
        //
        // Não definir
        // Content-Type aqui.
        //
        // O navegador cria
        // automaticamente:
        //
        // multipart/form-data;
        // boundary=...
        //
        headers:
          csrfHeaders,

        body:
          formData,

        credentials:
          "include",
      }
    );


  return parseResponse<Product>(
    response
  );
}


// ==========================================================
// TEMPLATES
// ==========================================================

type GetTemplatesInput = {
  category:
    ProductCategory;

  mode:
    GenerationMode;
};


type PaginatedTemplates = {
  count: number;

  next:
    string | null;

  previous:
    string | null;

  results:
    SceneTemplate[];
};


export async function getSceneTemplates({
  category,
  mode,
}: GetTemplatesInput):
  Promise<SceneTemplate[]> {

  const params =
    new URLSearchParams({
      category,
      mode,
    });


  const response =
    await fetch(
      `${API_URL}/api/studio/templates/?${params.toString()}`,
      {
        method:
          "GET",

        credentials:
          "include",
      }
    );


  const data =
    await parseResponse<
      | PaginatedTemplates
      | SceneTemplate[]
    >(response);


  if (
    Array.isArray(data)
  ) {
    return data;
  }


  return data.results;
}


// ==========================================================
// MODELOS
// ==========================================================

type PaginatedModelReferences = {
  count: number;

  next:
    string | null;

  previous:
    string | null;

  results:
    ModelReference[];
};


export async function getModelReferences():
  Promise<ModelReference[]> {

  const response =
    await fetch(
      `${API_URL}/api/ai/model-references/`,
      {
        method:
          "GET",

        credentials:
          "include",
      }
    );


  const data =
    await parseResponse<
      | PaginatedModelReferences
      | ModelReference[]
    >(response);


  if (
    Array.isArray(data)
  ) {
    return data;
  }


  return data.results;
}


// ==========================================================
// GERAÇÃO
// ==========================================================

type CreateGenerationInput = {
  productId:
    string;

  mode:
    GenerationMode;

  sceneTemplateId?:
    string | null;

  modelReferenceId?:
    string | null;

  idempotencyKey:
    string;
};


export async function createGeneration({
  productId,
  mode,
  sceneTemplateId,
  modelReferenceId,
  idempotencyKey,
}: CreateGenerationInput):
  Promise<Generation> {

  const csrfHeaders =
    getCsrfHeaders();


  const response =
    await fetch(
      `${API_URL}/api/studio/generations/`,
      {
        method:
          "POST",

        headers: {
          "Content-Type":
            "application/json",

          ...csrfHeaders,
        },

        credentials:
          "include",

        body:
          JSON.stringify({
            product_id:
              productId,

            mode,

            scene_template_id:
              sceneTemplateId ??
              null,

            model_reference_id:
              modelReferenceId ??
              null,

            idempotency_key:
              idempotencyKey,
          }),
      }
    );


  return parseResponse<Generation>(
    response
  );
}


// ==========================================================
// DETALHE DA GERAÇÃO
// ==========================================================

export async function getGeneration(
  generationId:
    string
): Promise<Generation> {

  const response =
    await fetch(
      `${API_URL}/api/studio/generations/${generationId}/`,
      {
        method:
          "GET",

        credentials:
          "include",
      }
    );


  return parseResponse<Generation>(
    response
  );
}

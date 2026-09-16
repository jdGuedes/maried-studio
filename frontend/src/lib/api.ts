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


function stringifyApiValue(
  value: unknown
): string {
  if (
    Array.isArray(value)
  ) {
    return value
      .map(stringifyApiValue)
      .filter(Boolean)
      .join(" ");
  }

  if (
    value &&
    typeof value === "object"
  ) {
    return Object.values(value)
      .map(stringifyApiValue)
      .filter(Boolean)
      .join(" ");
  }

  return String(
    value ?? ""
  );
}


export function humanizePasswordApiError(
  data:
    ApiErrorData | null,
  fallback: string
): string {
  const rawMessage =
    data?.detail ??
    (
      data
        ? Object.values(data)
            .map(stringifyApiValue)
            .filter(Boolean)
            .join(" ")
        : ""
    );

  const message =
    rawMessage
      .replace(
        /\b(new_password|new_password_confirm|current_password|non_field_errors|detail)\s*:\s*/gi,
        ""
      )
      .trim();

  if (!message) {
    return fallback;
  }

  const lower =
    message.toLowerCase();

  if (
    lower.includes("muito comum") ||
    lower.includes("too common")
  ) {
    return "Esta senha é muito comum. Escolha uma combinação menos previsível.";
  }

  if (
    lower.includes("muito curta") ||
    lower.includes("too short")
  ) {
    return "Use uma senha mais longa.";
  }

  if (
    lower.includes("inteiramente num") ||
    lower.includes("entirely numeric")
  ) {
    return "Evite usar somente números.";
  }

  if (
    lower.includes("muito parecida") ||
    lower.includes("similar")
  ) {
    return "Escolha uma senha menos parecida com seus dados pessoais.";
  }

  return message;
}


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


export type PasswordResetRequestInput = {
  email: string;
};


export type PasswordResetConfirmInput = {
  uid: string;

  token: string;

  newPassword: string;

  newPasswordConfirm: string;
};


export type AccountRecoveryStatus = {
  recovery_configured: boolean;

  recovery_key_configured: boolean;

  security_questions_configured: boolean;

  configured_at: string | null;

  key_rotated_at: string | null;

  temporarily_blocked: boolean;

  blocked_until: string | null;
};


export type AccountRecoverySetupInput = {
  question1: string;

  answer1: string;

  question2: string;

  answer2: string;
};


export type AccountRecoverySetupResponse = {
  recovery_key: string;

  status: AccountRecoveryStatus;
};


export type AccountRecoveryVerifyKeyInput = {
  email: string;

  recoveryKey: string;
};


export type AccountRecoveryAuthorization = {
  recovery_token: string;

  expires_in: number;
};


export type AccountRecoveryQuestion = {
  id: string;

  question: string;
};


export type AccountRecoveryQuestionsResponse = {
  challenge_id: string;

  questions: AccountRecoveryQuestion[];

  expires_in: number;
};


export type AccountRecoveryQuestionsVerifyInput = {
  challengeId: string;

  answers: Array<{
    questionId: string;

    answer: string;
  }>;
};


export type AccountRecoveryResetPasswordInput = {
  recoveryToken: string;

  newPassword: string;

  newPasswordConfirm: string;
};


export type AccountRecoveryResetPasswordResponse = {
  detail: string;

  recovery_key: string;
};


export type PasswordChangeInput = {
  currentPassword: string;

  newPassword: string;

  newPasswordConfirm: string;
};


export type AccountRecoveryRotateKeyInput = {
  currentPassword: string;
};


export type AccountRecoveryRotateKeyResponse = {
  recovery_key: string;

  status: AccountRecoveryStatus;
};


export type AccountRecoveryChangeQuestionsInput = {
  currentPassword: string;

  question1: string;

  answer1: string;

  question2: string;

  answer2: string;
};


export type AccountRecoveryChangeQuestionsResponse = {
  recovery_key: string;

  status: AccountRecoveryStatus;
};


type GenerationListItem = {
  id: string;

  status: Generation["status"];
};


type GenerationListResponse = {
  count: number;

  next:
    string | null;

  previous:
    string | null;

  results:
    GenerationListItem[];
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


async function parsePasswordResponse<T>(
  response: Response,
  fallback: string
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

    throw new ApiError(
      humanizePasswordApiError(
        errorData,
        fallback
      ),
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


export async function requestPasswordReset({
  email,
}: PasswordResetRequestInput):
  Promise<{
    detail: string;
  }> {

  await ensureCsrfCookie();

  const response =
    await fetch(
      `${API_URL}/api/accounts/password-reset/request/`,
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
          }),
      }
    );

  return parseResponse<{
    detail: string;
  }>(
    response
  );
}


export async function confirmPasswordReset({
  uid,
  token,
  newPassword,
  newPasswordConfirm,
}: PasswordResetConfirmInput):
  Promise<{
    detail: string;
  }> {

  await ensureCsrfCookie();

  const response =
    await fetch(
      `${API_URL}/api/accounts/password-reset/confirm/`,
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
            uid,
            token,
            new_password:
              newPassword,
            new_password_confirm:
              newPasswordConfirm,
          }),
      }
    );

  return parsePasswordResponse<{
    detail: string;
  }>(
    response,
    "Não foi possível alterar sua senha agora. Tente novamente."
  );
}


export async function getAccountRecoveryStatus():
  Promise<AccountRecoveryStatus> {
  const response =
    await fetch(
      `${API_URL}/api/accounts/recovery/status/`,
      {
        method:
          "GET",

        credentials:
          "include",

        cache:
          "no-store",
      }
    );

  return parseResponse<AccountRecoveryStatus>(
    response
  );
}

export async function setupAccountRecovery({
  question1,
  answer1,
  question2,
  answer2,
}: AccountRecoverySetupInput):
  Promise<AccountRecoverySetupResponse> {

  await ensureCsrfCookie();

  const response =
    await fetch(
      `${API_URL}/api/accounts/recovery/setup/`,
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
            question_1:
              question1,
            answer_1:
              answer1,
            question_2:
              question2,
            answer_2:
              answer2,
          }),
      }
    );

  return parseResponse<AccountRecoverySetupResponse>(
    response
  );
}


export async function verifyAccountRecoveryKey({
  email,
  recoveryKey,
}: AccountRecoveryVerifyKeyInput):
  Promise<AccountRecoveryAuthorization> {

  await ensureCsrfCookie();

  const response =
    await fetch(
      `${API_URL}/api/accounts/recovery/verify-key/`,
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
            recovery_key:
              recoveryKey,
          }),
      }
    );

  return parseResponse<AccountRecoveryAuthorization>(
    response
  );
}


export async function requestAccountRecoveryQuestions(
  email: string
): Promise<AccountRecoveryQuestionsResponse> {

  await ensureCsrfCookie();

  const response =
    await fetch(
      `${API_URL}/api/accounts/recovery/questions/`,
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
          }),
      }
    );

  return parseResponse<AccountRecoveryQuestionsResponse>(
    response
  );
}


export async function verifyAccountRecoveryQuestions({
  challengeId,
  answers,
}: AccountRecoveryQuestionsVerifyInput):
  Promise<AccountRecoveryAuthorization> {

  await ensureCsrfCookie();

  const response =
    await fetch(
      `${API_URL}/api/accounts/recovery/questions/verify/`,
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
            challenge_id:
              challengeId,
            answers:
              answers.map(
                (
                  answer
                ) => ({
                  question_id:
                    answer.questionId,
                  answer:
                    answer.answer,
                })
              ),
          }),
      }
    );

  return parseResponse<AccountRecoveryAuthorization>(
    response
  );
}


export async function resetPasswordWithRecovery({
  recoveryToken,
  newPassword,
  newPasswordConfirm,
}: AccountRecoveryResetPasswordInput):
  Promise<AccountRecoveryResetPasswordResponse> {

  await ensureCsrfCookie();

  const response =
    await fetch(
      `${API_URL}/api/accounts/recovery/reset-password/`,
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
            recovery_token:
              recoveryToken,
            new_password:
              newPassword,
            new_password_confirm:
              newPasswordConfirm,
          }),
      }
    );

  return parsePasswordResponse<AccountRecoveryResetPasswordResponse>(
    response,
    "Não foi possível alterar sua senha agora. Tente novamente."
  );
}


export async function changePassword({
  currentPassword,
  newPassword,
  newPasswordConfirm,
}: PasswordChangeInput):
  Promise<{
    detail: string;
  }> {

  await ensureCsrfCookie();

  const response =
    await fetch(
      `${API_URL}/api/accounts/password/change/`,
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
            current_password:
              currentPassword,
            new_password:
              newPassword,
            new_password_confirm:
              newPasswordConfirm,
          }),
      }
    );

  return parsePasswordResponse<{
    detail: string;
  }>(
    response,
    "Não foi possível alterar sua senha agora. Tente novamente."
  );
}


export async function rotateRecoveryKey({
  currentPassword,
}: AccountRecoveryRotateKeyInput):
  Promise<AccountRecoveryRotateKeyResponse> {

  await ensureCsrfCookie();

  const response =
    await fetch(
      `${API_URL}/api/accounts/recovery/rotate-key/`,
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
            current_password:
              currentPassword,
          }),
      }
    );

  return parsePasswordResponse<AccountRecoveryRotateKeyResponse>(
    response,
    "Não foi possível gerar uma nova chave agora. Tente novamente."
  );
}


export async function changeSecurityQuestions({
  currentPassword,
  question1,
  answer1,
  question2,
  answer2,
}: AccountRecoveryChangeQuestionsInput):
  Promise<AccountRecoveryChangeQuestionsResponse> {

  await ensureCsrfCookie();

  const response =
    await fetch(
      `${API_URL}/api/accounts/recovery/change-questions/`,
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
            current_password:
              currentPassword,
            question_1:
              question1,
            answer_1:
              answer1,
            question_2:
              question2,
            answer_2:
              answer2,
          }),
      }
    );

  return parsePasswordResponse<AccountRecoveryChangeQuestionsResponse>(
    response,
    "Não foi possível alterar as perguntas agora. Tente novamente."
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


export async function getActiveGeneration():
  Promise<Generation | null> {

  for (const generationStatus of [
    "PROCESSING",
    "CREDIT_RESERVED",
  ] as const) {
    const params =
      new URLSearchParams({
        status:
          generationStatus,
      });

    const response =
      await fetch(
        `${API_URL}/api/studio/generations/?${params.toString()}`,
        {
          method:
            "GET",

          credentials:
            "include",

          cache:
            "no-store",
        }
      );

    const data =
      await parseResponse<GenerationListResponse>(
        response
      );

    const activeGeneration =
      data.results[0];

    if (
      activeGeneration
    ) {
      return getGeneration(
        activeGeneration.id
      );
    }
  }

  return null;
}


// ==========================================================
// SUPERADMIN
// ==========================================================

type PaginatedResponse<T> = {
  count: number;

  next:
    string | null;

  previous:
    string | null;

  results:
    T[];
};


function unpackResults<T>(
  data:
    | PaginatedResponse<T>
    | T[]
): T[] {
  if (
    Array.isArray(data)
  ) {
    return data;
  }

  return data.results;
}


export type SuperAdminSummary = {
  organizations: number;
  active_organizations: number;
  users: number;
  plans: number;
  subscriptions: number;
  operational_active_subscriptions: number;
  operational_grace_subscriptions: number;
  operational_blocked_subscriptions: number;
  credit_wallets: number;
  generations: number;
  failed_generations: number;
};


export type SuperAdminPlan = {
  id: string;
  name: string;
  slug: string;
  description: string;
  price: string;
  billing_cycle: string;
  credits_per_cycle: number;
  extra_credit_limit_per_cycle: number;
  is_active: boolean;
  sort_order: number;
  stripe_product_id?: string | null;
  stripe_price_id?: string | null;
  stripe_synced_at?: string | null;
  stripe_sync_error?: string;
  stripe_ready_for_checkout?: boolean;
  stripe_sync_status?:
    | "SYNCED"
    | "PENDING"
    | "ERROR";
};


export type SuperAdminClientUser = {
  id: number;
  email: string;
  name: string;
  role?: string;
  role_label?: string;
  organization?: string | null;
  organization_name?: string | null;
  is_active: boolean;
  is_staff?: boolean;
  is_superuser?: boolean;
  recovery_security?: SuperAdminRecoverySecurity;
};


export type SuperAdminRecoverySecurity = {
  recovery_configured: boolean;

  recovery_key_configured: boolean;

  security_questions_configured: boolean;

  configured_at: string | null;

  key_rotated_at: string | null;

  temporarily_blocked: boolean;

  blocked_until: string | null;
};


export type SuperAdminClientSubscription = {
  id?: string;
  organization?: string;
  organization_name?: string;
  plan?: string;
  plan_name?: string;
  status?: string;
  price_snapshot?: string;
  credits_snapshot?: number;
  current_period_start?: string | null;
  current_period_end?: string | null;
  next_billing_at?: string | null;
  cancel_at_period_end?: boolean;
  stripe_customer_id?: string;
  stripe_subscription_id?: string | null;
  stripe_price_id?: string;
  stripe_status?: string;
  last_processed_stripe_invoice_id?: string | null;
  operational_status: string;
  grace_until?: string | null;
  days_remaining_in_grace?: number | null;
};


export type SuperAdminSubscription =
  SuperAdminClientSubscription & {
    id: string;
    organization: string;
    organization_name: string;
    plan: string;
    plan_name: string;
    status: string;
    price_snapshot: string;
    credits_snapshot: number;
    started_at: string | null;
    created_at: string;
    updated_at: string;
  };


export type SuperAdminClientWallet = {
  id: string;
  available_balance: number;
  total_balance?: number;
  balance?: number;
  reserved_balance: number;
  plan_balance: number;
  purchased_balance: number;
  plan_reserved_balance?: number;
  purchased_reserved_balance?: number;
};


export type SuperAdminClientListItem = {
  id: string;
  name: string;
  slug: string;
  is_active: boolean;
  user: SuperAdminClientUser | null;
  subscription: SuperAdminClientSubscription | null;
  wallet: SuperAdminClientWallet | null;
  operational_status: string;
  created_at: string;
};


export type SuperAdminAuditLog = {
  id: string;
  action: string;
  entity_type: string;
  entity_id: string;
  actor_email: string;
  organization: string | null;
  organization_name: string | null;
  metadata: Record<string, unknown>;
  created_at: string;
};


export type SuperAdminWallet = {
  id: string;
  organization: string;
  organization_name: string;
  balance: number;
  reserved_balance: number;
  plan_balance: number;
  purchased_balance: number;
  plan_reserved_balance: number;
  purchased_reserved_balance: number;
  available_balance: number;
  total_balance: number;
  created_at: string;
  updated_at: string;
};


export type SuperAdminCreditPackage = {
  id: string;
  name: string;
  slug: string;
  description: string;
  credits: number;
  price: string;
  currency: string;
  is_active: boolean;
  sort_order: number;
  stripe_product_id?: string | null;
  stripe_price_id?: string | null;
  stripe_synced_at?: string | null;
  stripe_sync_error?: string;
  stripe_ready_for_checkout?: boolean;
  stripe_sync_status?:
    | "SYNCED"
    | "PENDING"
    | "ERROR";
};


export type SuperAdminCreditPurchase = {
  id: string;
  organization: string;
  organization_name: string;
  package: string;
  package_name: string;
  subscription: string;
  plan: string;
  plan_name: string;
  status: string;
  credits_snapshot: number;
  price_snapshot: string;
  currency_snapshot: string;
  stripe_checkout_session_id?: string | null;
  stripe_payment_intent_id?: string | null;
  paid_at: string | null;
  created_at: string;
};


export type SuperAdminPaymentDispute = {
  id: string;
  organization: string;
  organization_name: string;
  stripe_dispute_reference: string;
  stripe_payment_intent_id: string;
  stripe_charge_id: string;
  stripe_customer_id: string;
  subscription_id: string | null;
  credit_purchase_id: string | null;
  origin_type: string;
  amount: number;
  currency: string;
  status: string;
  reason: string;
  evidence_due_by: string | null;
  resolved_at: string | null;
  is_blocking: boolean;
  created_at: string;
  updated_at: string;
};


export type SuperAdminGeneration = {
  id: string;
  organization: string;
  organization_name: string;
  user: number;
  user_email: string;
  product: string;
  product_name: string;
  mode: GenerationMode;
  status: string;
  failure_type: string;
  provider: string;
  model: string;
  credit_cost: number;
  retry_count: number;
  error_code: string;
  error_message: string;
  created_at: string;
  started_at: string | null;
  completed_at: string | null;
};


export type SuperAdminSceneTemplate = SceneTemplate & {
  prompt_template: string;
  generation_mode: GenerationMode;
  category: ProductCategory;
  is_active: boolean;
  created_at: string;
  updated_at: string;
};


export type SuperAdminClientDetail =
  SuperAdminClientListItem & {
    updated_at: string;
    stripe_customer_id?: string;
    subscription: SuperAdminClientSubscription;
    wallet: SuperAdminClientWallet;
    usage: {
      products_count: number;
      generations_count: number;
    };
    audit_logs: SuperAdminAuditLog[];
  };


export type CreateSuperAdminClientInput = {
  name: string;
  email: string;
  initial_password: string;
  plan_id: string;
};


export type AdjustSuperAdminCreditsInput = {
  organization_id: string;
  amount: number;
  balance_type:
    | "PLAN"
    | "PURCHASED";
  reason: string;
};


export type SuperAdminStripeReconciliation = {
  reconciled: boolean;
  applied: boolean;
  cycle_type?: string | null;
  subscription_status?: string | null;
  operational_status?: string | null;
  plan_balance?: number;
  purchased_balance?: number;
  stripe_subscription_status?: string | null;
  stripe_invoice_id?: string;
  stripe_subscription_id?: string;
  disputes_reconciled?: number;
  financial_blocked?: boolean;
  code?: string;
  detail?: string;
};


export async function getSuperAdminSummary():
  Promise<SuperAdminSummary> {
  const response =
    await fetch(
      `${API_URL}/api/superadmin/summary/`,
      {
        method:
          "GET",

        credentials:
          "include",

        cache:
          "no-store",
      }
    );

  return parseResponse<SuperAdminSummary>(
    response
  );
}


export async function getSuperAdminClients():
  Promise<SuperAdminClientListItem[]> {
  const response =
    await fetch(
      `${API_URL}/api/superadmin/clients/`,
      {
        method:
          "GET",

        credentials:
          "include",

        cache:
          "no-store",
      }
    );

  const data =
    await parseResponse<
      | PaginatedResponse<SuperAdminClientListItem>
      | SuperAdminClientListItem[]
    >(response);

  return unpackResults(data);
}


export async function getSuperAdminClient(
  clientId: string
): Promise<SuperAdminClientDetail> {
  const response =
    await fetch(
      `${API_URL}/api/superadmin/clients/${clientId}/`,
      {
        method:
          "GET",

        credentials:
          "include",

        cache:
          "no-store",
      }
    );

  return parseResponse<SuperAdminClientDetail>(
    response
  );
}


export async function getSuperAdminPlans():
  Promise<SuperAdminPlan[]> {
  const response =
    await fetch(
      `${API_URL}/api/superadmin/plans/`,
      {
        method:
          "GET",

        credentials:
          "include",

        cache:
          "no-store",
      }
    );

  const data =
    await parseResponse<
      | PaginatedResponse<SuperAdminPlan>
      | SuperAdminPlan[]
    >(response);

  return unpackResults(data);
}


export async function createSuperAdminPlan(
  input: Omit<SuperAdminPlan, "id">
): Promise<SuperAdminPlan> {
  await ensureCsrfCookie();

  const response =
    await fetch(
      `${API_URL}/api/superadmin/plans/`,
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
          JSON.stringify(input),
      }
    );

  return parseResponse<SuperAdminPlan>(
    response
  );
}


export async function updateSuperAdminPlan(
  planId: string,
  input: Partial<Omit<SuperAdminPlan, "id">>
): Promise<SuperAdminPlan> {
  await ensureCsrfCookie();

  const response =
    await fetch(
      `${API_URL}/api/superadmin/plans/${planId}/`,
      {
        method:
          "PATCH",

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
          JSON.stringify(input),
      }
    );

  return parseResponse<SuperAdminPlan>(
    response
  );
}


export async function syncSuperAdminPlanStripe(
  planId: string
): Promise<SuperAdminPlan> {
  await ensureCsrfCookie();

  const response =
    await fetch(
      `${API_URL}/api/superadmin/plans/${planId}/stripe-sync/`,
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

  return parseResponse<SuperAdminPlan>(
    response
  );
}


export async function getSuperAdminCreditPackages():
  Promise<SuperAdminCreditPackage[]> {
  const response =
    await fetch(
      `${API_URL}/api/superadmin/credit-packages/`,
      {
        method:
          "GET",

        credentials:
          "include",

        cache:
          "no-store",
      }
    );

  const data =
    await parseResponse<
      | PaginatedResponse<SuperAdminCreditPackage>
      | SuperAdminCreditPackage[]
    >(response);

  return unpackResults(data);
}


export async function createSuperAdminCreditPackage(
  input: Omit<SuperAdminCreditPackage, "id">
): Promise<SuperAdminCreditPackage> {
  await ensureCsrfCookie();

  const response =
    await fetch(
      `${API_URL}/api/superadmin/credit-packages/`,
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
          JSON.stringify(input),
      }
    );

  return parseResponse<SuperAdminCreditPackage>(
    response
  );
}


export async function updateSuperAdminCreditPackage(
  packageId: string,
  input: Partial<Omit<SuperAdminCreditPackage, "id">>
): Promise<SuperAdminCreditPackage> {
  await ensureCsrfCookie();

  const response =
    await fetch(
      `${API_URL}/api/superadmin/credit-packages/${packageId}/`,
      {
        method:
          "PATCH",

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
          JSON.stringify(input),
      }
    );

  return parseResponse<SuperAdminCreditPackage>(
    response
  );
}


export async function syncSuperAdminCreditPackageStripe(
  packageId: string
): Promise<SuperAdminCreditPackage> {
  await ensureCsrfCookie();

  const response =
    await fetch(
      `${API_URL}/api/superadmin/credit-packages/${packageId}/stripe-sync/`,
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

  return parseResponse<SuperAdminCreditPackage>(
    response
  );
}


export async function createSuperAdminClient(
  input: CreateSuperAdminClientInput
): Promise<SuperAdminClientDetail> {
  await ensureCsrfCookie();

  const response =
    await fetch(
      `${API_URL}/api/superadmin/clients/`,
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
          JSON.stringify(input),
      }
    );

  return parseResponse<SuperAdminClientDetail>(
    response
  );
}


export async function updateSuperAdminOrganization(
  organizationId: string,
  input: {
    name?: string;
    is_active?: boolean;
  }
): Promise<unknown> {
  await ensureCsrfCookie();

  const response =
    await fetch(
      `${API_URL}/api/superadmin/organizations/${organizationId}/`,
      {
        method:
          "PATCH",

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
          JSON.stringify(input),
      }
    );

  return parseResponse<unknown>(
    response
  );
}


export async function updateSuperAdminUser(
  userId: number,
  input: {
    name?: string;
    is_active?: boolean;
  }
): Promise<unknown> {
  await ensureCsrfCookie();

  const response =
    await fetch(
      `${API_URL}/api/superadmin/accounts/${userId}/`,
      {
        method:
          "PATCH",

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
          JSON.stringify(input),
      }
    );

  return parseResponse<unknown>(
    response
  );
}


export async function activateSuperAdminSubscription(
  organizationId: string,
  planId: string
): Promise<SuperAdminClientDetail> {
  await ensureCsrfCookie();

  const response =
    await fetch(
      `${API_URL}/api/superadmin/clients/${organizationId}/activate-subscription/`,
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
            plan_id:
              planId,
          }),
      }
    );

  return parseResponse<SuperAdminClientDetail>(
    response
  );
}


export async function reconcileSuperAdminClientStripe(
  organizationId: string
): Promise<SuperAdminStripeReconciliation> {
  await ensureCsrfCookie();

  const response =
    await fetch(
      `${API_URL}/api/superadmin/clients/${organizationId}/stripe-reconcile/`,
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

  return parseResponse<SuperAdminStripeReconciliation>(
    response
  );
}


export async function renewSuperAdminSubscription(
  subscriptionId: string
): Promise<SuperAdminClientSubscription> {
  await ensureCsrfCookie();

  const response =
    await fetch(
      `${API_URL}/api/superadmin/subscriptions/${subscriptionId}/renew/`,
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

  return parseResponse<SuperAdminClientSubscription>(
    response
  );
}


export async function adjustSuperAdminCredits(
  input: AdjustSuperAdminCreditsInput
): Promise<SuperAdminClientWallet> {
  await ensureCsrfCookie();

  const response =
    await fetch(
      `${API_URL}/api/superadmin/credit-adjustments/`,
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
          JSON.stringify(input),
      }
    );

  return parseResponse<SuperAdminClientWallet>(
    response
  );
}


export async function getSuperAdminSubscriptions():
  Promise<SuperAdminSubscription[]> {
  const response =
    await fetch(
      `${API_URL}/api/superadmin/subscriptions/`,
      {
        method:
          "GET",

        credentials:
          "include",

        cache:
          "no-store",
      }
    );

  const data =
    await parseResponse<
      | PaginatedResponse<SuperAdminSubscription>
      | SuperAdminSubscription[]
    >(response);

  return unpackResults(data);
}


export async function getSuperAdminWallets():
  Promise<SuperAdminWallet[]> {
  const response =
    await fetch(
      `${API_URL}/api/superadmin/credit-wallets/`,
      {
        method:
          "GET",

        credentials:
          "include",

        cache:
          "no-store",
      }
    );

  const data =
    await parseResponse<
      | PaginatedResponse<SuperAdminWallet>
      | SuperAdminWallet[]
    >(response);

  return unpackResults(data);
}


export async function getSuperAdminCreditPurchases():
  Promise<SuperAdminCreditPurchase[]> {
  const response =
    await fetch(
      `${API_URL}/api/superadmin/credit-purchases/`,
      {
        method:
          "GET",

        credentials:
          "include",

        cache:
          "no-store",
      }
    );

  const data =
    await parseResponse<
      | PaginatedResponse<SuperAdminCreditPurchase>
      | SuperAdminCreditPurchase[]
    >(response);

  return unpackResults(data);
}


export async function getSuperAdminPaymentDisputes():
  Promise<SuperAdminPaymentDispute[]> {
  const response =
    await fetch(
      `${API_URL}/api/superadmin/financeiro/disputas/`,
      {
        method:
          "GET",

        credentials:
          "include",

        cache:
          "no-store",
      }
    );

  const data =
    await parseResponse<
      | PaginatedResponse<SuperAdminPaymentDispute>
      | SuperAdminPaymentDispute[]
    >(response);

  return unpackResults(data);
}


export async function getSuperAdminGenerations(
  statusFilter = ""
): Promise<SuperAdminGeneration[]> {
  const params =
    statusFilter
      ? `?status=${encodeURIComponent(statusFilter)}`
      : "";

  const response =
    await fetch(
      `${API_URL}/api/superadmin/generations/${params}`,
      {
        method:
          "GET",

        credentials:
          "include",

        cache:
          "no-store",
      }
    );

  const data =
    await parseResponse<
      | PaginatedResponse<SuperAdminGeneration>
      | SuperAdminGeneration[]
    >(response);

  return unpackResults(data);
}


export async function getSuperAdminGeneration(
  generationId: string
): Promise<SuperAdminGeneration> {
  const response =
    await fetch(
      `${API_URL}/api/superadmin/generations/${generationId}/`,
      {
        method:
          "GET",

        credentials:
          "include",

        cache:
          "no-store",
      }
    );

  return parseResponse<SuperAdminGeneration>(
    response
  );
}


export async function getSuperAdminSceneTemplates():
  Promise<SuperAdminSceneTemplate[]> {
  const response =
    await fetch(
      `${API_URL}/api/superadmin/scene-templates/`,
      {
        method:
          "GET",

        credentials:
          "include",

        cache:
          "no-store",
      }
    );

  const data =
    await parseResponse<
      | PaginatedResponse<SuperAdminSceneTemplate>
      | SuperAdminSceneTemplate[]
    >(response);

  return unpackResults(data);
}


export async function createSuperAdminSceneTemplate(
  input: Omit<
    SuperAdminSceneTemplate,
    | "id"
    | "preview_image"
    | "created_at"
    | "updated_at"
  >
): Promise<SuperAdminSceneTemplate> {
  await ensureCsrfCookie();

  const response =
    await fetch(
      `${API_URL}/api/superadmin/scene-templates/`,
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
          JSON.stringify(input),
      }
    );

  return parseResponse<SuperAdminSceneTemplate>(
    response
  );
}


export async function updateSuperAdminSceneTemplate(
  templateId: string,
  input: Partial<
    Omit<
      SuperAdminSceneTemplate,
      | "id"
      | "preview_image"
      | "created_at"
      | "updated_at"
    >
  >
): Promise<SuperAdminSceneTemplate> {
  await ensureCsrfCookie();

  const response =
    await fetch(
      `${API_URL}/api/superadmin/scene-templates/${templateId}/`,
      {
        method:
          "PATCH",

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
          JSON.stringify(input),
      }
    );

  return parseResponse<SuperAdminSceneTemplate>(
    response
  );
}


export async function getSuperAdminAuditLogs():
  Promise<SuperAdminAuditLog[]> {
  const response =
    await fetch(
      `${API_URL}/api/superadmin/audit-logs/`,
      {
        method:
          "GET",

        credentials:
          "include",

        cache:
          "no-store",
      }
    );

  const data =
    await parseResponse<
      | PaginatedResponse<SuperAdminAuditLog>
      | SuperAdminAuditLog[]
    >(response);

  return unpackResults(data);
}

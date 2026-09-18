import {
  API_URL,
} from "@/lib/api-url";


// ==========================================================
// TIPOS
// ==========================================================

export type ProfileOrganization = {
  id: string;

  name: string;

  slug: string;

  is_active: boolean;
};


export type UserProfile = {
  id: number | string;

  name: string;

  email: string;

  role: string;

  role_label: string;

  is_superuser: boolean;

  organization: ProfileOrganization | null;

  recovery?: AccountRecoveryStatus;

  recovery_configured?: boolean;
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


export type UpdateProfileInput = {
  name?: string;

  organization_name?: string;
};


// ==========================================================
// ERRO
// ==========================================================

type ApiErrorData = {
  detail?: string;

  [key: string]:
    unknown;
};


export class ProfileApiError
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
      "ProfileApiError";

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


    throw new ProfileApiError(
      message,
      response.status,
      errorData
    );
  }


  return data as T;
}


// ==========================================================
// GET PERFIL
// ==========================================================

export async function getProfile():
  Promise<UserProfile> {

  const response =
    await fetch(
      `${API_URL}/api/accounts/me/`,
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


  return parseResponse<UserProfile>(
    response
  );
}


// ==========================================================
// PATCH PERFIL
// ==========================================================

export async function updateProfile(
  input:
    UpdateProfileInput
): Promise<UserProfile> {

  const csrfToken =
    getCsrfToken();


  if (
    !csrfToken
  ) {
    throw new ProfileApiError(
      "Token CSRF não encontrado.",
      403,
      null
    );
  }


  const response =
    await fetch(
      `${API_URL}/api/accounts/me/`,
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
          JSON.stringify(
            input
          ),
      }
    );


  return parseResponse<UserProfile>(
    response
  );
}

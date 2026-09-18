export function getApiUrl() {
  const configured =
    process.env.NEXT_PUBLIC_API_URL
      ?.trim()
      .replace(
        /\/+$/,
        ""
      );

  if (configured) {
    return configured;
  }

  if (
    process.env.NODE_ENV ===
    "production"
  ) {
    throw new Error(
      "NEXT_PUBLIC_API_URL must be configured for production builds."
    );
  }

  return "http://localhost:8000";
}


export const API_URL =
  getApiUrl();

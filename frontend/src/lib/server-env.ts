const LOCAL_BACKEND_URL = "http://127.0.0.1:8000";

export function getServerApiBaseUrl() {
  const configuredUrl = process.env.NEXT_SERVER_API_URL?.trim();
  if (configuredUrl) {
    return configuredUrl.replace(/\/+$/, "");
  }

  if (process.env.NODE_ENV !== "production") {
    return LOCAL_BACKEND_URL;
  }

  throw new Error("NEXT_SERVER_API_URL must be set in production.");
}

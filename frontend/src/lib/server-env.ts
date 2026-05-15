const LOCAL_BACKEND_URL = "http://127.0.0.1:8000";
const PRODUCTION_BACKEND_FALLBACKS = [
  "http://127.0.0.1:8000",
  "http://127.0.0.1:8020"
];

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

export function getServerApiBaseUrls() {
  const primaryUrl = getServerApiBaseUrl();
  const urls = [primaryUrl];

  if (process.env.NODE_ENV === "production") {
    urls.push(...PRODUCTION_BACKEND_FALLBACKS);
  }

  return Array.from(new Set(urls.map((url) => url.replace(/\/+$/, ""))));
}

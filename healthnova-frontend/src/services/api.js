import axios from "axios";

function resolveApiBaseUrl() {
  const envUrl = `${import.meta.env.VITE_API_BASE_URL || ""}`.trim();
  if (envUrl) return envUrl;

  if (typeof window === "undefined") {
    return "http://127.0.0.1:8000";
  }

  const hostname = `${window.location.hostname || ""}`.trim();
  const isLocalHost =
    hostname === "localhost" ||
    hostname === "127.0.0.1" ||
    hostname === "::1" ||
    /^10\.\d+\.\d+\.\d+$/.test(hostname) ||
    /^192\.168\.\d+\.\d+$/.test(hostname) ||
    /^172\.(1[6-9]|2\d|3[0-1])\.\d+\.\d+$/.test(hostname);

  if (isLocalHost && hostname) {
    return `http://${hostname}:8000`;
  }

  return "http://127.0.0.1:8000";
}

const API_BASE_URL = resolveApiBaseUrl();

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
});

function shouldRetryRequest(error) {
  if (!error) return false;
  if (error.code === "ECONNABORTED") return true;
  if (error.message === "Network Error" || !error.response) return true;
  const status = Number(error?.response?.status || 0);
  return status >= 500 && status < 600;
}

async function requestWithRetry(requestFn, options = {}) {
  const retries = Math.max(0, Number(options.retries ?? 1));
  const retryDelayMs = Math.max(0, Number(options.retryDelayMs ?? 1200));
  let attempt = 0;
  let lastError;

  while (attempt <= retries) {
    try {
      return await requestFn();
    } catch (error) {
      lastError = error;
      if (attempt >= retries || !shouldRetryRequest(error)) {
        throw error;
      }
      await new Promise((resolve) => window.setTimeout(resolve, retryDelayMs * (attempt + 1)));
      attempt += 1;
    }
  }

  throw lastError;
}

async function backendHealthOk() {
  try {
    const { data } = await api.get("/health", { timeout: 4000 });
    return data?.status === "ok";
  } catch {
    return false;
  }
}

async function normalizeApiError(error, action) {
  const rawErrorText = JSON.stringify(error?.response?.data || error?.message || "");

  if (action === "Hindi translation") {
    if (/API[_ ]KEY[_ ]INVALID/i.test(rawErrorText)) {
      return new Error("Hindi translation is temporarily unavailable because the translation service key is invalid.");
    }
    if (/API key expired/i.test(rawErrorText)) {
      return new Error("Hindi translation is temporarily unavailable because the translation service key has expired.");
    }
    if (/quota|rate limit|resource exhausted|billing/i.test(rawErrorText)) {
      return new Error("Hindi translation is temporarily unavailable because the translation service quota or rate limit was reached.");
    }
  }

  if (error?.response?.data?.error) {
    return new Error(error.response.data.error);
  }
  if (typeof error?.response?.data?.detail === "string") {
    return new Error(error.response.data.detail);
  }
  if (Array.isArray(error?.response?.data?.detail)) {
    const firstDetail = error.response.data.detail[0];
    if (typeof firstDetail?.msg === "string") {
      return new Error(firstDetail.msg);
    }
  }
  if (error?.code === "ECONNABORTED") {
    if (action === "Report analysis") {
      return new Error(
        "Report analysis timed out. Large PDFs or image OCR can take longer than expected. Try again with a clearer file, or wait and retry after the backend finishes loading."
      );
    }
    return new Error(`${action} timed out. The backend took too long to respond.`);
  }
  if (error?.message === "Network Error" || !error?.response) {
    const healthy = await backendHealthOk();
    if (healthy) {
      return new Error(`${action} could not finish because the backend was busy or restarted during the request. Please try again.`);
    }
    return new Error(
      `Cannot reach the backend at ${API_BASE_URL}. Start it with "npm run dev:full" from healthnova-frontend or run "..\\start-healthnova.ps1", then try again.`
    );
  }
  return new Error(error?.message || `${action} failed.`);
}

export async function ingestDocs() {
  try {
    const { data } = await requestWithRetry(() => api.post("/ingest"), { retries: 1 });
    return data;
  } catch (error) {
    throw await normalizeApiError(error, "Document ingestion");
  }
}

export async function analyzeReport(payload) {
  try {
    const { data } = await requestWithRetry(
      () =>
        api.post("/analyze", payload, {
          headers: { "Content-Type": "multipart/form-data" },
          timeout: 600000,
        }),
      { retries: 1, retryDelayMs: 1800 }
    );
    return data;
  } catch (error) {
    throw await normalizeApiError(error, "Report analysis");
  }
}

export async function chatWithAssistant(body) {
  try {
    const payload = {
      question: `${body?.question || ""}`.trim(),
      analysis_summary:
        body?.analysis_summary && typeof body.analysis_summary === "object" && !Array.isArray(body.analysis_summary)
          ? body.analysis_summary
          : {},
      history: Array.isArray(body?.history)
        ? body.history
            .map((item) => ({
              role: item?.role === "assistant" ? "assistant" : "user",
              content: `${item?.content || ""}`.trim(),
            }))
            .filter((item) => item.content)
        : [],
    };

    const { data } = await requestWithRetry(
      () =>
        api.post("/chat", payload, {
          headers: { "Content-Type": "application/json" },
          timeout: 45000,
        }),
      { retries: 1, retryDelayMs: 1000 }
    );
    return data;
  } catch (error) {
    throw await normalizeApiError(error, "Assistant chat");
  }
}

export async function translateAnalysisToHindi(texts) {
  try {
    const { data } = await api.post("/translate/hindi", { texts });
    return Array.isArray(data?.translations) ? data.translations : [];
  } catch (error) {
    throw await normalizeApiError(error, "Hindi translation");
  }
}

export async function findNearbyDoctors(body) {
  try {
    const { data } = await requestWithRetry(
      () =>
        api.post("/doctors/nearby", body, {
          timeout: 45000,
        }),
      { retries: 1 }
    );
    return data;
  } catch (error) {
    throw await normalizeApiError(error, "Nearby doctor search");
  }
}

export async function requestEmailOtp(body) {
  try {
    const { data } = await api.post("/auth/request-otp", body);
    return data;
  } catch (error) {
    throw await normalizeApiError(error, "OTP request");
  }
}

export async function checkOtpAccount(email) {
  try {
    const { data } = await api.post("/auth/check-account", { email });
    return data;
  } catch (error) {
    throw await normalizeApiError(error, "Account check");
  }
}

export async function syncUserAccount(payload) {
  try {
    const { data } = await api.post("/auth/sync-user", payload);
    if (data?.success === false && data?.error) {
      throw new Error(data.error);
    }
    return data;
  } catch (error) {
    throw await normalizeApiError(error, "Account sync");
  }
}

export async function verifyEmailOtp(body) {
  try {
    const { data } = await api.post("/auth/verify-otp", body);
    return data;
  } catch (error) {
    throw await normalizeApiError(error, "OTP verification");
  }
}

export async function resetEmailPassword(body) {
  try {
    const { data } = await api.post("/auth/reset-password", body);
    return data;
  } catch (error) {
    throw await normalizeApiError(error, "Password reset");
  }
}

export async function logoutOtpSession(token) {
  try {
    const { data } = await api.post(
      "/auth/logout",
      {},
      { headers: { "X-Session-Token": token } }
    );
    return data;
  } catch (error) {
    throw await normalizeApiError(error, "OTP logout");
  }
}

export async function loadOtpWorkspace(token) {
  try {
    const { data } = await api.get("/workspace", {
      headers: { "X-Session-Token": token },
    });
    return data;
  } catch (error) {
    throw await normalizeApiError(error, "Workspace load");
  }
}

export async function saveOtpWorkspace(token, payload) {
  try {
    const { data } = await api.put("/workspace", payload, {
      headers: { "X-Session-Token": token },
    });
    return data;
  } catch (error) {
    throw await normalizeApiError(error, "Workspace save");
  }
}

export default api;

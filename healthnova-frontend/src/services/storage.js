const REPORTS_KEY = "healthnova_reports";
const CHAT_KEY = "healthnova_chat";
const CHAT_TABS_KEY = "healthnova_chat_tabs";
const DARK_KEY = "healthnova_dark";
const OTP_SESSION_KEY = "healthnova_otp_session";
const AUTH_USER_KEY = "healthnova_auth_user";
const REPORT_HISTORY_WINDOW_MS = 24 * 60 * 60 * 1000;

function scopedKey(baseKey, userId) {
  return userId ? `${baseKey}_${userId}` : `${baseKey}_guest`;
}

function isWithinHistoryWindow(value) {
  const timestamp = new Date(value || 0).getTime();
  return Number.isFinite(timestamp) && Date.now() - timestamp <= REPORT_HISTORY_WINDOW_MS;
}

export function getReports(userId = "") {
  try {
    const parsed = JSON.parse(localStorage.getItem(scopedKey(REPORTS_KEY, userId)) || "[]");
    return Array.isArray(parsed)
      ? parsed
          .map((item) => ({
            ...item,
            createdAt: item?.createdAt || new Date().toISOString(),
          }))
          .filter((item) => isWithinHistoryWindow(item?.createdAt))
          .sort((left, right) => new Date(right.createdAt || 0).getTime() - new Date(left.createdAt || 0).getTime())
      : [];
  } catch {
    return [];
  }
}

export function saveReports(reports, userId = "") {
  const normalized = (reports || [])
    .map((item) => ({
      ...item,
      createdAt: item?.createdAt || new Date().toISOString(),
    }))
    .filter((item) => isWithinHistoryWindow(item?.createdAt))
    .sort((left, right) => new Date(right.createdAt || 0).getTime() - new Date(left.createdAt || 0).getTime())
    .slice(0, 20);
  localStorage.setItem(scopedKey(REPORTS_KEY, userId), JSON.stringify(normalized));
}

export function saveReport(report, userId = "") {
  const reports = getReports(userId);
  reports.unshift({ id: crypto.randomUUID(), createdAt: new Date().toISOString(), ...report });
  saveReports(reports, userId);
}

export function getChatHistory(userId = "") {
  try {
    return JSON.parse(localStorage.getItem(scopedKey(CHAT_KEY, userId)) || "[]");
  } catch {
    return [];
  }
}

export function saveChatHistory(history, userId = "") {
  localStorage.setItem(scopedKey(CHAT_KEY, userId), JSON.stringify((history || []).slice(-60)));
}

export function getChatTabs(userId = "") {
  try {
    const parsed = JSON.parse(localStorage.getItem(scopedKey(CHAT_TABS_KEY, userId)) || "[]");
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

export function saveChatTabs(tabs, userId = "") {
  localStorage.setItem(scopedKey(CHAT_TABS_KEY, userId), JSON.stringify(Array.isArray(tabs) ? tabs : []));
}

export function clearChatHistory(userId = "") {
  localStorage.removeItem(scopedKey(CHAT_KEY, userId));
}

export function getDarkMode() {
  return localStorage.getItem(DARK_KEY) === "1";
}

export function setDarkMode(enabled) {
  localStorage.setItem(DARK_KEY, enabled ? "1" : "0");
}

export function getOtpSession() {
  try {
    return JSON.parse(localStorage.getItem(OTP_SESSION_KEY) || "null");
  } catch {
    return null;
  }
}

export function saveOtpSession(session) {
  localStorage.setItem(OTP_SESSION_KEY, JSON.stringify(session || null));
}

export function clearOtpSession() {
  localStorage.removeItem(OTP_SESSION_KEY);
}

export function getAuthUserSnapshot() {
  try {
    return JSON.parse(localStorage.getItem(AUTH_USER_KEY) || "null");
  } catch {
    return null;
  }
}

export function saveAuthUserSnapshot(user) {
  localStorage.setItem(AUTH_USER_KEY, JSON.stringify(user || null));
}

export function clearAuthUserSnapshot() {
  localStorage.removeItem(AUTH_USER_KEY);
}


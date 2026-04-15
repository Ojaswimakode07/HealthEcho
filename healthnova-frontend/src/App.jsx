import { useEffect, useMemo, useState } from "react";
import { Route, Routes, useLocation, useNavigate } from "react-router-dom";
import {
  ChevronDown,
  FileUp,
  Home,
  LogIn,
  LogOut,
  Menu,
  MessageSquare,
  Moon,
  Star,
  SunMedium,
  X,
} from "lucide-react";
import AuthModal from "./components/AuthModal";
import LandingPage from "./pages/LandingPage";
import WorkspacePage from "./pages/WorkspacePage";
import {
  analyzeReport,
  chatWithAssistant,
  ingestDocs,
  loadOtpWorkspace,
  logoutOtpSession,
  saveOtpWorkspace,
} from "./services/api";
import {
  completeEmailLinkLogin,
  hasSubmittedPublicFeedback,
  loadPublicFeedback,
  loadUserWorkspace,
  logoutUser,
  observeAuthState,
  saveUserWorkspace,
  submitPublicFeedback,
} from "./services/firebase";
import {
  clearAuthUserSnapshot,
  clearOtpSession,
  getAuthUserSnapshot,
  getChatHistory,
  getChatTabs,
  getDarkMode,
  getOtpSession,
  getReports,
  saveAuthUserSnapshot,
  saveChatHistory,
  saveChatTabs,
  saveOtpSession,
  saveReports,
  setDarkMode,
} from "./services/storage";

const FEEDBACK_SUBMITTED_KEY = "healthnova_feedback_submitted";
const PENDING_FEEDBACK_KEY = "healthnova_pending_feedback";
const REPORT_HISTORY_WINDOW_MS = 24 * 60 * 60 * 1000;

function getWorkspaceAccountKey(user, otpSession) {
  return user?.uid || user?.email || otpSession?.user?.uid || otpSession?.user?.email || "";
}

function getFeedbackAccountKey(user, otpSession) {
  const effectiveUser = user || otpSession?.user || null;
  return effectiveUser?.uid || effectiveUser?.email || "guest";
}

function getFeedbackStorageKey(baseKey, accountKey) {
  return `${baseKey}:${accountKey || "guest"}`;
}

function getStoredFeedbackSubmitted(accountKey) {
  try {
    return window.localStorage.getItem(getFeedbackStorageKey(FEEDBACK_SUBMITTED_KEY, accountKey)) === "1";
  } catch {
    return false;
  }
}

function markFeedbackSubmitted(accountKey) {
  try {
    window.localStorage.setItem(getFeedbackStorageKey(FEEDBACK_SUBMITTED_KEY, accountKey), "1");
  } catch {}
}

function loadPendingFeedback() {
  try {
    const raw = window.localStorage.getItem(PENDING_FEEDBACK_KEY);
    const parsed = raw ? JSON.parse(raw) : [];
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

function savePendingFeedback(items) {
  try {
    window.localStorage.setItem(PENDING_FEEDBACK_KEY, JSON.stringify(items));
  } catch {}
}

function queuePendingFeedback(entry) {
  const current = loadPendingFeedback();
  savePendingFeedback([...current, entry]);
}

function mergeVisibleFeedback(current, entry) {
  return [...current, entry]
    .filter((item, index, all) => index === all.findIndex((candidate) => candidate.id === item.id))
    .filter((item) => Number(item?.rating) >= 4 && `${item?.quote || ""}`.trim() && `${item?.name || ""}`.trim())
    .sort((left, right) => new Date(right.createdAt || 0).getTime() - new Date(left.createdAt || 0).getTime())
    .slice(0, 5);
}

function getVisiblePendingFeedback() {
  return loadPendingFeedback()
    .filter((item) => Number(item?.rating) >= 4 && `${item?.quote || ""}`.trim() && `${item?.name || ""}`.trim())
    .map((item) => ({
      id: item.id,
      name: `${item.name}`.trim(),
      role: `${item.role || "HealthNova user"}`.trim(),
      quote: `${item.quote}`.trim(),
      rating: Number(item.rating),
      badge: `${item.rating}-star feedback`,
      createdAt: item.createdAt || new Date().toISOString(),
    }));
}

function getDefaultFeedbackName(user, otpSession) {
  const effectiveUser = user || otpSession?.user || null;
  if (effectiveUser?.name?.trim()) return effectiveUser.name.trim();
  if (effectiveUser?.email?.trim()) return effectiveUser.email.split("@")[0];
  return "";
}

function mergeWorkspace(localReports, localChat, remoteWorkspace) {
  const remoteReports = filterReportsTo24Hours(Array.isArray(remoteWorkspace?.reports) ? remoteWorkspace.reports : []);
  const recentLocalReports = filterReportsTo24Hours(localReports);
  const remoteChat = Array.isArray(remoteWorkspace?.chatHistory) ? remoteWorkspace.chatHistory : [];
  const remoteChatTabs = Array.isArray(remoteWorkspace?.chatTabs) ? remoteWorkspace.chatTabs : [];

  const reports = [...remoteReports, ...recentLocalReports].filter(
    (item, index, all) =>
      index === all.findIndex((candidate) => candidate.id === item.id || candidate.createdAt === item.createdAt)
  );

  const chatHistory = [...remoteChat, ...localChat].filter(
    (item, index, all) =>
      index ===
      all.findIndex(
        (candidate) =>
          candidate.id === item.id ||
          (candidate.role === item.role && candidate.content === item.content && candidate.createdAt === item.createdAt)
      )
  );

  return { reports: filterReportsTo24Hours(reports).slice(0, 20), chatHistory: chatHistory.slice(-60), chatTabs: remoteChatTabs };
}

function mergeLocalWorkspace(primaryReports, primaryChat, guestReports, guestChat) {
  const reports = [...filterReportsTo24Hours(primaryReports), ...filterReportsTo24Hours(guestReports)].filter(
    (item, index, all) =>
      index === all.findIndex((candidate) => candidate.id === item.id || candidate.createdAt === item.createdAt)
  );

  const chatHistory = [...(primaryChat || []), ...(guestChat || [])].filter(
    (item, index, all) =>
      index ===
      all.findIndex(
        (candidate) =>
          candidate.id === item.id ||
          (candidate.role === item.role && candidate.content === item.content && candidate.createdAt === item.createdAt)
      )
  );

  return { reports: filterReportsTo24Hours(reports).slice(0, 20), chatHistory: chatHistory.slice(-60), chatTabs: [] };
}

function filterReportsTo24Hours(items) {
  return (items || []).filter((item) => {
    const timestamp = new Date(item?.createdAt || 0).getTime();
    return Number.isFinite(timestamp) && Date.now() - timestamp <= REPORT_HISTORY_WINDOW_MS;
  });
}

function normalizeReportsForAccount(items, accountKey) {
  const normalizedAccountKey = `${accountKey || ""}`.trim().toLowerCase();
  return filterReportsTo24Hours(items).filter((item) => {
    const itemAccountKey = `${item?.accountKey || ""}`.trim().toLowerCase();
    if (!normalizedAccountKey) {
      return !itemAccountKey || itemAccountKey === "guest";
    }
    return !itemAccountKey || itemAccountKey === normalizedAccountKey;
  });
}

function flattenChatTabs(tabs) {
  const flattened = (Array.isArray(tabs) ? tabs : [])
    .flatMap((tab) => (Array.isArray(tab?.messages) ? tab.messages : []))
    .filter((item) => item?.role && item?.content && item?.createdAt)
    .sort((left, right) => new Date(left.createdAt || 0).getTime() - new Date(right.createdAt || 0).getTime());

  return flattened
    .filter(
      (item, index, all) =>
        index ===
        all.findIndex(
          (candidate) =>
            candidate.id === item.id ||
            (candidate.role === item.role && candidate.content === item.content && candidate.createdAt === item.createdAt)
        )
    )
    .slice(-60);
}

function detectReportMedium(file) {
  const type = `${file?.type || ""}`.toLowerCase();
  const name = `${file?.name || ""}`.toLowerCase();
  if (type.startsWith("image/")) return "Image report";
  if (type === "application/pdf" || name.endsWith(".pdf")) return "PDF report";
  if (name.endsWith(".doc") || name.endsWith(".docx")) return "Document report";
  return "Uploaded report";
}

function inferSpecialistFromMetadata(metadata = {}, response = {}) {
  const combined = [
    metadata?.reportType,
    metadata?.medium,
    metadata?.notes,
    response?.report_type,
    response?.clinical_explanation,
    response?.evidence_summary,
  ]
    .map((value) => `${value || ""}`.toLowerCase())
    .join(" ");

  if (/\b(ecg|ekg|electrocardiogram|cardiac|rhythm)\b/.test(combined)) return "Cardiologist";
  if (/\b(x[- ]?ray|xray|fracture|bone|orthopedic|orthopaedic|ortho)\b/.test(combined)) return "Orthopedist";
  if (/\b(pediatric|infant|child|9-month|month-old)\b/.test(combined)) return "Pediatrician";
  return "Relevant specialist";
}

function isLabLikeReportType(reportType = "") {
  const text = `${reportType || ""}`.toLowerCase();
  return /\b(cbc|blood|thyroid|kidney|liver|glucose|hb|hba1c|lipid|lab|biochemistry|hematology)\b/.test(text);
}

function inferReportTypeFromMetadata(metadata = {}, response = {}) {
  const combined = [
    metadata?.reportType,
    metadata?.medium,
    metadata?.notes,
    response?.report_type,
    response?.clinical_explanation,
    response?.evidence_summary,
    ...(Array.isArray(response?.report_findings) ? response.report_findings.flatMap((item) => [item?.label, item?.value]) : []),
    ...(Array.isArray(response?.interpreted_lab_values) ? response.interpreted_lab_values.flatMap((item) => [item?.label, item?.value]) : []),
    ...(response?.extracted_values && typeof response.extracted_values === "object" ? Object.keys(response.extracted_values) : []),
  ]
    .map((value) => `${value || ""}`.toLowerCase())
    .join(" ");

  if (/\b(hemoglobin|haemoglobin|wbc|rbc|platelet|mcv|mch|mchc|rdw|cbc|complete blood count)\b/.test(combined)) return "CBC";
  if (/\b(glucose|hba1c|diabetes)\b/.test(combined)) return "Blood test";
  if (/\b(tsh|t3|t4|thyroid)\b/.test(combined)) return "Thyroid report";
  if (/\b(creatinine|urea|kidney|renal)\b/.test(combined)) return "Kidney panel";
  if (/\b(bilirubin|alt|ast|alp|liver)\b/.test(combined)) return "Liver panel";
  return normalizeScalarText(response?.report_type, "") || metadata.reportType || metadata.medium || "Medical report";
}

function readFileAsDataUrl(file) {
  return new Promise((resolve, reject) => {
    if (!file) {
      resolve("");
      return;
    }
    const reader = new FileReader();
    reader.onload = () => resolve(typeof reader.result === "string" ? reader.result : "");
    reader.onerror = () => reject(new Error("Could not read the uploaded file preview."));
    reader.readAsDataURL(file);
  });
}

function toListItems(value, fallbackLabel) {
  if (!value) return [];
  const parseStructuredString = (raw) => {
    const text = `${raw || ""}`.trim();
    if (!text) return null;
    if (!/^[\[{]/.test(text)) return null;

    try {
      const normalized = text
        .replace(/([{,]\s*)'([^']+?)'\s*:/g, '$1"$2":')
        .replace(/:\s*'([^']*?)'/g, ': "$1"')
        .replace(/\bNone\b/g, "null")
        .replace(/\bTrue\b/g, "true")
        .replace(/\bFalse\b/g, "false");
      return JSON.parse(normalized);
    } catch {
      return null;
    }
  };

  const parsedStructured = typeof value === "string" ? parseStructuredString(value) : null;
  if (parsedStructured) {
    return toListItems(parsedStructured, fallbackLabel);
  }
  if (Array.isArray(value)) {
    return value
      .map((item, index) => {
        if (typeof item === "string") {
          return { label: `${fallbackLabel} ${index + 1}`, value: item };
        }
        if (item && typeof item === "object") {
          const label = item.label || item.name || item.title || item.test || `${fallbackLabel} ${index + 1}`;
          const rest = Object.entries(item)
            .filter(([key]) => !["label", "name", "title", "test"].includes(key))
            .map(([, entry]) => (entry == null ? "" : `${entry}`.trim()))
            .filter(Boolean)
            .join(" | ");
          return { label, value: rest || JSON.stringify(item) };
        }
        return { label: `${fallbackLabel} ${index + 1}`, value: `${item}` };
      })
      .filter((item) => item.value?.trim());
  }
  if (typeof value === "object") {
    return Object.entries(value)
      .map(([key, item]) => ({ label: key, value: item == null ? "" : `${item}`.trim() }))
      .filter((item) => item.value?.trim());
  }
  if (typeof value === "string" && value.trim()) {
    return [{ label: fallbackLabel, value: value.trim() }];
  }
  return [];
}

function normalizeScalarText(value, fallback = "") {
  const items = toListItems(value, "");
  if (items.length) {
    return items
      .map((item) => `${item.value || item.label || ""}`.trim())
      .filter(Boolean)
      .join(" ");
  }
  return `${value || fallback}`.trim() || fallback;
}

function splitEvidenceBuckets(items) {
  const whyLikely = [];
  const uncertain = [];

  items.forEach((item, index) => {
    const label = `${item?.label || `Evidence ${index + 1}`}`.trim();
    const value = `${item?.value || ""}`.trim();
    if (!value) return;

    const combined = `${label} ${value}`.toLowerCase();
    if (/(uncertain|limited|alternative|missing|ocr|unclear|incomplete|not enough)/.test(combined)) {
      uncertain.push({ label, value });
      return;
    }
    whyLikely.push({ label, value });
  });

  return { whyLikely, uncertain };
}

function normalizePredictedConditions(items) {
  const seen = new Set();
  return toListItems(items, "Condition")
    .map((item) => {
      const rawLabel = `${item?.label || ""}`.trim();
      const rawValue = `${item?.value || ""}`.trim();
      let label = rawLabel;
      let value = rawValue;

      if (/^condition(\s+\d+)?$/i.test(label) && value) {
        const parts = value.split(/[:|-]/);
        if (parts[0]?.trim()) {
          label = parts[0].trim();
        }
      }

      if (label && value.toLowerCase().startsWith(`${label.toLowerCase()}:`)) {
        value = value.slice(label.length + 1).trim();
      }

      if (!value) {
        value = label;
      }

      return {
        label: label || "Possible condition",
        value,
      };
    })
    .filter((item) => {
      const key = `${item.label} ${item.value}`.trim().toLowerCase();
      if (!key || seen.has(key)) return false;
      seen.add(key);
      return true;
    });
}

function buildMostLikelyPatternSection(response, predictedConditions, reportFindings) {
  const patternItem =
    predictedConditions.find((item) => `${item?.label || ""}`.trim().toLowerCase() === "most likely pattern") ||
    null;
  const value =
    patternItem?.value ||
    `${response?.clinical_explanation || ""}`.trim() ||
    reportFindings[0]?.value ||
    "";

  return value ? [{ label: "Most likely pattern", value }] : [];
}

function normalizeReport(response, fileName, metadata = {}) {
  const reportFindings = toListItems(response?.report_findings, "Finding");
  const interpretedLabValues = toListItems(response?.interpreted_lab_values, "Lab value");
  const predictedConditions = normalizePredictedConditions(response?.predicted_conditions);
  const recommendedTests = toListItems(response?.recommended_tests, "Recommended test");
  const suggestedBloodTests = toListItems(response?.suggested_blood_tests, "Suggested blood test");
  const dietRecommendations = toListItems(response?.diet_recommendations, "Diet");
  const lifestyleChanges = toListItems(response?.lifestyle_changes, "Lifestyle");
  const precautions = toListItems(response?.precautions, "Precaution");
  const evidenceSources = toListItems(response?.evidence_sources, "Evidence");
  const supportingContext = toListItems(response?.supporting_context, "Context");
  const extractedValues = toListItems(response?.extracted_values, "Extracted value");
  const normalizedReportType = inferReportTypeFromMetadata(metadata, response);
  const labLikeReport = isLabLikeReportType(normalizedReportType);
  const mostLikelyPattern = buildMostLikelyPatternSection(response, predictedConditions, reportFindings);
  const possibleDiseases = predictedConditions.filter(
    (item) => `${item?.label || ""}`.trim().toLowerCase() !== "most likely pattern"
  );
  const { whyLikely, uncertain } = splitEvidenceBuckets(evidenceSources);
  const nextTestsToConfirm = recommendedTests.length ? recommendedTests : labLikeReport ? suggestedBloodTests : [];

  const sections = [
    { title: "Most likely pattern", items: mostLikelyPattern },
    { title: "Possible diseases", items: possibleDiseases },
    { title: "Why this is likely", items: whyLikely },
    { title: "What makes it uncertain", items: uncertain },
    { title: "Next tests to confirm", items: nextTestsToConfirm },
    { title: "Report findings", items: reportFindings },
    { title: labLikeReport ? "Interpreted lab values" : "Interpreted details", items: interpretedLabValues },
    { title: "Predicted conditions", items: predictedConditions },
    { title: "Recommended tests", items: recommendedTests },
    { title: "Suggested blood tests", items: labLikeReport ? suggestedBloodTests : [] },
    { title: "Diet recommendations", items: dietRecommendations },
    { title: "Lifestyle changes", items: lifestyleChanges },
    { title: "Precautions", items: precautions },
    { title: "Supporting context", items: supportingContext },
    { title: "Evidence sources", items: evidenceSources },
    { title: "Extracted values", items: extractedValues },
  ].filter((section) => section.items.length);

  const clinicalExplanation = normalizeScalarText(response?.clinical_explanation);
  const evidenceSummary = normalizeScalarText(response?.evidence_summary);
  const symptomsSummary = normalizeScalarText(response?.symptoms_summary);
  const riskLevelText = normalizeScalarText(response?.risk_level, "Preliminary");
  const confidenceLevelText = normalizeScalarText(response?.confidence_level, "Preliminary");
  const doctorSpecialistText =
    normalizeScalarText(response?.doctor_specialist, "") || inferSpecialistFromMetadata(metadata, response);
  const disclaimerText = normalizeScalarText(
    response?.disclaimer,
    "This is AI-assisted guidance and does not replace clinician review."
  );
  const summary =
    clinicalExplanation ||
    evidenceSummary ||
    symptomsSummary ||
    reportFindings[0]?.value ||
    "Analysis completed.";

  return {
    id: crypto.randomUUID(),
    createdAt: new Date().toISOString(),
    fileName,
    title: fileName || "Medical report",
    patientName: metadata.patientName || "",
    reportType: normalizedReportType,
    notes: metadata.notes || "",
    medium: metadata.medium || "",
    previewUrl: metadata.previewUrl || "",
    accountKey: metadata.accountKey || "guest",
    summary,
    clinicalExplanation,
    evidenceSummary,
    symptomsSummary,
    riskLevel: riskLevelText,
    confidenceLevel: confidenceLevelText,
    displayConfidence: confidenceLevelText,
    doctorSpecialist: doctorSpecialistText,
    disclaimer: disclaimerText,
    analysisReliability: "structured",
    accuracyNote: disclaimerText,
    verdict: {
      tone: /(high|critical|urgent|severe)/i.test(riskLevelText) ? "attention" : "okay",
      label: riskLevelText || "Preliminary",
      summary,
    },
    sections,
    numericMetrics: [],
    raw: response,
    chartData: [],
  };
}

function buildAnalysisSummary(report) {
  if (!report) return {};
  const extractedValues = report.sections?.find((section) => section.title === "Extracted values")?.items || [];
  return {
    title: report.title || "",
    summary: report.summary || "",
    risk_level: report.riskLevel || "",
    confidence_level: report.confidenceLevel || "",
    doctor_specialist: report.doctorSpecialist || "",
    report_type: report.reportType || "",
    extracted_values: extractedValues.reduce((acc, item) => {
      if (item?.label && item?.value) acc[item.label] = item.value;
      return acc;
    }, {}),
  };
}

function buildLocalChatFallback(message, report) {
  const text = `${message || ""}`.trim().toLowerCase();
  const summary = `${report?.summary || ""}`.trim();
  const specialist = `${report?.doctorSpecialist || "doctor"}`.trim();
  const risk = `${report?.riskLevel || ""}`.trim();

  if (/what does this report mean|explain.*report|summary of the report|what is in the report/.test(text)) {
    return summary
      ? `In simple terms, ${summary} The current report risk looks ${risk || "not clearly stated"}. If you want, ask me about one specific value and I’ll keep it short and simple.`
      : "I can explain the report, but I need the report summary or extracted values first.";
  }

  if (/what should i ask my doctor|questions? for my doctor/.test(text)) {
    return `Ask what the main abnormal finding is, how serious it is, what could be causing it, whether repeat testing is needed, and whether you should see a ${specialist.toLowerCase()}.`;
  }

  if (/which values?.*abnormal|which values?.*high|which values?.*low/.test(text)) {
    return summary
      ? `The main values to follow up are usually the ones outside range or mentioned in the report summary. Right now your report says: ${summary}`
      : "The values needing follow-up are usually the ones outside range or marked high or low in the report.";
  }

  if (/hi|hello|hey/.test(text)) {
    return summary
      ? `Hi. I can help with your report. Right now the summary says: ${summary}`
      : "Hi. I can help explain your report, symptoms, or what to ask your doctor next.";
  }

  if (summary) {
    return `I could not reach the live chat service fast enough, but based on your latest report: ${summary} If you ask one short question about a symptom, value, or next step, I’ll answer from the report context.`;
  }

  return "I could not reach the live chat service fast enough, but you can still ask about symptoms, report values, or next steps and I’ll answer with the context available here.";
}

export function App() {
  const [otpSession, setOtpSession] = useState(() => getOtpSession());
  const [user, setUser] = useState(() => getAuthUserSnapshot() || getOtpSession()?.user || null);
  const [userMenuOpen, setUserMenuOpen] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [authOpen, setAuthOpen] = useState(false);
  const [authMode, setAuthMode] = useState("login");
  const [reports, setReports] = useState([]);
  const [chatHistory, setChatHistory] = useState([]);
  const [chatTabs, setChatTabs] = useState([]);
  const [dark, setDark] = useState(() => getDarkMode());
  const [statusMessage, setStatusMessage] = useState("");
  const [isBootstrappingAuth, setIsBootstrappingAuth] = useState(true);
  const [siteFeedback, setSiteFeedback] = useState([]);
  const [feedbackOpen, setFeedbackOpen] = useState(false);
  const [feedbackSubmitting, setFeedbackSubmitting] = useState(false);
  const [feedbackError, setFeedbackError] = useState("");
  const location = useLocation();
  const navigate = useNavigate();
  const feedbackAccountKey = getFeedbackAccountKey(user, otpSession);
  const [hasSubmittedFeedback, setHasSubmittedFeedback] = useState(() => getStoredFeedbackSubmitted("guest"));
  const [feedbackForm, setFeedbackForm] = useState({ name: "", role: "", rating: 0, quote: "" });
  const hasFeedbackEligibleUser = Boolean(user?.uid || user?.email || otpSession?.user?.uid || otpSession?.user?.email);
  const canOpenFeedback = hasFeedbackEligibleUser && !hasSubmittedFeedback;
  const isLanding = location.pathname === "/";

  useEffect(() => {
    if (!statusMessage) return undefined;
    const timer = window.setTimeout(() => setStatusMessage(""), 3200);
    return () => window.clearTimeout(timer);
  }, [statusMessage]);

  useEffect(() => {
    document.documentElement.classList.toggle("dark", dark);
    setDarkMode(dark);
  }, [dark]);

  useEffect(() => {
    let active = true;
    const localSubmitted = getStoredFeedbackSubmitted(feedbackAccountKey);
    setHasSubmittedFeedback(localSubmitted);

    if (!feedbackAccountKey || feedbackAccountKey === "guest") {
      return () => {
        active = false;
      };
    }

    hasSubmittedPublicFeedback(feedbackAccountKey)
      .then((submitted) => {
        if (active) {
          setHasSubmittedFeedback(localSubmitted || submitted);
        }
      })
      .catch(() => {
        if (active) {
          setHasSubmittedFeedback(localSubmitted);
        }
      });

    return () => {
      active = false;
    };
  }, [feedbackAccountKey]);

  useEffect(() => {
    let active = true;
    const pendingVisible = getVisiblePendingFeedback();
    if (pendingVisible.length) {
      setSiteFeedback((current) => {
        let next = current;
        pendingVisible.forEach((item) => {
          next = mergeVisibleFeedback(next, item);
        });
        return next;
      });
    }

    loadPublicFeedback()
      .then((items) => {
        if (!active) return;
        let next = Array.isArray(items) ? items : [];
        pendingVisible.forEach((item) => {
          next = mergeVisibleFeedback(next, item);
        });
        setSiteFeedback(next);
      })
      .catch(() => {});

    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    let active = true;

    completeEmailLinkLogin()
      .catch((error) => {
        if (active) setStatusMessage(error.message || "Could not complete login link.");
      })
      .finally(() => {
        if (active) setIsBootstrappingAuth(false);
      });

    const unsubscribe = observeAuthState(async (nextUser) => {
      if (!active) return;
      const effectiveUser = nextUser || otpSession?.user || null;
      if (nextUser) {
        saveAuthUserSnapshot(nextUser);
      } else if (!otpSession?.token) {
        clearAuthUserSnapshot();
      }
      setUser(effectiveUser);
      const userId = nextUser?.uid || otpSession?.user?.uid || otpSession?.user?.email || "";
      const localReports = normalizeReportsForAccount(getReports(userId), userId);
      const localChat = getChatHistory(userId);
      const localChatTabs = getChatTabs(userId);

      if (!nextUser && !otpSession?.token) {
        setReports(localReports);
        setChatHistory(localChat);
        setChatTabs(localChatTabs);
        return;
      }

      try {
        const remoteWorkspace = nextUser?.uid
          ? await loadUserWorkspace(nextUser.uid)
          : await loadOtpWorkspace(otpSession.token);
        const merged = mergeWorkspace(localReports, localChat, remoteWorkspace);
        setReports(normalizeReportsForAccount(merged.reports, userId));
        setChatHistory(merged.chatHistory);
        setChatTabs(Array.isArray(remoteWorkspace?.chatTabs) && remoteWorkspace.chatTabs.length ? remoteWorkspace.chatTabs : localChatTabs);
        saveReports(normalizeReportsForAccount(merged.reports, userId), userId);
        saveChatHistory(merged.chatHistory, userId);
        saveChatTabs(Array.isArray(remoteWorkspace?.chatTabs) && remoteWorkspace.chatTabs.length ? remoteWorkspace.chatTabs : localChatTabs, userId);
      } catch {
        setReports(localReports);
        setChatHistory(localChat);
        setChatTabs(localChatTabs);
      }
    });

    return () => {
      active = false;
      unsubscribe();
    };
  }, [otpSession]);

  useEffect(() => {
    const userId = getWorkspaceAccountKey(user, otpSession);
    const recentReports = normalizeReportsForAccount(reports, userId);
    const persistedChatHistory = chatTabs.length ? flattenChatTabs(chatTabs) : chatHistory;
    if (recentReports.length !== reports.length) {
      setReports(recentReports);
      return;
    }
    saveReports(recentReports, userId);
    saveChatHistory(persistedChatHistory, userId);
    saveChatTabs(chatTabs, userId);

    if (otpSession?.token && !user?.uid) {
      saveOtpWorkspace(otpSession.token, { reports: recentReports, chatHistory: persistedChatHistory, chatTabs }).catch(() => {});
    }

    if (user?.uid) {
      saveUserWorkspace(user.uid, { reports: recentReports, chatHistory: persistedChatHistory, chatTabs }, { email: user.email, name: user.name }).catch(() => {});
    }
  }, [reports, chatHistory, chatTabs, user, otpSession]);

  useEffect(() => {
    if (isBootstrappingAuth || !canOpenFeedback) return undefined;
    const timer = window.setTimeout(() => setFeedbackOpen(true), 10 * 60 * 1000);
    return () => window.clearTimeout(timer);
  }, [canOpenFeedback, isBootstrappingAuth]);

  useEffect(() => {
    if (!feedbackOpen) return;
    setFeedbackForm((current) => ({
      ...current,
      name: current.name || getDefaultFeedbackName(user, otpSession),
    }));
  }, [feedbackOpen, user, otpSession]);

  useEffect(() => {
    setMobileMenuOpen(false);
    setUserMenuOpen(false);
  }, [location.pathname]);

  useEffect(() => {
    async function flushPendingFeedback() {
      const pendingItems = loadPendingFeedback();
      if (!pendingItems.length || !navigator.onLine) return;

      const remaining = [];
      for (const item of pendingItems) {
        try {
          const response = await submitPublicFeedback(item);
          if (response?.displayed && response?.entry) {
            setSiteFeedback((current) => mergeVisibleFeedback(current, response.entry));
          }
        } catch {
          remaining.push(item);
        }
      }
      savePendingFeedback(remaining);
    }

    flushPendingFeedback();
    window.addEventListener("online", flushPendingFeedback);
    return () => window.removeEventListener("online", flushPendingFeedback);
  }, []);

  const workspaceNavItems = useMemo(
    () => [
      { label: "Home", path: "/", icon: Home, match: (pathname) => pathname === "/" },
      { label: "Analysis", path: "/app/analysis", icon: FileUp, match: (pathname) => pathname === "/app/analysis" },
      { label: "Chat", path: "/app/chat", icon: MessageSquare, match: (pathname) => pathname === "/app/chat" },
    ],
    []
  );

  const landingNavItems = useMemo(
    () => [
      { label: "Services", sectionId: "services" },
      { label: "Why Choose Us", sectionId: "advantages" },
      { label: "Care Paths", sectionId: "programs" },
      { label: "Reviews", sectionId: "testimonials" },
    ],
    []
  );

  const navItems = isLanding ? landingNavItems : workspaceNavItems;

  function openAuth(mode = "login") {
    setAuthMode(mode);
    setAuthOpen(true);
  }

  function scrollToSection(sectionId) {
    if (!sectionId) return;
    if (location.pathname !== "/") {
      navigate("/", { state: { scrollTo: sectionId } });
      return;
    }
    const target = document.getElementById(sectionId);
    target?.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  function handleNavSelection(item) {
    if (item.sectionId) {
      scrollToSection(item.sectionId);
      return;
    }
    if (item.path) {
      navigate(item.path);
    }
  }

  async function handleAnalyze(formValues) {
    const formData = new FormData();
    formData.append("file", formValues.file);

    const manualText = [formValues.patientName, formValues.reportType, formValues.notes]
      .map((value) => (typeof value === "string" ? value.trim() : ""))
      .filter(Boolean)
      .join("\n");

    if (manualText) {
      formData.append("manual_text", manualText);
    }

    const result = await analyzeReport(formData);
    const previewUrl = formValues.file?.type?.startsWith("image/") ? await readFileAsDataUrl(formValues.file) : "";
    const accountKey = getWorkspaceAccountKey(user, otpSession);
    const report = normalizeReport(result, formValues.file?.name || "Report", {
      patientName: formValues.patientName?.trim?.() || "",
      reportType: formValues.reportType?.trim?.() || "",
      notes: formValues.notes?.trim?.() || "",
      medium: detectReportMedium(formValues.file),
      previewUrl,
      accountKey: accountKey || "guest",
    });
    setReports((current) => [report, ...current].slice(0, 20));
    setStatusMessage("Report analyzed successfully.");
    navigate("/app/analysis");
    return report;
  }

  async function handleChatSubmit(message) {
    const trimmedMessage = `${message || ""}`.trim();
    if (!trimmedMessage) return;

    const userMessage = {
      id: crypto.randomUUID(),
      role: "user",
      content: trimmedMessage,
      createdAt: new Date().toISOString(),
    };

    const nextHistory = [...chatHistory, userMessage];
    setChatHistory(nextHistory);

    const analysisSummary = buildAnalysisSummary(reports[0]);
    let assistantMessage;

    try {
      const response = await chatWithAssistant({
        question: trimmedMessage,
        analysis_summary: analysisSummary,
        history: nextHistory.map(({ role, content }) => ({ role, content })),
      });

      assistantMessage = {
        id: crypto.randomUUID(),
        role: "assistant",
        content:
          response?.answer ||
          response?.result ||
          response?.response ||
          response?.message ||
          "I could not produce a complete answer yet.",
        createdAt: new Date().toISOString(),
      };
    } catch {
      assistantMessage = {
        id: crypto.randomUUID(),
        role: "assistant",
        content: buildLocalChatFallback(trimmedMessage, reports[0]),
        createdAt: new Date().toISOString(),
      };
    }

    setChatHistory((current) => [...current, assistantMessage].slice(-60));
  }

  async function handleIngest() {
    const response = await ingestDocs();
    setStatusMessage(response?.message || "Document ingestion completed.");
    return response;
  }

  async function handleFeedbackSubmit(event) {
    event.preventDefault();
    setFeedbackSubmitting(true);
    setFeedbackError("");

    const payload = {
      id: globalThis.crypto?.randomUUID?.() || `${Date.now()}`,
      createdAt: new Date().toISOString(),
      ...feedbackForm,
      accountKey: feedbackAccountKey,
      user: user || otpSession?.user || null,
    };

    try {
      const response = await submitPublicFeedback(payload);
      if (response?.alreadySubmitted) {
        markFeedbackSubmitted(feedbackAccountKey);
        setHasSubmittedFeedback(true);
        setFeedbackOpen(false);
        setStatusMessage("Feedback was already submitted for this account.");
      } else {
        if (response?.displayed && response?.entry) {
          setSiteFeedback((current) => mergeVisibleFeedback(current, response.entry));
        }
        markFeedbackSubmitted(feedbackAccountKey);
        setHasSubmittedFeedback(true);
        setFeedbackOpen(false);
        setStatusMessage("Thanks for the feedback.");
      }
    } catch (error) {
      const message = error.message || "Could not submit feedback right now.";
      if (!navigator.onLine || /client is offline|offline/i.test(message)) {
        queuePendingFeedback(payload);
        if (Number(payload.rating) >= 4 && `${payload.quote || ""}`.trim() && `${payload.name || ""}`.trim()) {
          setSiteFeedback((current) =>
            mergeVisibleFeedback(current, {
              id: payload.id,
              name: `${payload.name}`.trim(),
              role: `${payload.role || "HealthNova user"}`.trim(),
              quote: `${payload.quote}`.trim(),
              rating: Number(payload.rating),
              badge: `${payload.rating}-star feedback`,
              createdAt: payload.createdAt,
            })
          );
        }
        markFeedbackSubmitted(feedbackAccountKey);
        setHasSubmittedFeedback(true);
        setFeedbackOpen(false);
        setStatusMessage("Feedback saved locally. It will sync when you are back online.");
      } else {
        setFeedbackError(message);
      }
    } finally {
      setFeedbackSubmitting(false);
    }
  }

  async function handleLogout() {
    if (otpSession?.token && !user?.uid) {
      try {
        await logoutOtpSession(otpSession.token);
      } catch {}
      clearOtpSession();
      clearAuthUserSnapshot();
      setOtpSession(null);
      setUser(null);
      navigate("/");
      return;
    }

    await logoutUser();
    clearOtpSession();
    clearAuthUserSnapshot();
    setOtpSession(null);
    setUser(null);
    navigate("/");
  }

  return (
    <div className="app-root">
      <header className="topbar">
        <div className="topbar__row">
          <button
            className="brand"
            onClick={() => {
              if (location.pathname === "/") {
                window.scrollTo({ top: 0, behavior: "smooth" });
                return;
              }
              navigate("/");
            }}
            type="button"
          >
            <span className="brand__pulse" />
            <span>HealthNova</span>
          </button>

          <button
            className="icon-chip topbar__menu-toggle"
            onClick={() => setMobileMenuOpen((current) => !current)}
            aria-label={mobileMenuOpen ? "Close menu" : "Open menu"}
            aria-expanded={mobileMenuOpen}
            type="button"
          >
            {mobileMenuOpen ? <X size={18} /> : <Menu size={18} />}
          </button>
        </div>

        <div className={`topbar__menu ${mobileMenuOpen ? "is-open" : ""}`}>
          <nav className={`topbar__nav ${isLanding ? "topbar__nav--landing" : "topbar__nav--workspace"}`}>
            {navItems.map((item) => {
              const Icon = item.icon;
              const isActive = item.match ? item.match(location.pathname) : false;
              return (
                <button
                  key={item.label}
                  className={`nav-chip ${isActive ? "active" : ""} ${Icon ? "" : "nav-chip--plain"}`}
                  onClick={() => handleNavSelection(item)}
                  type="button"
                >
                  {Icon ? <Icon size={16} /> : null}
                  <span>{item.label}</span>
                </button>
              );
            })}
          </nav>

          <div className="topbar__actions">
            <button className="icon-chip" onClick={() => setDark((current) => !current)} aria-label="Toggle theme" type="button">
              {dark ? <SunMedium size={18} /> : <Moon size={18} />}
            </button>

            {!user ? (
              <button className="ghost-btn" onClick={() => openAuth("login")} type="button">
                <LogIn size={16} />
                <span>Login</span>
              </button>
            ) : (
              <div className="user-menu">
                <button className="user-badge user-menu__trigger" onClick={() => setUserMenuOpen((current) => !current)} type="button">
                  <span className="user-badge__avatar">{(user.name || user.email || "H")[0]}</span>
                  <span>{user.name || user.email}</span>
                  <ChevronDown size={16} className={userMenuOpen ? "chevron-open" : ""} />
                </button>
                {userMenuOpen ? (
                  <div className="user-menu__dropdown">
                    {canOpenFeedback ? (
                      <button
                        className="ghost-btn user-menu__item"
                        onClick={() => {
                          setFeedbackError("");
                          setFeedbackOpen(true);
                          setUserMenuOpen(false);
                        }}
                        type="button"
                        disabled={feedbackSubmitting}
                      >
                        <Star size={16} />
                        <span>Give Feedback</span>
                      </button>
                    ) : null}
                    <button className="ghost-btn user-menu__item" onClick={handleLogout} type="button">
                      <LogOut size={16} />
                      <span>Logout</span>
                    </button>
                  </div>
                ) : null}
              </div>
            )}

            <button className="primary-btn topbar__cta" onClick={() => navigate(isLanding ? "/app/analysis" : "/")} type="button">
              <span>{isLanding ? "Open Workspace" : "Back Home"}</span>
            </button>
          </div>
        </div>
      </header>

      {statusMessage ? <div className="status-banner">{statusMessage}</div> : null}

      <Routes>
        <Route
          path="/"
          element={
            <LandingPage
              user={user}
              testimonials={siteFeedback}
              onExploreWorkspace={() => navigate("/app/analysis")}
              onOpenAuth={openAuth}
              onOpenChat={() => navigate("/app/chat")}
            />
          }
        />
        <Route
          path="/app/:tab"
          element={
            <WorkspacePage
              user={user}
              authReady={!isBootstrappingAuth}
              reports={reports}
              chatHistory={chatHistory}
              chatTabs={chatTabs}
              onAnalyze={handleAnalyze}
              onChatSubmit={handleChatSubmit}
              onChatTabsChange={setChatTabs}
              onIngest={handleIngest}
              onOpenAuth={openAuth}
            />
          }
        />
      </Routes>

      {authOpen ? (
        <AuthModal
          mode={authMode}
          onClose={() => setAuthOpen(false)}
          onAuthenticated={(payload) => {
            setAuthOpen(false);
            if (payload?.otpSession) {
              saveOtpSession(payload.otpSession);
              setOtpSession(payload.otpSession);
              saveAuthUserSnapshot(payload.otpSession.user || null);
              setUser(payload.otpSession.user || null);
            }
            if (payload?.user && !payload?.otpSession) {
              clearOtpSession();
              setOtpSession(null);
              saveAuthUserSnapshot(payload.user);
              setUser(payload.user);
            }
          }}
        />
      ) : null}

      {feedbackOpen ? (
        <div className="modal-overlay">
          <div className="feedback-modal" onClick={(event) => event.stopPropagation()}>
            <div className="feedback-modal__intro">
              <span className="eyebrow">Required feedback</span>
              <h2>How was your HealthNova experience?</h2>
              <p>You have used HealthNova for 10 minutes. Please submit this one-time feedback form to continue. Once submitted, it will not be asked again for this account.</p>
            </div>

            <form className="feedback-form" onSubmit={handleFeedbackSubmit}>
              <label className="form-field">
                <span>Your name</span>
                <input
                  type="text"
                  value={feedbackForm.name}
                  onChange={(event) => setFeedbackForm((current) => ({ ...current, name: event.target.value }))}
                  placeholder="Your name"
                  disabled={feedbackSubmitting}
                  required
                />
              </label>

              <label className="form-field">
                <span>Your context</span>
                <input
                  type="text"
                  value={feedbackForm.role}
                  onChange={(event) => setFeedbackForm((current) => ({ ...current, role: event.target.value }))}
                  placeholder="Monitoring thyroid labs, caregiver, etc."
                  disabled={feedbackSubmitting}
                />
              </label>

              <div className="form-field">
                <span>Your rating</span>
                <div className="feedback-stars" role="radiogroup" aria-label="Feedback rating">
                  {[1, 2, 3, 4, 5].map((value) => (
                    <button
                      key={value}
                      className={`feedback-star ${feedbackForm.rating >= value ? "is-active" : ""}`}
                      onClick={() => setFeedbackForm((current) => ({ ...current, rating: value }))}
                      type="button"
                      aria-label={`${value} star${value > 1 ? "s" : ""}`}
                      disabled={feedbackSubmitting}
                    >
                      <Star size={18} fill={feedbackForm.rating >= value ? "currentColor" : "none"} />
                    </button>
                  ))}
                </div>
              </div>

              <label className="form-field">
                <span>Your feedback</span>
                <textarea
                  rows="4"
                  value={feedbackForm.quote}
                  onChange={(event) => setFeedbackForm((current) => ({ ...current, quote: event.target.value }))}
                  placeholder="Tell us what helped or what felt clear."
                  disabled={feedbackSubmitting}
                  required
                />
              </label>

              {feedbackError ? <div className="auth-alert auth-alert--error">{feedbackError}</div> : null}

              <div className="feedback-form__actions">
                <button className="primary-btn" type="submit" disabled={feedbackSubmitting}>
                  <span>{feedbackSubmitting ? "Submitting..." : "Submit feedback"}</span>
                </button>
              </div>
            </form>
          </div>
        </div>
      ) : null}
    </div>
  );
}

export default App;

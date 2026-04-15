import { useEffect, useMemo, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import {
  AlertCircle,
  Bot,
  Camera,
  Check,
  ClipboardList,
  Copy,
  Download,
  FileText,
  FileUp,
  FlaskConical,
  HeartPulse,
  History,
  Image as ImageIcon,
  Languages,
  LoaderCircle,
  LockKeyhole,
  LocateFixed,
  MapPin,
  MessageCircleHeart,
  Mic,
  RefreshCcw,
  SendHorizonal,
  ShieldCheck,
  Sparkles,
  TriangleAlert,
  Upload,
  Volume2,
  X,
  Zap,
} from "lucide-react";
import { chatWithAssistant, findNearbyDoctors, translateAnalysisToHindi } from "../services/api";
import "./workspace.css";

const REPORT_HISTORY_WINDOW_MS = 24 * 60 * 60 * 1000;
const CHAT_STORAGE_PREFIX = "healthnova-chat-tabs";
const CHAT_TABS_WINDOW_MS = 24 * 60 * 60 * 1000;
const MAX_CHAT_TABS = 8;
const CHAT_VOICE_MAX_MS = 5 * 60 * 1000;
const MAX_VISIBLE_MEASURES = 64;
const REPORT_TYPE_SUGGESTIONS = [
  "Blood work",
  "CBC",
  "Thyroid",
  "Kidney panel",
  "Liver panel",
  "X-ray report",
  "ECG",
  "Ultrasound",
  "CT scan",
  "MRI",
];
const BLOCKED_UPLOAD_EXTENSIONS = [".gif", ".mp4", ".mov", ".avi", ".mkv", ".webm", ".mpeg", ".mpg", ".wmv", ".m4v"];
const CHAT_SUGGESTION_GROUPS = ["Suggested", "Symptoms", "Reports", "Medicines", "Next steps"];
const CHAT_SUGGESTED_PROMPTS = [
  "Explain this report in simple language.",
  "Which values need closer follow-up?",
  "What should I ask my doctor next?",
];
const MARKER_REFERENCE_RULES = {
  Hemoglobin: { low: 12, high: 17.5 },
  WBC: { low: 4, high: 11, scaleUpToThousands: true },
  RBC: { low: 3.8, high: 6.2 },
  "Packed Cell Volume (PCV)": { low: 36, high: 53 },
  "Platelet Count": { low: 150, high: 450, allowLargeCounts: true },
  MCV: { low: 80, high: 100 },
  MCH: { low: 27, high: 33 },
  MCHC: { low: 32, high: 36 },
  RDW: { low: 11.5, high: 14.5 },
  MPV: { low: 7, high: 12.5 },
  Neutrophils: { low: 40, high: 75 },
  Lymphocytes: { low: 20, high: 45 },
  Monocytes: { low: 2, high: 10 },
  Eosinophils: { low: 0, high: 6 },
  Basophils: { low: 0, high: 2 },
  Glucose: { low: 70, high: 140 },
  HbA1c: { low: 4, high: 6.4 },
  Creatinine: { low: 0.5, high: 1.3 },
  Urea: { low: 10, high: 50 },
  TSH: { low: 0.4, high: 4.5 },
  T3: { low: 0.6, high: 2.0 },
  T4: { low: 4.5, high: 12.5 },
  Sodium: { low: 135, high: 145 },
  Potassium: { low: 3.5, high: 5.1 },
  Calcium: { low: 8.5, high: 10.5 },
  Bilirubin: { low: 0.1, high: 1.2 },
  ALT: { low: 0, high: 56 },
  AST: { low: 0, high: 40 },
  ALP: { low: 44, high: 147 },
  Cholesterol: { low: 0, high: 200 },
  LDL: { low: 0, high: 130 },
  HDL: { low: 40, high: 100, lowerIsWorse: true },
  Triglycerides: { low: 0, high: 150 },
  "Uric Acid": { low: 3, high: 7.2 },
  "Vitamin D": { low: 20, high: 100 },
  "Vitamin B12": { low: 200, high: 900 },
  Ferritin: { low: 15, high: 300 },
  Iron: { low: 60, high: 170 },
  CRP: { low: 0, high: 10 },
  ESR: { low: 0, high: 20 },
  "Heart Rate": { low: 60, high: 100 },
  "PR Interval": { low: 120, high: 200 },
  "QRS Duration": { low: 60, high: 120 },
  "QTc Interval": { low: 350, high: 450 },
  QTc: { low: 350, high: 450 },
  BP: { low: 90, high: 140 },
  SpO2: { low: 95, high: 100, lowerIsWorse: true },
};

function safeText(value) {
  return typeof value === "string" ? value.trim() : "";
}

function safeArray(value) {
  return Array.isArray(value) ? value : [];
}

function isLabLikeReportType(reportType = "") {
  const text = `${reportType || ""}`.toLowerCase();
  return /\b(cbc|blood|thyroid|kidney|liver|glucose|hb|hba1c|lipid|lab|biochemistry|hematology)\b/.test(text);
}

function isWithinLast24Hours(value) {
  const timestamp = new Date(value || 0).getTime();
  return Number.isFinite(timestamp) && Date.now() - timestamp <= REPORT_HISTORY_WINDOW_MS;
}

function formatReportDate(value) {
  if (!value) return "Just now";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "Just now";
  return new Intl.DateTimeFormat("en-IN", {
    day: "numeric",
    month: "short",
    year: "numeric",
    hour: "numeric",
    minute: "2-digit",
  }).format(date);
}

function getChatStorageKey(user) {
  const identity = safeText(user?.uid) || safeText(user?.email) || "guest";
  return `${CHAT_STORAGE_PREFIX}:${identity.toLowerCase()}`;
}

function isWithinChatWindow(value) {
  const timestamp = new Date(value || 0).getTime();
  return Number.isFinite(timestamp) && Date.now() - timestamp <= CHAT_TABS_WINDOW_MS;
}

function normalizeChatMessageRecord(message) {
  const role = safeText(message?.role) === "assistant" ? "assistant" : "user";
  const content = safeText(message?.content);
  const createdAt = safeText(message?.createdAt) || new Date().toISOString();
  if (!content || !isWithinChatWindow(createdAt)) return null;
  return {
    id: safeText(message?.id) || `${role}-${createdAt}-${content.slice(0, 18)}`,
    role,
    content,
    createdAt,
  };
}

function buildChatTabLabel(messages, fallbackLabel = "New chat") {
  const firstUserMessage = safeArray(messages).find((item) => item?.role === "user" && safeText(item?.content));
  if (!firstUserMessage) return fallbackLabel;
  const text = safeText(firstUserMessage.content).replace(/\s+/g, " ");
  return text.length > 24 ? `${text.slice(0, 24).trim()}...` : text;
}

function createChatTab(messages = [], label = "New chat") {
  const normalizedMessages = safeArray(messages).map(normalizeChatMessageRecord).filter(Boolean);
  const updatedAt =
    normalizedMessages[normalizedMessages.length - 1]?.createdAt || new Date().toISOString();
  return {
    id: globalThis.crypto?.randomUUID?.() || `chat-${Date.now()}-${Math.random().toString(16).slice(2, 8)}`,
    label: buildChatTabLabel(normalizedMessages, label),
    createdAt: updatedAt,
    updatedAt,
    messages: normalizedMessages,
  };
}

function trimChatTabs(tabs) {
  const normalizedTabs = safeArray(tabs)
    .map((tab, index) => {
      const messages = safeArray(tab?.messages).map(normalizeChatMessageRecord).filter(Boolean).slice(-60);
      const updatedAt = safeText(tab?.updatedAt) || messages[messages.length - 1]?.createdAt || safeText(tab?.createdAt);
      if (!messages.length && !isWithinChatWindow(updatedAt)) return null;
      return {
        id: safeText(tab?.id) || `chat-tab-${index}`,
        label: buildChatTabLabel(messages, safeText(tab?.label) || `Chat ${index + 1}`),
        createdAt: safeText(tab?.createdAt) || updatedAt || new Date().toISOString(),
        updatedAt: updatedAt || new Date().toISOString(),
        messages,
      };
    })
    .filter((tab) => tab && isWithinChatWindow(tab.updatedAt))
    .sort((left, right) => new Date(right.updatedAt || 0).getTime() - new Date(left.updatedAt || 0).getTime());

  return normalizedTabs.slice(0, MAX_CHAT_TABS);
}

function loadStoredChatTabs(storageKey, fallbackMessages = []) {
  if (typeof window === "undefined") {
    const initialTab = createChatTab(fallbackMessages, "Chat 1");
    return { tabs: [initialTab], activeId: initialTab.id };
  }

  try {
    const raw = window.localStorage.getItem(storageKey);
    const parsed = raw ? JSON.parse(raw) : null;
    const tabs = trimChatTabs(parsed?.tabs);
    const activeId = safeText(parsed?.activeId);
    if (tabs.length) {
      return {
        tabs,
        activeId: tabs.some((tab) => tab.id === activeId) ? activeId : tabs[0].id,
      };
    }
  } catch {}

  const fallbackTab = createChatTab(fallbackMessages, "Chat 1");
  return { tabs: [fallbackTab], activeId: fallbackTab.id };
}

function saveStoredChatTabs(storageKey, tabs, activeId) {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.setItem(storageKey, JSON.stringify({ tabs: trimChatTabs(tabs), activeId }));
  } catch {}
}

function isBlockedUploadFile(file) {
  const fileName = safeText(file?.name).toLowerCase();
  const contentType = safeText(file?.type).toLowerCase();
  return BLOCKED_UPLOAD_EXTENSIONS.some((extension) => fileName.endsWith(extension)) || contentType.startsWith("video/") || contentType === "image/gif";
}

function buildAnalysisSummaryFromReport(report) {
  if (!report) return {};
  const extractedValues = safeArray(report?.sections).find((section) => section?.title === "Extracted values")?.items || [];
  return {
    title: safeText(report?.title),
    summary: safeText(report?.summary),
    risk_level: safeText(report?.riskLevel),
    confidence_level: safeText(report?.confidenceLevel),
    doctor_specialist: safeText(report?.doctorSpecialist),
    report_type: safeText(report?.reportType),
    extracted_values: extractedValues.reduce((acc, item) => {
      if (safeText(item?.label) && safeText(item?.value)) acc[item.label] = item.value;
      return acc;
    }, {}),
  };
}

function serializeChatTabs(tabs) {
  try {
    return JSON.stringify(trimChatTabs(tabs));
  } catch {
    return "[]";
  }
}

function normalizeRiskLevel(value) {
  const text = safeText(value).toLowerCase();
  if (/(critical|emergency|urgent)/.test(text)) return "critical";
  if (/(high|severe)/.test(text)) return "high";
  if (/(moderate|medium|watch|borderline)/.test(text)) return "moderate";
  return "low";
}

function getVerdictCopy(riskLevel) {
  if (riskLevel === "critical") {
    return {
      title: "Critical concern",
      body: "This report needs urgent medical review. Please contact a clinician right away.",
    };
  }
  if (riskLevel === "high") {
    return {
      title: "High concern",
      body: "This report suggests something important may need medical follow-up soon.",
    };
  }
  if (riskLevel === "moderate") {
    return {
      title: "Moderate concern",
      body: "Some findings may need follow-up, but they are usually best interpreted with symptoms and medical history.",
    };
  }
  return {
    title: "Lower concern",
    body: "Nothing here looks immediately alarming, though a doctor should still review the full clinical picture.",
  };
}

function getSection(report, title) {
  return safeArray(report?.sections).find((section) => safeText(section?.title).toLowerCase() === title.toLowerCase()) || null;
}

function getSectionItems(report, title) {
  return safeArray(getSection(report, title)?.items);
}

function parseMarkerStatus(item) {
  const text = normalizeOcrText(`${safeText(item?.label)} ${safeText(item?.value)}`).toLowerCase();
  if (/(critical low|critically low)/.test(text)) return "critical_low";
  if (/(critical high|critically high)/.test(text)) return "critical_high";
  if (/\blow\b/.test(text)) return "low";
  if (/\bhigh\b/.test(text) || /\belevated\b/.test(text)) return "high";
  return inferMarkerStatusFromValue(item?.label, item?.value);
}

function extractNumericValue(value) {
  const text = cleanMarkerValue(value);
  if (!text) return null;
  const match = text.match(/[-+]?\d*\.?\d+/);
  if (!match) return null;
  const parsed = Number(match[0]);
  return Number.isFinite(parsed) ? parsed : null;
}

function inferMarkerStatusFromValue(label, value) {
  const normalizedName = normalizeMarkerName(label);
  const normalizedText = normalizeOcrText(`${value || ""}`).toLowerCase();

  if (!normalizedName) return "normal";
  if (/tachycardia|st elevation|st depression|t wave inversion|fracture|effusion|opacity|consolidation|lesion|mass|nodule|positive/.test(normalizedText)) {
    return "high";
  }
  if (/bradycardia|negative for acute abnormality|normal sinus rhythm|within normal limits|unremarkable|negative/.test(normalizedText)) {
    return "normal";
  }

  const numericValue = extractNumericValue(value);
  const rules = MARKER_REFERENCE_RULES[normalizedName];
  if (!rules || numericValue == null) return "normal";

  let comparableValue = numericValue;
  if (rules.scaleUpToThousands && comparableValue > 1000) {
    comparableValue = comparableValue / 1000;
  }
  if (rules.allowLargeCounts && comparableValue > 5000) {
    comparableValue = comparableValue / 1000;
  }

  if (rules.lowerIsWorse) {
    if (comparableValue < rules.low) return comparableValue < rules.low * 0.85 ? "critical_low" : "low";
    if (comparableValue > rules.high) return comparableValue > rules.high * 1.1 ? "critical_high" : "high";
    return "normal";
  }

  if (comparableValue < rules.low) return comparableValue < rules.low * 0.8 ? "critical_low" : "low";
  if (comparableValue > rules.high) return comparableValue > rules.high * 1.2 ? "critical_high" : "high";
  return "normal";
}

function normalizeOcrText(value) {
  return safeText(value)
    .replace(/0/g, "o")
    .replace(/1/g, "l")
    .replace(/5(?=[a-z])/gi, "s")
    .replace(/\s+/g, " ")
    .trim();
}

function normalizeMarkerName(name) {
  const raw = normalizeOcrText(name).toLowerCase().replace(/[^\w\s]/g, " ").replace(/\s+/g, " ").trim();
  if (!raw) return "";

  const contains = (needle) => raw.includes(needle);

  if (contains("hemoglobin") || raw === "hb" || contains("haemoglobin")) return "Hemoglobin";
  if (raw === "wbc" || contains("white blood cell") || contains("wbc count") || contains("total wbc")) return "WBC";
  if (raw === "rbc" || contains("red blood cell") || contains("rbc count") || contains("total rbc")) return "RBC";
  if (contains("packed cell volume") || raw === "pcv" || contains("hematocrit") || contains("haematocrit")) {
    return "Packed Cell Volume (PCV)";
  }
  if (contains("platelet")) return "Platelet Count";
  if (raw === "esr" || contains("erythrocyte sedimentation rate")) return "ESR";
  if (contains("lymphocyte") || contains("lympho cytes") || raw === "lymph") return "Lymphocytes";
  if (contains("neutrophil")) return "Neutrophils";
  if (contains("monocyte")) return "Monocytes";
  if (contains("eosinophil")) return "Eosinophils";
  if (contains("basophil")) return "Basophils";
  if (contains("glucose")) return "Glucose";
  if (contains("hba1c") || contains("glycated hemoglobin")) return "HbA1c";
  if (contains("creatinine")) return "Creatinine";
  if (contains("blood urea") || raw === "urea" || raw === "bun") return "Urea";
  if (contains("bilirubin")) return "Bilirubin";
  if (raw === "alt" || contains("alanine aminotransferase") || contains("sgpt")) return "ALT";
  if (raw === "ast" || contains("aspartate aminotransferase") || contains("sgot")) return "AST";
  if (raw === "alp" || contains("alkaline phosphatase")) return "ALP";
  if (contains("cholesterol")) return "Cholesterol";
  if (raw === "ldl" || contains("ldl cholesterol")) return "LDL";
  if (raw === "hdl" || contains("hdl cholesterol")) return "HDL";
  if (contains("triglyceride")) return "Triglycerides";
  if (contains("uric acid")) return "Uric Acid";
  if (contains("vitamin d")) return "Vitamin D";
  if (contains("vitamin b12") || raw === "b12") return "Vitamin B12";
  if (contains("ferritin")) return "Ferritin";
  if (raw === "crp" || contains("c reactive protein")) return "CRP";
  if (raw === "tsh") return "TSH";
  if (raw === "t3") return "T3";
  if (raw === "t4") return "T4";
  if (contains("heart rate") || raw === "hr" || raw === "pulse") return "Heart Rate";
  if (contains("pr interval")) return "PR Interval";
  if (contains("qrs duration") || raw === "qrs") return "QRS Duration";
  if (contains("qtc interval") || raw === "qtc") return "QTc Interval";
  if (contains("spo2") || contains("oxygen saturation")) return "SpO2";
  if (raw === "bp" || contains("blood pressure")) return "BP";
  if (contains("rhythm")) return "Rhythm";
  if (contains("st t changes") || contains("st-t changes")) return "ST-T Changes";
  if (raw === "mcv" || contains(" mcv") || contains("mcv ") || contains("mean corpuscular volume") || contains("volume mcv")) return "MCV";
  if (raw === "mch" || contains(" mch") || contains("mch ") || contains("mean corpuscular hemoglobin")) return "MCH";
  if (raw === "mchc" || contains(" mchc") || contains("mchc ") || contains("mean corpuscular hemoglobin concentration")) return "MCHC";
  if (raw === "rdw" || contains(" rdw") || contains("rdw ") || contains("red cell distribution width")) return "RDW";
  if (raw === "mpv" || contains(" mpv") || contains("mpv ") || contains("mean platelet volume")) return "MPV";

  return raw
    .split(" ")
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

function cleanMarkerValue(value) {
  return safeText(value)
    .replace(/\s+/g, " ")
    .replace(/\bhigh\b/gi, "High")
    .replace(/\blow\b/gi, "Low")
    .trim();
}

function extractDisplayMarkerValue(value) {
  const cleaned = cleanMarkerValue(value);
  if (!cleaned) return "Not available";
  const numericMatch = cleaned.match(/[-+]?\d*\.?\d+/);
  if (numericMatch) return numericMatch[0];
  if (/positive/i.test(cleaned)) return "Positive";
  if (/negative/i.test(cleaned)) return "Negative";
  return cleaned;
}

function isLikelyNoiseMarker(name, value) {
  const cleanedName = normalizeOcrText(name).toLowerCase();
  const cleanedValue = normalizeOcrText(value).toLowerCase();
  const normalizedName = normalizeMarkerName(name).toLowerCase();

  if (!cleanedName || cleanedName.length < 3) return true;
  if (/^[a-z]\s+[a-z]+$/.test(cleanedName)) return true;
  if (/shivam|bungal|mindray|mumbai|hospital|laboratory|pathology|diagnostic|print|page/.test(cleanedName)) return true;
  if (/^[a-z\s)]+$/.test(cleanedName) && cleanedName.length <= 5) return true;
  if (!/\d/.test(cleanedValue) && !/high|low|normal/.test(cleanedValue)) return true;
  if (/\b\d{5,}\b/.test(cleanedValue) && !/high|low|normal/.test(cleanedValue)) return true;
  if (!isRecognizedMeasure(normalizedName) && !/high|low|critical/.test(cleanedValue) && cleanedName.split(" ").length <= 2 && !/\d/.test(cleanedName)) {
    return true;
  }

  return false;
}

function markerPriority(marker) {
  let score = marker.important ? 4 : 0;
  if (marker.status === "critical_high" || marker.status === "critical_low") score += 5;
  else if (marker.status === "high" || marker.status === "low") score += 4;
  if (/\d/.test(marker.value)) score += 1;
  return score;
}

function isImportantMeasure(name, status) {
  const label = safeText(name).toLowerCase();
  if (!label) return false;
  if (status && status !== "normal") return true;

  return [
    "hemoglobin",
    "packed cell volume",
    "pcv",
    "glucose",
    "hba1c",
    "creatinine",
    "urea",
    "bun",
    "bilirubin",
    "alt",
    "ast",
    "alp",
    "tsh",
    "t3",
    "t4",
    "cholesterol",
    "ldl",
    "hdl",
    "triglycerides",
    "platelet",
    "wbc",
    "rbc",
    "mcv",
    "mch",
    "mchc",
    "rdw",
    "mpv",
    "sodium",
    "potassium",
    "calcium",
    "uric acid",
    "vitamin d",
    "vitamin b12",
    "ferritin",
    "iron",
    "crp",
    "esr",
    "heart rate",
    "pr interval",
    "qrs duration",
    "qtc interval",
    "rhythm",
    "st-t changes",
    "bp",
    "spo2",
  ].some((keyword) => label.includes(keyword));
}

function isRecognizedMeasure(name) {
  const label = safeText(name).toLowerCase();
  if (!label) return false;

  return [
    "hemoglobin",
    "packed cell volume (pcv)",
    "wbc",
    "rbc",
    "platelet count",
    "esr",
    "lymphocytes",
    "neutrophils",
    "monocytes",
    "eosinophils",
    "basophils",
    "glucose",
    "hba1c",
    "creatinine",
    "urea",
    "tsh",
    "t3",
    "t4",
    "mcv",
    "mch",
    "mchc",
    "rdw",
    "mpv",
    "sodium",
    "potassium",
    "calcium",
    "bilirubin",
    "alt",
    "ast",
    "alp",
    "cholesterol",
    "ldl",
    "hdl",
    "triglycerides",
    "uric acid",
    "vitamin d",
    "vitamin b12",
    "ferritin",
    "iron",
    "crp",
    "heart rate",
    "pr interval",
    "qrs duration",
    "qtc interval",
    "rhythm",
    "st-t changes",
    "bp",
    "spo2",
  ].includes(label);
}

function parseMarkersFromFindingText(text, index = 0) {
  const cleaned = normalizeOcrText(text);
  if (!cleaned) return [];

  const patterns = [
    { name: "Hemoglobin", regex: /(?:hemoglobin|haemoglobin|hb)[^0-9a-z]{0,10}([0-9][0-9a-z./-]*)/i },
    { name: "WBC", regex: /(?:total\s*)?(?:wbc|white blood cell)[^0-9a-z]{0,10}([0-9][0-9a-z./-]*)/i },
    { name: "RBC", regex: /(?:rbc|red blood cell)[^0-9a-z]{0,10}([0-9][0-9a-z./-]*)/i },
    { name: "Platelet count", regex: /(?:platelet(?:s)?(?: count)?|plt)[^0-9a-z]{0,10}([0-9][0-9a-z./-]*)/i },
    { name: "MCV", regex: /(?:mcv)[^0-9a-z]{0,10}([0-9][0-9a-z./-]*)/i },
    { name: "MCH", regex: /(?:mch)[^0-9a-z]{0,10}([0-9][0-9a-z./-]*)/i },
    { name: "MCHC", regex: /(?:mchc)[^0-9a-z]{0,10}([0-9][0-9a-z./-]*)/i },
    { name: "RDW", regex: /(?:rdw)[^0-9a-z]{0,10}([0-9][0-9a-z./-]*)/i },
    { name: "Glucose", regex: /(?:glucose)[^0-9a-z]{0,10}([0-9][0-9a-z./-]*)/i },
    { name: "HbA1c", regex: /(?:hba1c)[^0-9a-z]{0,10}([0-9][0-9a-z./-]*)/i },
    { name: "Creatinine", regex: /(?:creatinine)[^0-9a-z]{0,10}([0-9][0-9a-z./-]*)/i },
    { name: "TSH", regex: /(?:tsh)[^0-9a-z]{0,10}([0-9][0-9a-z./-]*)/i },
  ];

  return patterns
    .map((pattern, patternIndex) => {
      const match = cleaned.match(pattern.regex);
      if (!match?.[1]) return null;
      const rawValue = cleanMarkerValue(match[1]);
      return {
        id: `${pattern.name}-${index}-${patternIndex}`,
        name: pattern.name,
        value: extractDisplayMarkerValue(rawValue),
        rawValue: rawValue || "Not available",
        status: parseMarkerStatus({ value: cleaned }),
        important: true,
        recognized: true,
      };
    })
    .filter(Boolean);
}

function buildMarkers(report) {
  const extractedValues = getSectionItems(report, "Extracted values");
  const interpretedValues = getSectionItems(report, "Interpreted lab values");
  const source = extractedValues.length ? extractedValues : interpretedValues;

  let mapped = source
    .map((item, index) => {
      const rawName = safeText(item?.label) || `Marker ${index + 1}`;
      const rawValue = cleanMarkerValue(item?.value);
      const normalizedName = normalizeMarkerName(rawName);
      const status = parseMarkerStatus(item);

      return {
        id: `${normalizedName || rawName}-${index}`,
        name: normalizedName || rawName,
        value: extractDisplayMarkerValue(rawValue),
        rawValue: rawValue || "Not available",
        status,
        important: isImportantMeasure(normalizedName || rawName, status),
        recognized: isRecognizedMeasure(normalizedName || rawName),
      };
    })
    .filter((item) => !isLikelyNoiseMarker(item.name, item.value));

  if (!mapped.length) {
    mapped = getSectionItems(report, "Report findings")
      .flatMap((item, index) => parseMarkersFromFindingText(item?.value || item?.label, index))
      .filter((item) => !isLikelyNoiseMarker(item.name, item.value));
  }

  const deduped = [];
  const seen = new Map();

  for (const marker of mapped) {
    const key = marker.name.toLowerCase();
    const existingIndex = seen.get(key);

    if (existingIndex == null) {
      seen.set(key, deduped.length);
      deduped.push(marker);
      continue;
    }

    const existing = deduped[existingIndex];
    if (markerPriority(marker) > markerPriority(existing)) {
      deduped[existingIndex] = marker;
    }
  }

  return deduped
    .filter((item) => item.recognized || item.status !== "normal")
    .sort((left, right) => {
      const priorityDiff = markerPriority(right) - markerPriority(left);
      if (priorityDiff !== 0) return priorityDiff;
      return left.name.localeCompare(right.name);
    })
    .slice(0, MAX_VISIBLE_MEASURES);
}

function buildPossibleDiseases(report) {
  const items = getSectionItems(report, "Possible diseases").length
    ? getSectionItems(report, "Possible diseases")
    : getSectionItems(report, "Predicted conditions");

  return items.map((item, index) => {
    const combined = `${safeText(item?.label)} ${safeText(item?.value)}`.toLowerCase();
    let likelihood = "moderate";
    if (/(high|strong|likely)/.test(combined)) likelihood = "high";
    if (/(low|less likely|unlikely)/.test(combined)) likelihood = "low";

    return {
      id: `${safeText(item?.label)}-${index}`,
      name: safeText(item?.label) || `Condition ${index + 1}`,
      explanation: safeText(item?.value),
      likelihood,
    };
  });
}

function buildPrecautions(report) {
  return getSectionItems(report, "Precautions").map((item, index) => {
    const value = safeText(item?.value);
    const lower = value.toLowerCase();
    let urgency = "routine";
    if (/(urgent|immediate|emergency|today)/.test(lower)) urgency = "immediate";
    else if (/(soon|within|prompt)/.test(lower)) urgency = "soon";

    return {
      id: `${safeText(item?.label)}-${index}`,
      title: safeText(item?.label) || `Precaution ${index + 1}`,
      detail: value,
      urgency,
    };
  });
}

function buildHomeRemedies(report) {
  const diet = getSectionItems(report, "Diet recommendations").map((item, index) => ({
    id: `diet-${index}`,
    title: safeText(item?.label) || `Diet ${index + 1}`,
    detail: safeText(item?.value),
    category: "diet",
  }));

  const lifestyle = getSectionItems(report, "Lifestyle changes").map((item, index) => ({
    id: `lifestyle-${index}`,
    title: safeText(item?.label) || `Lifestyle ${index + 1}`,
    detail: safeText(item?.value),
    category: "lifestyle",
  }));

  return [...diet, ...lifestyle];
}

function buildRecommendedTests(report) {
  const items = getSectionItems(report, "Next tests to confirm").length
    ? getSectionItems(report, "Next tests to confirm")
    : getSectionItems(report, "Recommended tests");

  return items.map((item, index) => ({
    id: `${safeText(item?.label)}-${index}`,
    test: safeText(item?.label) || `Recommended test ${index + 1}`,
    reason: safeText(item?.value),
  }));
}

function buildFallbackRecommendedTests(report, markers) {
  if (getSectionItems(report, "Next tests to confirm").length || getSectionItems(report, "Recommended tests").length) {
    return [];
  }

  const reportType = safeText(report?.reportType).toLowerCase();
  const abnormal = safeArray(markers).filter((item) => item.status !== "normal");
  const tests = [];

  if (abnormal.some((item) => /hemoglobin|rbc|packed cell volume|pcv|mcv|mch|mchc|rdw/i.test(item.name))) {
    tests.push({
      id: "fallback-cbc-repeat",
      test: "Repeat CBC",
      reason: "A repeat complete blood count can confirm whether the abnormal blood indices persist.",
    });
  }
  if (abnormal.some((item) => /glucose|hba1c/i.test(item.name))) {
    tests.push({
      id: "fallback-sugar",
      test: "Fasting glucose / HbA1c review",
      reason: "Repeat sugar testing can help confirm whether the glucose pattern is persistent.",
    });
  }
  if (abnormal.some((item) => /creatinine|urea|sodium|potassium|calcium/i.test(item.name))) {
    tests.push({
      id: "fallback-metabolic",
      test: "Kidney function and electrolyte panel",
      reason: "Follow-up chemistry testing may help clarify whether the abnormal values are clinically significant.",
    });
  }

  if (!abnormal.length && /(x-ray|xray|ecg|echo|mri|ct|ultrasound|scan|imaging)/i.test(reportType)) {
    tests.push({
      id: "fallback-imaging-review",
      test: "Clinical review of the report and symptoms",
      reason: "Imaging and ECG reports are best confirmed with a doctor who can match the written findings with symptoms and exam.",
    });
  }

  if (!tests.length) {
    tests.push({
      id: "fallback-doctor-review",
      test: isLabLikeReportType(reportType) ? "Doctor review with repeat relevant labs" : "Doctor review with report-specific follow-up",
      reason: "A clinician can decide which follow-up steps or tests are needed based on symptoms, history, and the uploaded report.",
    });
  }

  return tests;
}

function buildFallbackHomeRemedies(report, markers) {
  if (getSectionItems(report, "Diet recommendations").length || getSectionItems(report, "Lifestyle changes").length) {
    return [];
  }

  const abnormal = safeArray(markers).filter((item) => item.status !== "normal");
  const remedies = [
    {
      id: "fallback-hydration",
      title: "Hydration and routine monitoring",
      detail: "Stay well hydrated and keep a simple note of symptoms, medications, and repeat lab dates before your doctor visit.",
      category: "lifestyle",
    },
  ];

  if (abnormal.some((item) => /glucose|hba1c|cholesterol|triglycerides/i.test(item.name))) {
    remedies.push({
      id: "fallback-diet",
      title: "Balanced meals",
      detail: "Prefer regular meals with less refined sugar and more fiber-rich foods until a doctor reviews the report.",
      category: "diet",
    });
  }

  if (abnormal.some((item) => /hemoglobin|rbc|packed cell volume|pcv|platelet/i.test(item.name))) {
    remedies.push({
      id: "fallback-effort",
      title: "Avoid overexertion if symptomatic",
      detail: "If you feel weak, dizzy, or short of breath, avoid strenuous activity until your clinician reviews the results.",
      category: "lifestyle",
    });
  }

  return remedies.slice(0, 4);
}

function buildFallbackPrecautions(report, markers) {
  if (getSectionItems(report, "Precautions").length) return [];

  const reportType = safeText(report?.reportType).toLowerCase();
  const abnormal = safeArray(markers).filter((item) => item.status !== "normal");
  const precautions = [
    {
      id: "fallback-precaution-review",
      title: "Arrange follow-up review",
      detail: "Take this report to a qualified doctor so the values can be interpreted with symptoms and history.",
      urgency: abnormal.length ? "soon" : "routine",
    },
  ];

  if (abnormal.some((item) => item.status === "high" || item.status === "critical_high" || item.status === "critical_low")) {
    precautions.unshift({
      id: "fallback-red-flags",
      title: "Seek urgent care for red-flag symptoms",
      detail: "Get urgent medical help if you develop severe weakness, chest pain, fainting, breathing trouble, or persistent vomiting.",
      urgency: "immediate",
    });
  }

  if (!abnormal.length && /(x-ray|xray|ecg|echo|mri|ct|ultrasound|scan|imaging)/i.test(reportType)) {
    precautions.unshift({
      id: "fallback-report-carry",
      title: "Keep the full report for review",
      detail: "Take the original imaging or ECG report to your doctor so the written impression can be checked with your symptoms.",
      urgency: "soon",
    });
  }

  return precautions.slice(0, 4);
}

function buildFallbackPossibleDiseases(report, markers) {
  if (getSectionItems(report, "Possible diseases").length || getSectionItems(report, "Predicted conditions").length) {
    return [];
  }

  const abnormal = safeArray(markers).filter((item) => item.status !== "normal");
  if (!abnormal.length) return [];

  return [
    {
      id: "fallback-pattern",
      name: "Pattern needs clinical confirmation",
      explanation: `The abnormal measures (${abnormal.slice(0, 3).map((item) => item.name).join(", ")}) suggest a pattern that should be confirmed by a clinician rather than treated as a final diagnosis.`,
      likelihood: "moderate",
    },
  ];
}

function isClinicalFindingLine(text) {
  const cleaned = normalizeOcrText(text).toLowerCase();
  if (!cleaned) return false;

  if (
    /patna|pathology|smart vision|complex|bhagwat|nagar|opposite|infotech|accurate|caring|instant|sample collected|registered|age|phone|mobile|mumbai|mindray|kumar|address|reporting time|collected at/.test(
      cleaned
    )
  ) {
    return false;
  }

  if (
    /(impression|finding|findings|ecg|x-ray|xray|ultrasound|mri|ct scan|ct|radiograph|sinus rhythm|tachycardia|bradycardia|cardiomegaly|effusion|opacity|infiltrate|fracture|normal study|no acute|abnormal|degenerative|lesion|consolidation|axis deviation|st elevation|t wave|qrs|qtc)/.test(
      cleaned
    )
  ) {
    return true;
  }

  if (!/\d/.test(cleaned)) return false;

  return /(hemoglobin|hb|rbc|wbc|pcv|packed cell volume|platelet|esr|mcv|mch|mchc|rdw|mpv|neutroph|lymph|monocyte|eosinoph|basoph|glucose|hba1c|creatinine|urea|bilirubin|alt|ast|alp|cholesterol|ldl|hdl|triglycerides|vitamin|ferritin|iron|crp|tsh|t3|t4|high|low)/.test(
    cleaned
  );
}

function buildRelevantReportFindings(report) {
  const rawFindings = getSectionItems(report, "Report findings");
  return rawFindings
    .map((item, index) => {
      const value = safeText(item?.value || item?.label);
      if (!isClinicalFindingLine(value)) return null;
      return {
        label: `Clinical finding ${index + 1}`,
        value: normalizeOcrText(value),
      };
    })
    .filter(Boolean)
    .slice(0, 6);
}

function buildReportViewModel(report) {
  if (!report) return null;

  const reportType = report.reportType || report?.raw?.report_type || report.medium || "Medical report";
  const markers = buildMarkers(report);
  const possibleDiseases = [...buildPossibleDiseases(report), ...buildFallbackPossibleDiseases(report, markers)].slice(0, 6);
  const precautions = [...buildPrecautions(report), ...buildFallbackPrecautions(report, markers)].slice(0, 6);
  const homeRemedies = [...buildHomeRemedies(report), ...buildFallbackHomeRemedies(report, markers)].slice(0, 6);
  const recommendedTests = [...buildRecommendedTests(report), ...buildFallbackRecommendedTests(report, markers)].slice(0, 6);
  const reportFindings = buildRelevantReportFindings(report);
  const supportingContext = getSectionItems(report, "Supporting context");
  const riskLevel = normalizeRiskLevel(report?.riskLevel || report?.raw?.risk_level || "");

  return {
    id: report.id,
    analyzedAt: report.createdAt,
    reportType,
    title: report.title || report.fileName || "Medical report",
    summary: safeText(report.summary || report.clinicalExplanation || report.evidenceSummary || "Analysis completed."),
    doctorSpecialist: safeText(report.doctorSpecialist || report?.raw?.doctor_specialist || "Relevant specialist"),
    confidenceLevel: safeText(report.confidenceLevel || report.displayConfidence || "Preliminary"),
    disclaimer: safeText(report.disclaimer || "This is AI-assisted guidance and does not replace clinician review."),
    patientName: safeText(report.patientName),
    markers: isLabLikeReportType(reportType) ? markers : markers,
    possibleDiseases,
    precautions,
    homeRemedies,
    recommendedTests,
    reportFindings,
    supportingContext,
    dietaryAdvice: homeRemedies.filter((item) => item.category === "diet").map((item) => item.detail).join(" "),
    exerciseAdvice: homeRemedies.filter((item) => item.category === "lifestyle").map((item) => item.detail).join(" "),
    riskLevel,
  };
}

function buildDownloadHtml(analysis, user) {
  return `<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>HealthNova Report</title>
  <style>
    body{font-family:system-ui,sans-serif;max-width:900px;margin:2rem auto;padding:0 1rem;color:#163458}
    h1,h2{color:#0e2340}
    .card{border:1px solid #d9edf2;border-radius:14px;padding:1rem;margin:1rem 0;background:#fff}
    table{width:100%;border-collapse:collapse}
    th,td{border:1px solid #d9edf2;padding:.65rem;text-align:left}
    th{background:#eef8fb}
    .note{background:#fff7e6;border-color:#f8d88c}
  </style>
</head>
<body>
  <h1>HealthNova Report</h1>
  <p><strong>Patient:</strong> ${safeText(user?.name) || "Patient"}</p>
  <p><strong>Analyzed:</strong> ${formatReportDate(analysis.analyzedAt)}</p>
  <div class="card">
    <h2>Summary</h2>
    <p>${analysis.summary}</p>
    <p><strong>Risk:</strong> ${analysis.riskLevel}</p>
    <p><strong>Suggested specialist:</strong> ${analysis.doctorSpecialist}</p>
  </div>
  <div class="card">
    <h2>Extracted Values</h2>
    <table>
      <thead><tr><th>Test</th><th>Value</th><th>Status</th></tr></thead>
      <tbody>
        ${analysis.markers.map((marker) => `<tr><td>${marker.name}</td><td>${marker.value}</td><td>${marker.status}</td></tr>`).join("")}
      </tbody>
    </table>
  </div>
  <div class="card">
    <h2>Follow-up Tests</h2>
    ${analysis.recommendedTests.map((item) => `<p><strong>${item.test}</strong>: ${item.reason}</p>`).join("") || "<p>No follow-up tests listed.</p>"}
  </div>
  <div class="card note">
    <h2>Disclaimer</h2>
    <p>${analysis.disclaimer}</p>
  </div>
</body>
</html>`;
}

function buildSpeechText(analysis, language = "en", userName = "") {
  const greeting = language === "hi"
    ? `नमस्ते ${safeText(userName) || "user"}.`
    : `Hi ${safeText(userName) || "user"}.`;

  const disclaimer = language === "hi"
    ? "पहले एक छोटा डिस्क्लेमर. यह जानकारी केवल सामान्य समझ के लिए है, यह डॉक्टर की सलाह, निदान, या आपातकालीन देखभाल का विकल्प नहीं है."
    : "First, a quick disclaimer. This information is for general understanding only and does not replace a doctor's advice, diagnosis, or emergency care.";

  const summaryLead = language === "hi"
    ? "अब मैं आपका रिपोर्ट सारांश पढ़ रही हूँ."
    : "I will now read your report summary.";

  return [
    disclaimer,
    greeting,
    summaryLead,
    analysis?.summary,
    ...safeArray(analysis?.possibleDiseases).slice(0, 2).map((item) => `${item.name}. ${item.explanation}`),
    ...safeArray(analysis?.precautions).slice(0, 2).map((item) => `${item.title}. ${item.detail}`),
  ]
    .filter(Boolean)
    .join(". ");
}

function buildTranslationEntries(analysis, verdict) {
  if (!analysis) return [];

  return [
    analysis.summary,
    verdict?.title,
    verdict?.body,
    analysis.disclaimer,
    analysis.doctorSpecialist,
    "Dietary Advice",
    "Lifestyle Advice",
    "Recommended specialty",
    "Best matched from the current report summary and extracted findings.",
    "Take this report with you for review.",
    "Showing the most clinically relevant or abnormal values from the report instead of every extracted item.",
    "Status is taken from the uploaded report text when Low or High is explicitly present, then cleaned and deduplicated on the frontend.",
    ...safeArray(analysis.possibleDiseases).flatMap((item) => [item.name, item.explanation]),
    ...safeArray(analysis.precautions).flatMap((item) => [item.title, item.detail]),
    ...safeArray(analysis.homeRemedies).flatMap((item) => [item.title, item.detail, item.category]),
    ...safeArray(analysis.recommendedTests).flatMap((item) => [item.test, item.reason]),
    ...safeArray(analysis.reportFindings).flatMap((item) => [item.label, item.value]),
    ...safeArray(analysis.supportingContext).flatMap((item) => [item.label, item.value]),
  ].filter(Boolean);
}

function buildFriendlySpeechText(analysis, language = "en", userName = "") {
  const safeUser = safeText(userName) || "user";
  const greeting = `Hi ${safeUser}.`;
  const appIntro =
    "This application is for understanding medical reports, checking important values, and helping you know the next steps to discuss with your doctor.";
  const disclaimer =
    "First, a quick disclaimer. This information is for general understanding only and does not replace a doctor's advice, diagnosis, or emergency care.";
  const summaryLead =
    language === "hi" ? "I will now read your report summary in Hindi." : "I will now read your report summary.";

  return [
    greeting,
    appIntro,
    disclaimer,
    summaryLead,
    analysis?.summary,
    ...safeArray(analysis?.possibleDiseases).slice(0, 2).map((item) => `${item.name}. ${item.explanation}`),
    ...safeArray(analysis?.precautions).slice(0, 2).map((item) => `${item.title}. ${item.detail}`),
  ]
    .filter(Boolean)
    .join(". ");
}

function getPreferredVoice(language) {
  if (!window.speechSynthesis) return null;

  const voices = window.speechSynthesis.getVoices();
  if (!voices.length) return null;

  const preferredLocales = language === "hi" ? ["hi-in", "hi"] : ["en-in", "en-gb", "en-us", "en"];
  const femaleHints = [
    "female", "woman", "zira", "samantha", "heera", "veena", "priya", "karen", "aria", "susan",
    "hazel", "serena", "natasha", "ava", "jenny", "neerja", "swara", "raveena", "sonia", "ananya",
  ];
  const maleHints = ["male", "man", "david", "mark", "guy", "james", "richard", "alex", "daniel", "george"];

  const scoreVoice = (voice) => {
    const name = `${voice.name || ""}`.toLowerCase();
    const lang = `${voice.lang || ""}`.toLowerCase();
    let score = 0;

    const localeIndex = preferredLocales.findIndex((prefix) => lang.startsWith(prefix));
    if (localeIndex !== -1) score += 30 - localeIndex * 4;
    if (voice.localService) score += 4;
    if (femaleHints.some((hint) => name.includes(hint))) score += 18;
    if (maleHints.some((hint) => name.includes(hint))) score -= 8;
    if (/google|microsoft|natural|neural|premium|enhanced|online/.test(name)) score += 8;
    if (language !== "hi" && /(english|india|india english|uk english|us english)/.test(name)) score += 5;
    if (language === "hi" && /(hindi|india)/.test(name)) score += 5;

    return score;
  };

  return [...voices].sort((left, right) => scoreVoice(right) - scoreVoice(left))[0] || null;
}

function statusLabel(status, language) {
  const cleaned = safeText(status).replace(/_/g, " ").toLowerCase();
  if (language !== "hi") return cleaned;

  if (cleaned === "normal") return "सामान्य";
  if (cleaned === "high") return "उच्च";
  if (cleaned === "low") return "कम";
  if (cleaned === "critical high") return "बहुत अधिक";
  if (cleaned === "critical low") return "बहुत कम";
  return cleaned;
}

function getSpeechRecognitionCtor() {
  if (typeof window === "undefined") return null;
  return window.SpeechRecognition || window.webkitSpeechRecognition || null;
}

function buildChatReplySpeechText(text) {
  return safeText(text)
    .replace(/[*_`#>-]+/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

function renderLockedState(kind, onOpenAuth) {
  return (
    <div className="locked-state">
      <div className="locked-state__icon">
        <LockKeyhole size={30} />
      </div>
      <h3>{kind === "chat" ? "Private assistant" : "Private analysis"}</h3>
      <p>{kind === "chat" ? "Log in to chat about your reports." : "Log in to upload and analyze medical reports."}</p>
      <div className="locked-state__actions">
        <button className="primary-btn" onClick={() => onOpenAuth("signup")} type="button">
          Get started
        </button>
        <button className="ghost-btn" onClick={() => onOpenAuth("login")} type="button">
          Log in
        </button>
      </div>
    </div>
  );
}

function renderRestoringState() {
  return (
    <div className="restoring-state">
      <LoaderCircle className="spin" size={22} />
      <p>Restoring your workspace...</p>
    </div>
  );
}

export default function WorkspacePage({
  user,
  authReady = true,
  reports = [],
  chatHistory = [],
  chatTabs: persistedChatTabs = [],
  onAnalyze,
  onChatSubmit,
  onChatTabsChange,
  onIngest,
  onOpenAuth,
}) {
  const { tab = "analysis" } = useParams();
  const navigate = useNavigate();
  const activeTab = tab === "chat" ? "chat" : "analysis";
  const isLocked = authReady && !user;

  const fileInputRef = useRef(null);
  const cameraInputRef = useRef(null);
  const textareaRef = useRef(null);
  const chatThreadRef = useRef(null);
  const chatRecognitionRef = useRef(null);
  const chatVoiceTimerRef = useRef(null);
  const chatVoiceBaseRef = useRef("");
  const chatVoiceFinalRef = useRef("");
  const cameraVideoRef = useRef(null);
  const cameraStreamRef = useRef(null);

  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [form, setForm] = useState({
    patientName: "",
    reportType: "",
    notes: "",
    file: null,
  });
  const [isDragging, setIsDragging] = useState(false);
  const [selectedReportId, setSelectedReportId] = useState("");
  const [analysisLoading, setAnalysisLoading] = useState(false);
  const [analysisStage, setAnalysisStage] = useState("");
  const [analysisError, setAnalysisError] = useState("");
  const [latestResolvedReport, setLatestResolvedReport] = useState(null);
  const [ingestLoading, setIngestLoading] = useState(false);
  const [copyState, setCopyState] = useState("idle");
  const [listenState, setListenState] = useState("idle");
  const [analysisLanguage, setAnalysisLanguage] = useState("en");
  const [translationState, setTranslationState] = useState({
    loading: false,
    map: {},
  });
  const [doctorLocation, setDoctorLocation] = useState({
    status: "idle",
    latitude: null,
    longitude: null,
    error: "",
  });
  const [locationPermission, setLocationPermission] = useState("unknown");
  const [nearbyDoctorsState, setNearbyDoctorsState] = useState({
    loading: false,
    area: "",
    items: [],
    links: [],
    error: "",
  });
  const [chatInput, setChatInput] = useState("");
  const [chatLoading, setChatLoading] = useState(false);
  const [chatError, setChatError] = useState("");
  const [chatVoiceState, setChatVoiceState] = useState("idle");
  const [chatSpeakingId, setChatSpeakingId] = useState("");
  const chatStorageKey = useMemo(() => getChatStorageKey(user), [user]);
  const initialChatTabsState = useMemo(
    () => loadStoredChatTabs(chatStorageKey, chatHistory),
    [chatStorageKey, chatHistory]
  );
  const [chatTabs, setChatTabs] = useState(() =>
    trimChatTabs(persistedChatTabs).length ? trimChatTabs(persistedChatTabs) : initialChatTabsState.tabs
  );
  const [activeChatTabId, setActiveChatTabId] = useState(() =>
    trimChatTabs(persistedChatTabs).length ? trimChatTabs(persistedChatTabs)[0].id : initialChatTabsState.activeId
  );
  const [cameraOpen, setCameraOpen] = useState(false);
  const [cameraLoading, setCameraLoading] = useState(false);
  const [cameraError, setCameraError] = useState("");
  const [cameraFacingMode, setCameraFacingMode] = useState("environment");
  const [imagePreviewOpen, setImagePreviewOpen] = useState(false);

  const recentReports24h = useMemo(
    () => safeArray(reports).filter((item) => isWithinLast24Hours(item?.createdAt)).slice(0, 12),
    [reports]
  );

  const selectedReport = useMemo(() => {
    const fromReports = reports.find((item) => item.id === selectedReportId) || reports[0] || null;
    if (fromReports) return fromReports;
    return latestResolvedReport;
  }, [reports, selectedReportId, latestResolvedReport]);

  const analysis = useMemo(() => buildReportViewModel(selectedReport), [selectedReport]);
  const activeChatTab = useMemo(
    () => chatTabs.find((tabItem) => tabItem.id === activeChatTabId) || chatTabs[0] || null,
    [chatTabs, activeChatTabId]
  );
  const activeChatMessages = useMemo(() => safeArray(activeChatTab?.messages), [activeChatTab]);
  const chatScrollStateRef = useRef({
    tabId: "",
    messageCount: 0,
    lastMessageId: "",
  });
  const shouldShowStarterPrompts = activeChatMessages.length === 0;
  const abnormalMarkers = useMemo(
    () => safeArray(analysis?.markers).filter((item) => item.status !== "normal"),
    [analysis]
  );
  const filePreviewUrl = useMemo(() => {
    if (!form.file || !String(form.file.type || "").toLowerCase().startsWith("image/")) return "";
    return URL.createObjectURL(form.file);
  }, [form.file]);
  const hasImagePreview = Boolean(filePreviewUrl);

  useEffect(() => {
    if (!reports.length) {
      setSelectedReportId("");
      return;
    }
    setSelectedReportId((current) => (current && reports.some((item) => item.id === current) ? current : reports[0].id));
  }, [reports]);

  useEffect(() => {
    if (latestResolvedReport?.id && reports.some((item) => item.id === latestResolvedReport.id)) {
      setLatestResolvedReport(null);
    }
  }, [reports, latestResolvedReport]);

  useEffect(() => {
    const persistedTabs = trimChatTabs(persistedChatTabs);
    if (persistedTabs.length) {
      setChatTabs(persistedTabs);
      setActiveChatTabId((current) => (persistedTabs.some((tab) => tab.id === current) ? current : persistedTabs[0].id));
      return;
    }
    const { tabs, activeId } = loadStoredChatTabs(chatStorageKey, chatHistory);
    setChatTabs(tabs);
    setActiveChatTabId(activeId);
  }, [chatStorageKey, chatHistory, persistedChatTabs]);

  useEffect(() => {
    const trimmedTabs = trimChatTabs(chatTabs);
    const nextTabs = trimmedTabs.length ? trimmedTabs : [createChatTab([], "Chat 1")];
    const nextActiveId = nextTabs.some((tabItem) => tabItem.id === activeChatTabId) ? activeChatTabId : nextTabs[0].id;
    saveStoredChatTabs(chatStorageKey, nextTabs, nextActiveId);
    if (serializeChatTabs(nextTabs) !== serializeChatTabs(chatTabs)) setChatTabs(nextTabs);
    if (nextActiveId !== activeChatTabId) setActiveChatTabId(nextActiveId);
    if (serializeChatTabs(nextTabs) !== serializeChatTabs(persistedChatTabs)) {
      onChatTabsChange?.(nextTabs);
    }
  }, [chatTabs, activeChatTabId, chatStorageKey, onChatTabsChange, persistedChatTabs]);

  useEffect(() => {
    setSidebarOpen(false);
  }, [activeTab, selectedReportId]);

  useEffect(() => {
    if (activeTab !== "chat") return;
    const thread = chatThreadRef.current;
    if (!thread) return;
    const lastMessage = activeChatMessages[activeChatMessages.length - 1];
    const nextScrollState = {
      tabId: activeChatTabId,
      messageCount: activeChatMessages.length,
      lastMessageId: safeText(lastMessage?.id),
    };
    const previousScrollState = chatScrollStateRef.current;
    const tabChanged = previousScrollState.tabId !== nextScrollState.tabId;
    const messageChanged =
      previousScrollState.messageCount !== nextScrollState.messageCount ||
      previousScrollState.lastMessageId !== nextScrollState.lastMessageId;

    chatScrollStateRef.current = nextScrollState;
    if (!tabChanged && !messageChanged) return;

    const shouldSmoothScroll = !tabChanged && lastMessage?.role === "assistant";
    window.requestAnimationFrame(() => {
      thread.scrollTo({
        top: thread.scrollHeight,
        behavior: shouldSmoothScroll ? "smooth" : "auto",
      });
    });
  }, [activeTab, activeChatMessages, activeChatTabId]);

  useEffect(() => {
    if (copyState !== "done") return undefined;
    const timer = window.setTimeout(() => setCopyState("idle"), 1800);
    return () => window.clearTimeout(timer);
  }, [copyState]);

  useEffect(() => {
    setAnalysisLanguage("en");
    setTranslationState({ loading: false, map: {} });
    setListenState("idle");
    setDoctorLocation({ status: "idle", latitude: null, longitude: null, error: "" });
    setLocationPermission("unknown");
    setNearbyDoctorsState({ loading: false, area: "", items: [], links: [], error: "" });
    window.speechSynthesis?.cancel();
    if (chatRecognitionRef.current) {
      chatRecognitionRef.current.onresult = null;
      chatRecognitionRef.current.onend = null;
      chatRecognitionRef.current.onerror = null;
      chatRecognitionRef.current.stop();
      chatRecognitionRef.current = null;
    }
    if (chatVoiceTimerRef.current) {
      window.clearTimeout(chatVoiceTimerRef.current);
      chatVoiceTimerRef.current = null;
    }
    setChatVoiceState("idle");
    setChatSpeakingId("");
  }, [analysis?.id]);

  useEffect(
    () => () => {
      window.speechSynthesis?.cancel();
      if (chatRecognitionRef.current) {
        chatRecognitionRef.current.onresult = null;
        chatRecognitionRef.current.onend = null;
        chatRecognitionRef.current.onerror = null;
        chatRecognitionRef.current.stop();
        chatRecognitionRef.current = null;
      }
      if (chatVoiceTimerRef.current) {
        window.clearTimeout(chatVoiceTimerRef.current);
        chatVoiceTimerRef.current = null;
      }
    },
    []
  );

  useEffect(
    () => () => {
      if (filePreviewUrl) URL.revokeObjectURL(filePreviewUrl);
    },
    [filePreviewUrl]
  );

  useEffect(() => {
    if (!cameraOpen || !cameraVideoRef.current || !cameraStreamRef.current) return;
    cameraVideoRef.current.srcObject = cameraStreamRef.current;
    cameraVideoRef.current
      .play()
      .catch(() => {});
  }, [cameraOpen, cameraLoading]);

  useEffect(
    () => () => {
      if (cameraStreamRef.current) {
        cameraStreamRef.current.getTracks().forEach((track) => track.stop());
        cameraStreamRef.current = null;
      }
    },
    []
  );

  useEffect(() => {
    if (!window.navigator?.geolocation) {
      setLocationPermission("unsupported");
      return;
    }

    if (!window.navigator?.permissions?.query) {
      setLocationPermission("prompt");
      return;
    }

    let active = true;
    let permissionStatus;

    window.navigator.permissions
      .query({ name: "geolocation" })
      .then((status) => {
        if (!active) return;
        permissionStatus = status;
        setLocationPermission(status.state || "prompt");
        status.onchange = () => {
          if (!active) return;
          setLocationPermission(status.state || "prompt");
        };
      })
      .catch(() => {
        if (active) setLocationPermission("prompt");
      });

    return () => {
      active = false;
      if (permissionStatus) permissionStatus.onchange = null;
    };
  }, [analysis?.id]);

  useEffect(() => {
    if (locationPermission !== "granted") return;
    if (doctorLocation.status === "granted" || doctorLocation.status === "loading") return;
    requestDoctorLocation();
  }, [locationPermission, doctorLocation.status]);

  useEffect(() => {
    const textarea = textareaRef.current;
    if (!textarea) return;
    if (!chatInput.trim()) {
      textarea.style.height = "44px";
      return;
    }
    textarea.style.height = "44px";
    const nextHeight = Math.min(textarea.scrollHeight, 96);
    textarea.style.height = `${Math.max(nextHeight, 44)}px`;
  }, [chatInput]);

  function updateFile(file) {
    setAnalysisError("");
    setImagePreviewOpen(false);
    if (file && isBlockedUploadFile(file)) {
      setForm((current) => ({ ...current, file: null }));
      setAnalysisError("Video and GIF files are not supported. Upload a PDF, photo, or text-based report instead.");
      return;
    }
    setForm((current) => ({ ...current, file: file || null }));
  }

  function updateActiveChatTab(updater) {
    setChatTabs((current) =>
      current.map((tabItem) => {
        if (tabItem.id !== activeChatTabId) return tabItem;
        const nextTab = typeof updater === "function" ? updater(tabItem) : updater;
        return {
          ...tabItem,
          ...nextTab,
          messages: safeArray(nextTab?.messages ?? tabItem.messages).slice(-60),
          updatedAt: safeText(nextTab?.updatedAt) || new Date().toISOString(),
        };
      })
    );
  }

  function createNewChatTab() {
    const nextTabNumber = chatTabs.length + 1;
    const nextTab = createChatTab([], `Chat ${nextTabNumber}`);
    setChatTabs((current) => [nextTab, ...current].slice(0, MAX_CHAT_TABS));
    setActiveChatTabId(nextTab.id);
    setChatInput("");
    setChatError("");
    window.setTimeout(() => textareaRef.current?.focus(), 50);
  }

  function removeChatTab(tabId) {
    setChatTabs((current) => {
      const remaining = current.filter((tabItem) => tabItem.id !== tabId);
      if (!remaining.length) {
        const fallbackTab = createChatTab([], "Chat 1");
        setActiveChatTabId(fallbackTab.id);
        return [fallbackTab];
      }
      if (activeChatTabId === tabId) setActiveChatTabId(remaining[0].id);
      return remaining;
    });
  }

  function stopCameraStream() {
    if (cameraStreamRef.current) {
      cameraStreamRef.current.getTracks().forEach((track) => track.stop());
      cameraStreamRef.current = null;
    }
  }

  async function startCameraPreview(facingMode = "environment") {
    stopCameraStream();
    const stream = await window.navigator.mediaDevices.getUserMedia({
      video: {
        facingMode: { ideal: facingMode },
      },
      audio: false,
    });
    cameraStreamRef.current = stream;
    setCameraFacingMode(facingMode);
  }

  function closeCameraModal() {
    stopCameraStream();
    setCameraOpen(false);
    setCameraLoading(false);
    setCameraError("");
  }

  async function openCameraModal() {
    setCameraError("");
    setCameraOpen(true);
    setCameraLoading(true);

    if (!window.navigator?.mediaDevices?.getUserMedia) {
      setCameraLoading(false);
      setCameraError("Live camera preview is not supported in this browser. Using the file picker instead.");
      window.setTimeout(() => cameraInputRef.current?.click(), 80);
      return;
    }

    try {
      await startCameraPreview("environment");
      setCameraLoading(false);
    } catch (error) {
      setCameraLoading(false);
      setCameraError("Camera permission was denied or the camera could not be started.");
    }
  }

  async function rotateCamera() {
    if (!window.navigator?.mediaDevices?.getUserMedia || cameraLoading) return;

    const nextFacingMode = cameraFacingMode === "environment" ? "user" : "environment";
    setCameraLoading(true);
    setCameraError("");

    try {
      await startCameraPreview(nextFacingMode);
      setCameraLoading(false);
    } catch (error) {
      setCameraLoading(false);
      setCameraError("Could not switch cameras on this device right now.");
    }
  }

  function captureFromCamera() {
    const video = cameraVideoRef.current;
    if (!video || !video.videoWidth || !video.videoHeight) {
      setCameraError("Camera preview is not ready yet. Please wait a moment and try again.");
      return;
    }

    const canvas = document.createElement("canvas");
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;

    const context = canvas.getContext("2d");
    if (!context) {
      setCameraError("Could not capture the camera frame.");
      return;
    }

    context.drawImage(video, 0, 0, canvas.width, canvas.height);
    canvas.toBlob(
      (blob) => {
        if (!blob) {
          setCameraError("Could not create an image from the camera.");
          return;
        }
        const file = new File([blob], `healthnova-camera-${Date.now()}.jpg`, { type: "image/jpeg" });
        updateFile(file);
        closeCameraModal();
      },
      "image/jpeg",
      0.92
    );
  }

  function handleDrop(event) {
    event.preventDefault();
    setIsDragging(false);
    const file = event.dataTransfer?.files?.[0];
    if (file) updateFile(file);
  }

  function handleDragOver(event) {
    event.preventDefault();
    setIsDragging(true);
  }

  function handleDragLeave(event) {
    event.preventDefault();
    setIsDragging(false);
  }

  async function submitAnalysis(event) {
    event.preventDefault();

    if (!authReady) {
      setAnalysisError("Session is still loading. Please wait a moment.");
      return;
    }

    if (isLocked) {
      onOpenAuth("login");
      return;
    }

    if (!form.file) {
      setAnalysisError("Choose a report file first.");
      return;
    }

    setAnalysisLoading(true);
    setAnalysisStage("analyzing");
    setAnalysisError("");

    try {
      const report = await onAnalyze(form);
      setLatestResolvedReport(report || null);
      if (report?.id) {
        setSelectedReportId(report.id);
      }
      setForm({
        patientName: "",
        reportType: "",
        notes: "",
        file: null,
      });
      setAnalysisStage("done");
    } catch (error) {
      setAnalysisError(error.message || "Analysis failed. Please try again.");
    } finally {
      setAnalysisLoading(false);
    }
  }

  async function runIngest() {
    if (!authReady) return;
    if (isLocked) {
      onOpenAuth("login");
      return;
    }

    setIngestLoading(true);
    setAnalysisError("");

    try {
      await onIngest();
    } catch (error) {
      setAnalysisError(error.message || "Knowledge refresh failed.");
    } finally {
      setIngestLoading(false);
    }
  }

  async function copySummary() {
    if (!analysis) return;

    const summaryText = [
      `Report: ${analysis.reportType}`,
      `Analyzed: ${formatReportDate(analysis.analyzedAt)}`,
      `Summary: ${analysis.summary}`,
      `Risk: ${analysis.riskLevel}`,
      `Suggested specialist: ${analysis.doctorSpecialist}`,
    ].join("\n");

    try {
      await navigator.clipboard.writeText(summaryText);
      setCopyState("done");
    } catch {
      setCopyState("idle");
    }
  }

  function downloadReport() {
    if (!analysis) return;

    const html = buildDownloadHtml(analysis, user);
    const blob = new Blob([html], { type: "text/html;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = `healthnova-report-${Date.now()}.html`;
    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();
    URL.revokeObjectURL(url);
  }

  async function toggleHindi() {
    if (!analysis) return;

    if (analysisLanguage === "hi") {
      setAnalysisLanguage("en");
      if (listenState === "playing") {
        window.speechSynthesis?.cancel();
        setListenState("idle");
      }
      return;
    }

    if (Object.keys(translationState.map).length) {
      setAnalysisLanguage("hi");
      return;
    }

    setTranslationState((current) => ({ ...current, loading: true }));
    setAnalysisError("");

    try {
      const translations = await translateAnalysisToHindi(translationEntries);
      const map = {};
      translationEntries.forEach((text, index) => {
        if (text && translations[index]) map[text] = translations[index];
      });
      setTranslationState({ loading: false, map });
      setAnalysisLanguage("hi");
    } catch (error) {
      setTranslationState({ loading: false, map: {} });
      setAnalysisError(error.message || "Hindi translation failed.");
    }
  }

  function toggleListen() {
    if (!window.speechSynthesis || !window.SpeechSynthesisUtterance) {
      setAnalysisError("Speech playback is not supported in this browser.");
      return;
    }

    if (listenState === "playing") {
      window.speechSynthesis.cancel();
      setListenState("idle");
      return;
    }

    if (!analysis) return;

    const translateForSpeech = (text) => {
      if (analysisLanguage !== "hi") return text;
      return translationState.map[text] || text;
    };

    const speechText = buildFriendlySpeechText({
      ...analysis,
      summary: translateForSpeech(analysis.summary),
      possibleDiseases: safeArray(analysis.possibleDiseases).map((item) => ({
        ...item,
        name: translateForSpeech(item.name),
        explanation: translateForSpeech(item.explanation),
      })),
      precautions: safeArray(analysis.precautions).map((item) => ({
        ...item,
        title: translateForSpeech(item.title),
        detail: translateForSpeech(item.detail),
      })),
    }, analysisLanguage, safeText(user?.name));
    if (!speechText) return;

    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(speechText);
    const selectedVoice = getPreferredVoice(analysisLanguage);
    utterance.lang = selectedVoice?.lang || (analysisLanguage === "hi" ? "hi-IN" : "en-IN");
    if (selectedVoice) utterance.voice = selectedVoice;
    utterance.rate = analysisLanguage === "hi" ? 0.88 : 0.92;
    utterance.pitch = analysisLanguage === "hi" ? 1.02 : 1.12;
    utterance.onend = () => setListenState("idle");
    utterance.onerror = () => setListenState("idle");
    setListenState("playing");
    window.speechSynthesis.speak(utterance);
  }

  function stopChatDictation(resetState = true) {
    if (chatVoiceTimerRef.current) {
      window.clearTimeout(chatVoiceTimerRef.current);
      chatVoiceTimerRef.current = null;
    }
    const recognition = chatRecognitionRef.current;
    if (recognition) {
      recognition.onresult = null;
      recognition.onend = null;
      recognition.onerror = null;
      recognition.stop();
      chatRecognitionRef.current = null;
    }
    chatVoiceBaseRef.current = "";
    chatVoiceFinalRef.current = "";
    if (resetState) setChatVoiceState("idle");
  }

  function toggleChatDictation() {
    const SpeechRecognitionCtor = getSpeechRecognitionCtor();
    if (!SpeechRecognitionCtor) {
      setChatError("Voice typing is not supported in this browser.");
      return;
    }

    if (chatVoiceState === "listening") {
      stopChatDictation(true);
      return;
    }

    try {
      const recognition = new SpeechRecognitionCtor();
      chatVoiceBaseRef.current = safeText(chatInput);
      chatVoiceFinalRef.current = "";
      recognition.lang = "en-IN";
      recognition.continuous = true;
      recognition.interimResults = true;
      recognition.maxAlternatives = 1;

      recognition.onresult = (event) => {
        let finalChunk = chatVoiceFinalRef.current;
        let interimChunk = "";

        for (let index = event.resultIndex; index < event.results.length; index += 1) {
          const transcript = safeText(event.results[index]?.[0]?.transcript);
          if (!transcript) continue;
          if (event.results[index].isFinal) finalChunk = `${finalChunk} ${transcript}`.trim();
          else interimChunk = `${interimChunk} ${transcript}`.trim();
        }

        chatVoiceFinalRef.current = finalChunk;
        const nextText = [chatVoiceBaseRef.current, finalChunk, interimChunk].filter(Boolean).join(" ").trim();
        setChatInput(nextText);
      };

      recognition.onerror = () => {
        stopChatDictation(true);
        setChatError("Voice typing stopped. Please try again.");
      };

      recognition.onend = () => {
        if (chatRecognitionRef.current === recognition) {
          stopChatDictation(true);
        }
      };

      recognition.start();
      chatRecognitionRef.current = recognition;
      setChatVoiceState("listening");
      setChatError("");
      chatVoiceTimerRef.current = window.setTimeout(() => {
        stopChatDictation(true);
      }, CHAT_VOICE_MAX_MS);
    } catch {
      stopChatDictation(true);
      setChatError("Could not start voice typing in this browser.");
    }
  }

  function speakChatReply(messageId, text) {
    if (!window.speechSynthesis || !window.SpeechSynthesisUtterance) return;
    const speechText = buildChatReplySpeechText(text);
    if (!speechText) return;

    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(speechText);
    const selectedVoice = getPreferredVoice("en");
    utterance.lang = selectedVoice?.lang || "en-IN";
    if (selectedVoice) utterance.voice = selectedVoice;
    utterance.rate = 0.95;
    utterance.pitch = 1.04;
    utterance.onend = () => setChatSpeakingId("");
    utterance.onerror = () => setChatSpeakingId("");
    setChatSpeakingId(messageId);
    window.speechSynthesis.speak(utterance);
  }

  function stopChatReplySpeech(messageId = "") {
    if (!window.speechSynthesis) return;
    if (!messageId || chatSpeakingId === messageId) {
      window.speechSynthesis.cancel();
      setChatSpeakingId("");
    }
  }

  function handleChatReplyHoverStart(messageId, text) {
    if (chatSpeakingId === messageId) return;
    speakChatReply(messageId, text);
  }

  function handleChatReplyHoverEnd(messageId) {
    stopChatReplySpeech(messageId);
  }

  function requestDoctorLocation() {
    if (!window.navigator?.geolocation) {
      setDoctorLocation({
        status: "error",
        latitude: null,
        longitude: null,
        error: "Location access is not available in this browser.",
      });
      return;
    }

    setDoctorLocation({
      status: "loading",
      latitude: null,
      longitude: null,
      error: "",
    });

    window.navigator.geolocation.getCurrentPosition(
      (position) => {
        setLocationPermission("granted");
        setDoctorLocation({
          status: "granted",
          latitude: position.coords.latitude,
          longitude: position.coords.longitude,
          error: "",
        });
      },
      (error) => {
        const denied = error?.code === 1;
        if (denied) setLocationPermission("denied");
        setDoctorLocation({
          status: denied ? "denied" : "error",
          latitude: null,
          longitude: null,
          error: denied ? "Location permission was denied." : "Could not get your current location.",
        });
      },
      {
        enableHighAccuracy: true,
        timeout: 12000,
        maximumAge: 300000,
      }
    );
  }

  useEffect(() => {
    if (doctorLocation.status !== "granted" || !analysis?.doctorSpecialist) return;

    let cancelled = false;
    setNearbyDoctorsState({
      loading: true,
      area: "",
      items: [],
      links: [],
      error: "",
    });

    findNearbyDoctors({
      latitude: doctorLocation.latitude,
      longitude: doctorLocation.longitude,
      specialty: analysis.doctorSpecialist,
      limit: 4,
    })
      .then((data) => {
        if (cancelled) return;
        setNearbyDoctorsState({
          loading: false,
          area: safeText(data?.area),
          items: safeArray(data?.doctors),
          links: safeArray(data?.fallback_links),
          error: "",
        });
      })
      .catch((error) => {
        if (cancelled) return;
        setNearbyDoctorsState({
          loading: false,
          area: "",
          items: [],
          links: [],
          error: error.message || "Could not load nearby doctors.",
        });
      });

    return () => {
      cancelled = true;
    };
  }, [doctorLocation, analysis?.doctorSpecialist]);

  async function submitChat(event) {
    event.preventDefault();

    if (!authReady) {
      setChatError("Session is still loading.");
      return;
    }

    if (isLocked) {
      onOpenAuth("login");
      return;
    }

    if (!chatInput.trim()) return;

    setChatLoading(true);
    setChatError("");
    const message = chatInput.trim();
    setChatInput("");
    const createdAt = new Date().toISOString();
    const userMessage = {
      id: globalThis.crypto?.randomUUID?.() || `user-${Date.now()}`,
      role: "user",
      content: message,
      createdAt,
    };
    const nextHistory = [...activeChatMessages, userMessage];
    updateActiveChatTab((current) => ({
      ...current,
      label: buildChatTabLabel(nextHistory, current?.label || "New chat"),
      updatedAt: createdAt,
      messages: nextHistory,
    }));

    try {
      const response = await chatWithAssistant({
        question: message,
        analysis_summary: buildAnalysisSummaryFromReport(selectedReport || reports[0] || latestResolvedReport),
        history: nextHistory.map(({ role, content }) => ({ role, content })),
      });
      const assistantMessage = {
        id: globalThis.crypto?.randomUUID?.() || `assistant-${Date.now()}`,
        role: "assistant",
        content:
          response?.answer ||
          response?.result ||
          response?.response ||
          response?.message ||
          "I could not produce a complete answer yet.",
        createdAt: new Date().toISOString(),
      };
      updateActiveChatTab((current) => ({
        ...current,
        messages: [...safeArray(current?.messages), assistantMessage],
        updatedAt: assistantMessage.createdAt,
      }));
    } catch (error) {
      const rawMessage = error.message || "Chat failed.";
      setChatError(
        /Cannot reach the backend/i.test(rawMessage)
          ? "Backend offline. Start HealthNova backend and try again."
          : rawMessage
      );
      setChatInput(message);
      updateActiveChatTab((current) => ({
        ...current,
        messages: safeArray(current?.messages).filter((item) => item.id !== userMessage.id),
      }));
    } finally {
      setChatLoading(false);
    }
  }

  function handleChatKeyDown(event) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      if (!chatLoading && chatInput.trim()) {
        submitChat(event);
      }
    }
  }

  function usePrompt(prompt) {
    if (!activeChatTab) createNewChatTab();
    setChatInput(prompt);
    navigate("/app/chat");
    window.setTimeout(() => textareaRef.current?.focus(), 50);
  }

  const verdict = getVerdictCopy(analysis?.riskLevel || "low");
  const translationEntries = useMemo(() => buildTranslationEntries(analysis, verdict), [analysis, verdict]);

  function translateText(text) {
    if (analysisLanguage !== "hi") return text;
    return translationState.map[text] || text;
  }

  return (
    <div className="workspace-root">
      {sidebarOpen ? <div className="sidebar-backdrop" onClick={() => setSidebarOpen(false)} /> : null}

      <aside className={`workspace-sidebar ${sidebarOpen ? "is-open" : ""}`}>
        <div className="sidebar-header">
          <span className="eyebrow">
            <History size={12} />
            24-hour history
          </span>
          <button className="icon-btn" onClick={() => setSidebarOpen(false)} type="button" aria-label="Close sidebar">
            <X size={14} />
          </button>
        </div>

        {recentReports24h.length ? (
          recentReports24h.map((report, index) => (
            <button
              key={report.id}
              className={`sidebar-item ${selectedReportId === report.id ? "is-active" : ""}`}
              onClick={() => setSelectedReportId(report.id)}
              type="button"
            >
              <span className="sidebar-item__title">{report.title || report.reportType || `Report ${index + 1}`}</span>
              <span className="sidebar-item__date">{formatReportDate(report.createdAt)}</span>
            </button>
          ))
        ) : (
          <p className="sidebar-empty">No reports saved in the last 24 hours.</p>
        )}
      </aside>

      <section className="workspace-main">
        <div className="workspace-topbar">
          {activeTab === "analysis" ? (
            <button className="ghost-btn ghost-btn--small" onClick={() => setSidebarOpen(true)} type="button">
              <History size={14} />
              <span>Analysis history</span>
            </button>
          ) : (
            <div />
          )}
          {analysisLoading ? (
            <div className="workspace-run-banner" role="status" aria-live="polite">
              <LoaderCircle className="spin" size={16} />
              <span>{analysisStage === "analyzing" ? "Analysis is running in the background" : "Processing report in the background"}</span>
              {activeTab !== "analysis" ? (
                <button className="ghost-btn ghost-btn--small workspace-run-banner__action" onClick={() => navigate("/app/analysis")} type="button">
                  Open analysis
                </button>
              ) : null}
            </div>
          ) : null}
        </div>

        {activeTab === "analysis" ? (
          <div className="workspace-analysis-layout">
            <div className="analysis-sidebar-form">
              <form onSubmit={submitAnalysis}>
                <div className="panel panel--analysis-intake">
                  <div className="panel__header">
                    <div className="analysis-intake-heading">
                      <span className="analysis-intake-heading__eyebrow">Report analysis</span>
                      <h3>Upload And Analyze</h3>
                      <p className="panel-subtle">
                        Add any medical report and HealthNova will detect the report type from the content, then turn it into a structured summary, findings list, and follow-up guidance.
                      </p>
                    </div>
                    <button className="ghost-btn ghost-btn--small" onClick={runIngest} type="button" disabled={ingestLoading}>
                      {ingestLoading ? <LoaderCircle className="spin" size={14} /> : <RefreshCcw size={14} />}
                      <span>Refresh docs</span>
                    </button>
                  </div>

                  <div className="analysis-intake-grid">
                    <div className="analysis-intake-column analysis-intake-column--details">
                      <div className="chip-row chip-row--intake">
                        {REPORT_TYPE_SUGGESTIONS.map((suggestion) => (
                          <button
                            key={suggestion}
                            className={`chip ${form.reportType === suggestion ? "chip--active" : ""}`}
                            onClick={() => setForm((current) => ({ ...current, reportType: suggestion }))}
                            type="button"
                          >
                            {suggestion}
                          </button>
                        ))}
                      </div>
                      <p className="panel-subtle analysis-intake-note">
                        Report type is optional. If you leave it blank, the API will detect what is in the uploaded report.
                      </p>

                      <div className="analysis-details-fields">
                        <input
                          className="analysis-field"
                          value={form.patientName}
                          onChange={(event) => setForm((current) => ({ ...current, patientName: event.target.value }))}
                          placeholder="Patient name"
                        />
                        <input
                          className="analysis-field"
                          value={form.reportType}
                          onChange={(event) => setForm((current) => ({ ...current, reportType: event.target.value }))}
                          placeholder="Report type (optional)"
                        />
                      </div>

                      <div className="analysis-notes-wrap">
                        <textarea
                          className="analysis-notes"
                          value={form.notes}
                          onChange={(event) => setForm((current) => ({ ...current, notes: event.target.value }))}
                          placeholder="Optional notes for context"
                          rows={4}
                        />
                      </div>
                    </div>

                    <div className="analysis-intake-column analysis-intake-column--upload">
                      <label
                        className={`upload-box${isDragging ? " is-dragging" : ""}${form.file ? " has-file" : ""}`}
                        onDrop={handleDrop}
                        onDragOver={handleDragOver}
                        onDragLeave={handleDragLeave}
                      >
                        <div className="upload-box__badge">
                          <ShieldCheck size={12} />
                          Secure medical upload
                        </div>
                        <div className="upload-box__icon">
                          <FileText size={34} />
                        </div>
                        <span>{form.file ? form.file.name : "Drop report here or click to browse"}</span>
                        <small>PDF, image, DOCX, XLSX, CSV, JSON</small>
                        <p className="upload-box__helper">
                          Clear scans and photos work best. You can also add patient details on the left before analysis.
                        </p>
                        <input
                          ref={fileInputRef}
                          type="file"
                          accept=".pdf,.png,.jpg,.jpeg,.webp,.bmp,.tif,.tiff,.txt,.md,.json,.csv,.doc,.docx,.xls,.xlsx"
                          style={{ display: "none" }}
                          onChange={(event) => updateFile(event.target.files?.[0] || null)}
                        />
                      </label>

                      <div className="upload-actions-row">
                        <button className="ghost-btn" onClick={() => fileInputRef.current?.click()} type="button">
                          <FileUp size={15} />
                          <span>Browse files</span>
                        </button>
                        <button className="ghost-btn" onClick={openCameraModal} type="button">
                          <Camera size={15} />
                          <span>Use camera</span>
                        </button>
                        <input
                          ref={cameraInputRef}
                          type="file"
                          accept="image/*"
                          capture="environment"
                          style={{ display: "none" }}
                          onChange={(event) => updateFile(event.target.files?.[0] || null)}
                        />
                      </div>

                      <button className="primary-btn primary-btn--hero" type="submit" disabled={analysisLoading}>
                        {analysisLoading ? <LoaderCircle className="spin" size={16} /> : <Zap size={16} />}
                        <span>{analysisLoading ? (analysisStage === "analyzing" ? "Analyzing report..." : "Processing...") : "Analyze report"}</span>
                      </button>
                    </div>
                  </div>

                  {analysisError ? <div className="auth-alert auth-alert--error">{analysisError}</div> : null}

                  {form.file ? (
                    <div className="file-chip">
                      <FileText size={14} style={{ color: "var(--c-teal)" }} />
                      <span style={{ flex: 1, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{form.file.name}</span>
                      {hasImagePreview ? (
                        <button
                          className="icon-btn file-chip__preview-btn"
                          onClick={() => setImagePreviewOpen(true)}
                          type="button"
                          aria-label="Preview uploaded image"
                          title="Preview uploaded image"
                        >
                          <ImageIcon size={14} />
                        </button>
                      ) : null}
                      <span className="file-chip__size">{Math.max(1, Math.round(form.file.size / 1024))} KB</span>
                      <button className="icon-btn" onClick={() => updateFile(null)} type="button" aria-label="Remove file">
                        <X size={12} />
                      </button>
                    </div>
                  ) : null}
                </div>
              </form>
            </div>

            <div className="analysis-results-area">
              <div className="panel panel--analysis-results">
                <div className="panel__header panel__header--stack">
                  <div>
                    <h3>Structured Report Output</h3>
                    <p className="panel-subtle">
                      {analysis
                        ? analysisLanguage === "hi"
                          ? "आपकी नवीनतम रिपोर्ट हिंदी में देखने के लिए तैयार है"
                          : "Your latest report is ready to review"
                        : "Upload a report to start"}
                    </p>
                  </div>

                  {analysis ? (
                    <div className="result-toolbar">
                      <button className="ghost-btn ghost-btn--small" onClick={toggleHindi} type="button" disabled={translationState.loading}>
                        {translationState.loading ? <LoaderCircle className="spin" size={14} /> : <Languages size={14} />}
                        <span>{analysisLanguage === "hi" ? "English" : "Hindi"}</span>
                      </button>
                      <button className="ghost-btn ghost-btn--small" onClick={toggleListen} type="button">
                        <Volume2 size={14} />
                        <span>{listenState === "playing" ? "Stop" : analysisLanguage === "hi" ? "Speak Hindi" : "Listen"}</span>
                      </button>
                      <button className="ghost-btn ghost-btn--small" onClick={copySummary} type="button">
                        {copyState === "done" ? <Check size={14} /> : <Copy size={14} />}
                        <span>{copyState === "done" ? "Copied" : "Copy"}</span>
                      </button>
                      <button className="ghost-btn ghost-btn--small" onClick={downloadReport} type="button">
                        <Download size={14} />
                        <span>Download</span>
                      </button>
                      <button className="ghost-btn ghost-btn--small" onClick={() => navigate("/app/chat")} type="button">
                        <MessageCircleHeart size={14} />
                        <span>Ask AI</span>
                      </button>
                    </div>
                  ) : null}
                </div>

                {!authReady ? (
                  renderRestoringState()
                ) : isLocked ? (
                  renderLockedState("analysis", onOpenAuth)
                ) : analysisLoading ? (
                  <div className="loading-analysis">
                    <LoaderCircle className="spin" size={26} />
                    <div>
                      <strong>{analysisStage === "analyzing" ? "Analyzing report..." : "Processing..."}</strong>
                      <p>The backend is reading your file and generating the structured output.</p>
                    </div>
                  </div>
                ) : analysis ? (
                  <div className="analysis-result">
                    <div className={`verdict-banner verdict-banner--${analysis.riskLevel}`}>
                      <div className="verdict-banner__icon">
                        {analysis.riskLevel === "critical" || analysis.riskLevel === "high" ? (
                          <TriangleAlert size={20} />
                        ) : analysis.riskLevel === "moderate" ? (
                          <AlertCircle size={20} />
                        ) : (
                          <ShieldCheck size={20} />
                        )}
                      </div>
                      <div>
                        <strong>{translateText(verdict.title)}</strong>
                        <p>{translateText(analysis.summary || verdict.body)}</p>
                      </div>
                    </div>

                    <div className="report-meta-grid">
                      <article className="metric-tile">
                        <span>{translateText("Report type")}</span>
                        <strong>{translateText(analysis.reportType)}</strong>
                      </article>
                      <article className="metric-tile">
                        <span>{translateText("Analyzed")}</span>
                        <strong>{formatReportDate(analysis.analyzedAt)}</strong>
                      </article>
                      <article className="metric-tile">
                        <span>{translateText("Structured details")}</span>
                        <strong>{analysisLanguage === "hi" ? `${analysis.markers.length} ${translateText("items")}` : `${analysis.markers.length} items`}</strong>
                      </article>
                      <article className="metric-tile">
                        <span>{translateText("Abnormal")}</span>
                        <strong>{abnormalMarkers.length}</strong>
                      </article>
                      <article className="metric-tile">
                        <span>{translateText("Risk level")}</span>
                        <strong className={`risk-badge risk-badge--${analysis.riskLevel}`}>{translateText(analysis.riskLevel)}</strong>
                      </article>
                      <article className="metric-tile">
                        <span>{translateText("Suggested specialist")}</span>
                        <strong>{translateText(analysis.doctorSpecialist)}</strong>
                      </article>
                    </div>

                    <section className="report-section-block report-section-block--full">
                      <div className="report-section-head">
                        <div className="report-section-head__icon">
                          <FlaskConical size={16} />
                        </div>
                        <div>
                          <h4>{translateText("Important Measures")}</h4>
                          <p>{translateText("Showing the most clinically relevant extracted details from the report instead of every raw OCR line.")}</p>
                          <p className="panel-subtle">{translateText("For lab reports this includes key values. For ECG and imaging-style reports, the summary and findings sections may carry more of the useful detail.")}</p>
                        </div>
                      </div>

                      {analysis.markers.length ? (
                        <div className="markers-table-wrap">
                          <table className="markers-table">
                            <thead>
                              <tr>
                                <th>{translateText("Test")}</th>
                                <th>{translateText("Value")}</th>
                                <th>{translateText("Status")}</th>
                              </tr>
                            </thead>
                            <tbody>
                              {analysis.markers.map((marker) => (
                                <tr key={marker.id}>
                                  <td className="marker-name">{translateText(marker.name)}</td>
                                  <td>{marker.value}</td>
                                  <td>
                                    <span className={`status-badge status-badge--${marker.status}`}>{translateText(marker.status.replace("_", " "))}</span>
                                  </td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      ) : (
                        <div className="empty-card">
                          <Upload size={18} />
                          <p>{translateText("No structured numeric values were extracted. This can happen with ECG, X-ray, or imaging reports, so check the summary and findings below.")}</p>
                        </div>
                      )}
                    </section>

                    {analysis.possibleDiseases.length ? (
                      <section className="report-section-block report-section-block--full">
                        <div className="report-section-head">
                          <div className="report-section-head__icon">
                            <HeartPulse size={16} />
                          </div>
                          <div>
                            <h4>{translateText("Possible Conditions To Discuss")}</h4>
                            <p>{translateText("These are patterns to review with a doctor, not confirmed diagnoses.")}</p>
                          </div>
                        </div>
                        <div className="disease-cards">
                          {analysis.possibleDiseases.map((item) => (
                            <div key={item.id} className={`disease-card disease-card--${item.likelihood}`}>
                              <div className="disease-card__head">
                                <strong>{translateText(item.name)}</strong>
                                <span className={`likelihood-badge likelihood-badge--${item.likelihood}`}>{analysisLanguage === "hi" ? `${translateText(item.likelihood)} ${translateText("likelihood")}` : `${item.likelihood} likelihood`}</span>
                              </div>
                              <p>{translateText(item.explanation)}</p>
                            </div>
                          ))}
                        </div>
                      </section>
                    ) : null}

                    <div className="analysis-report-board">
                      <section className="report-section-block">
                        <div className="report-section-head">
                          <div className="report-section-head__icon">
                            <ShieldCheck size={16} />
                          </div>
                          <div>
                            <h4>{translateText("Precautions")}</h4>
                            <p>{translateText("Suggested next steps and caution areas based on the current report.")}</p>
                          </div>
                        </div>

                        {analysis.precautions.length ? (
                          <div className="report-bullet-grid">
                            {analysis.precautions.map((item) => (
                              <article key={item.id} className={`insight-card insight-card--precaution insight-card--urgency-${item.urgency}`}>
                                <div className="insight-card__label-row">
                                  <span>{translateText(item.title)}</span>
                                  {item.urgency !== "routine" ? (
                                    <span className={`urgency-badge urgency-badge--${item.urgency}`}>{translateText(item.urgency)}</span>
                                  ) : null}
                                </div>
                                <p>{translateText(item.detail)}</p>
                              </article>
                            ))}
                          </div>
                        ) : (
                          <div className="empty-card">
                            <ShieldCheck size={18} />
                            <p>{translateText("No precaution items were generated for this report.")}</p>
                          </div>
                        )}
                      </section>

                      <section className="report-section-block">
                        <div className="report-section-head">
                          <div className="report-section-head__icon">
                            <HeartPulse size={16} />
                          </div>
                          <div>
                            <h4>{translateText("Daily Guidance")}</h4>
                            <p>{translateText("Short practical advice extracted from the report summary.")}</p>
                          </div>
                        </div>

                        {(analysis.dietaryAdvice || analysis.exerciseAdvice) ? (
                          <div className="advice-grid">
                            {analysis.dietaryAdvice ? (
                              <div className="advice-card advice-card--diet">
                                <strong>{translateText("Dietary Advice")}</strong>
                                <p>{translateText(analysis.dietaryAdvice)}</p>
                              </div>
                            ) : null}
                            {analysis.exerciseAdvice ? (
                              <div className="advice-card advice-card--exercise">
                                <strong>{translateText("Lifestyle Advice")}</strong>
                                <p>{translateText(analysis.exerciseAdvice)}</p>
                              </div>
                            ) : null}
                          </div>
                        ) : (
                          <div className="empty-card">
                            <HeartPulse size={18} />
                            <p>{translateText("No daily guidance was generated for this report.")}</p>
                          </div>
                        )}
                      </section>
                    </div>

                    {analysis.recommendedTests.length ? (
                      <section className="report-section-block report-section-block--full">
                        <div className="report-section-head">
                          <div className="report-section-head__icon">
                            <ClipboardList size={16} />
                          </div>
                          <div>
                            <h4>{translateText("Recommended Follow-up Tests")}</h4>
                            <p>{translateText("These tests may help confirm or clarify the report findings.")}</p>
                          </div>
                        </div>

                        <div className="report-bullet-grid">
                          {analysis.recommendedTests.map((item) => (
                            <article key={item.id} className="insight-card">
                              <span>{translateText(item.test)}</span>
                              <p>{translateText(item.reason)}</p>
                            </article>
                          ))}
                        </div>
                      </section>
                    ) : null}

                    <section className="report-section-block report-section-block--full">
                      <div className="report-section-head">
                        <div className="report-section-head__icon">
                          <HeartPulse size={16} />
                          </div>
                          <div>
                            <h4>{translateText("Nearby Doctor Search")}</h4>
                            <p>{translateText("Allow GPS once, then HealthNova will open nearby doctor results for the right specialty.")}</p>
                          </div>
                        </div>

                      {doctorLocation.status === "granted" ? (
                        nearbyDoctorsState.loading ? (
                          <div className="empty-card empty-card--doctor">
                            <LoaderCircle className="spin" size={18} />
                            <div>
                              <strong>{translateText("Finding nearby doctors...")}</strong>
                              <p>{translateText(`Searching live results for ${analysis.doctorSpecialist} near your current area.`)}</p>
                            </div>
                          </div>
                        ) : nearbyDoctorsState.items.length ? (
                          <div className="doctor-cards">
                            {nearbyDoctorsState.items.map((item, index) => (
                              <div key={`${item.url}-${index}`} className="doctor-card">
                                <div className="doctor-card__topline">
                                  <MapPin size={14} />
                                  <span>{translateText(item.area || nearbyDoctorsState.area || "Nearby")}</span>
                                </div>
                                <strong>{translateText(item.name)}</strong>
                                <span className="doctor-profession">{translateText(item.specialty || analysis.doctorSpecialist)}</span>
                                <p>{translateText(item.snippet || "Live nearby search result.")}</p>
                                <p className="doctor-phone">{item.source}</p>
                                <div className="doctor-card__actions">
                                  <a
                                    className="doctor-map-link"
                                    href={item.maps_url || item.url}
                                    target="_blank"
                                    rel="noreferrer"
                                    aria-label={`Open ${item.name || "doctor"} in Google Maps`}
                                    title="Open in Google Maps"
                                  >
                                    <MapPin size={16} />
                                  </a>
                                </div>
                              </div>
                            ))}
                          </div>
                        ) : (
                          <div className="empty-card empty-card--doctor">
                            <MapPin size={18} />
                            <div>
                              <strong>{translateText("No in-page doctor matches found yet")}</strong>
                              <p>{translateText(nearbyDoctorsState.error || "We could not parse nearby doctor cards for this area right now.")}</p>
                            </div>
                            <div className="doctor-card__actions">
                              {nearbyDoctorsState.links.slice(0, 1).map((item) => (
                                <a
                                  key={item.url}
                                  className="doctor-map-link"
                                  href={item.url}
                                  target="_blank"
                                  rel="noreferrer"
                                  aria-label={item.label}
                                  title={item.label}
                                >
                                  <MapPin size={16} />
                                </a>
                              ))}
                            </div>
                          </div>
                        )
                      ) : (
                        <div className="empty-card empty-card--doctor">
                          {doctorLocation.status === "loading" ? <LoaderCircle className="spin" size={18} /> : <LocateFixed size={18} />}
                          <div>
                            <strong>
                              {doctorLocation.status === "loading"
                                ? translateText("Requesting your live location...")
                                : doctorLocation.status === "denied" || locationPermission === "denied"
                                  ? translateText("Location permission is blocked")
                                  : translateText("Allow location for real nearby doctors")}
                            </strong>
                            <p>
                              {translateText(doctorLocation.error ||
                                (locationPermission === "granted"
                                  ? "Location access is allowed. HealthNova will use your current area for nearby doctor results."
                                  : locationPermission === "denied"
                                    ? "Location permission is denied in the browser. Allow location for this site and try again."
                                    : "HealthNova needs your permission to use live location and show nearby doctor results for the recommended specialty."))}
                            </p>
                          </div>
                          {doctorLocation.status !== "loading" ? (
                            <button className="primary-btn" onClick={requestDoctorLocation} type="button">
                              <LocateFixed size={16} />
                              <span>{translateText(locationPermission === "denied" ? "Try Location Again" : "Allow Location")}</span>
                            </button>
                          ) : null}
                        </div>
                      )}
                    </section>

                    {analysis.reportFindings.length ? (
                      <section className="report-section-block report-section-block--full">
                        <div className="report-section-head">
                          <div className="report-section-head__icon">
                            <ClipboardList size={16} />
                          </div>
                          <div>
                            <h4>{translateText("Report Findings")}</h4>
                            <p>{translateText("Important lines extracted from the uploaded report text.")}</p>
                          </div>
                        </div>

                        <div className="report-bullet-grid">
                          {analysis.reportFindings.map((item, index) => (
                            <article key={`${item.label}-${index}`} className="insight-card">
                              <span>{translateText(item.label)}</span>
                              <p>{translateText(item.value)}</p>
                            </article>
                          ))}
                        </div>
                      </section>
                    ) : null}

                    {analysis.supportingContext.length ? (
                      <section className="report-section-block report-section-block--full">
                        <div className="report-section-head">
                          <div className="report-section-head__icon">
                            <Bot size={16} />
                          </div>
                          <div>
                            <h4>{translateText("Supporting Context")}</h4>
                            <p>{translateText("Additional background the backend retrieved to support the explanation.")}</p>
                          </div>
                        </div>

                        <div className="report-bullet-grid">
                          {analysis.supportingContext.map((item, index) => (
                            <article key={`${item.label}-${index}`} className="insight-card">
                              <span>{translateText(item.label)}</span>
                              <p>{translateText(item.value)}</p>
                            </article>
                          ))}
                        </div>
                      </section>
                    ) : null}

                    <div className="report-disclaimer">
                      <strong>{translateText("Disclaimer")}</strong>
                      <p>{translateText(analysis.disclaimer)}</p>
                    </div>
                  </div>
                ) : (
                  <div className="empty-analysis">
                    <div className="empty-analysis__icon">
                      <FileUp size={38} />
                    </div>
                    <strong>Upload a medical report to begin</strong>
                    <p>The analysis view will populate here with extracted values, findings, follow-up tests, and chat-ready context.</p>
                  </div>
                )}
              </div>
            </div>
          </div>
        ) : (
          <div className="chat-layout">
            {!authReady ? (
              renderRestoringState()
            ) : isLocked ? (
              renderLockedState("chat", onOpenAuth)
            ) : (
              <div className="chat-studio">
                <section className="chat-studio__main panel">
                  {chatError ? <div className="auth-alert auth-alert--error chat-panel__alert">{chatError}</div> : null}

                  <div className="chat-studio__tabs">
                    <div className="chat-tabs-scroll">
                      {chatTabs.map((tabItem, index) => (
                        <div key={tabItem.id} className={`chat-tab-chip ${activeChatTabId === tabItem.id ? "is-active" : ""}`}>
                          <button
                            className="chat-tab-chip__select"
                            onClick={() => setActiveChatTabId(tabItem.id)}
                            type="button"
                          >
                            <span>{safeText(tabItem.label) || `Chat ${index + 1}`}</span>
                          </button>
                          {chatTabs.length > 1 ? (
                            <button
                              className="chat-tab-chip__close"
                              onClick={() => removeChatTab(tabItem.id)}
                              type="button"
                              aria-label={`Close ${safeText(tabItem.label) || `Chat ${index + 1}`}`}
                            >
                              <X size={12} />
                            </button>
                          ) : null}
                        </div>
                      ))}
                    </div>
                    <button className="ghost-btn ghost-btn--small chat-tabs-bar__add" onClick={createNewChatTab} type="button">
                      <Sparkles size={14} />
                      <span>New chat</span>
                    </button>
                  </div>

                  <div className="chat-studio__body">
                    <div
                      className="chat-thread chat-studio__thread"
                      ref={chatThreadRef}
                      onPointerLeave={() => stopChatReplySpeech()}
                    >
                    {shouldShowStarterPrompts ? (
                      <div className="chat-studio__inline-prompts">
                        {CHAT_SUGGESTED_PROMPTS.map((prompt) => (
                          <button key={prompt} className="chat-studio__inline-prompt" onClick={() => usePrompt(prompt)} type="button">
                            <span>{prompt}</span>
                            <span>→</span>
                          </button>
                        ))}
                      </div>
                    ) : null}

                    {activeChatMessages.length ? (
                      activeChatMessages.map((message, index) => (
                        <div key={message.id || `${message.role}-${index}`} className={`chat-message-row ${message.role}`}>
                          <article
                            className={`chat-bubble ${message.role} ${chatSpeakingId === message.id ? "is-speaking" : ""}`}
                            onPointerEnter={
                              message.role === "assistant"
                                ? () => handleChatReplyHoverStart(message.id || `${message.role}-${index}`, message.content)
                                : undefined
                            }
                            onPointerLeave={
                              message.role === "assistant"
                                ? () => handleChatReplyHoverEnd(message.id || `${message.role}-${index}`)
                                : undefined
                            }
                          >
                            {message.role === "assistant" ? <strong>HealthNova</strong> : null}
                            <p>{message.content}</p>
                            {message.role === "assistant" ? (
                              <span className="chat-bubble__voice-hint">
                                <Volume2 size={13} />
                                <span>{chatSpeakingId === (message.id || `${message.role}-${index}`) ? "Playing" : "Hover to listen"}</span>
                              </span>
                            ) : null}
                          </article>
                        </div>
                      ))
                    ) : null}

                    {chatLoading ? (
                      <div className="chat-message-row assistant">
                        <article className="chat-bubble assistant chat-bubble--thinking">
                          <strong>HealthNova</strong>
                          <div className="thinking-dots">
                            <span />
                            <span />
                            <span />
                          </div>
                        </article>
                      </div>
                    ) : null}
                    </div>

                    <form className="chat-studio__composer" onSubmit={submitChat}>
                      <div className="chat-studio__composer-shell">
                        <textarea
                          ref={textareaRef}
                          rows={1}
                          value={chatInput}
                          onChange={(event) => setChatInput(event.target.value)}
                          onKeyDown={handleChatKeyDown}
                          placeholder="Ask about symptoms, report values, trends, or next steps..."
                          aria-label="Message HealthNova"
                        />
                        <button
                          className={`ghost-btn chat-studio__voice ${chatVoiceState === "listening" ? "is-listening" : ""}`}
                          type="button"
                          onClick={toggleChatDictation}
                          aria-label={chatVoiceState === "listening" ? "Stop voice typing" : "Start voice typing"}
                          title={chatVoiceState === "listening" ? "Stop voice typing" : "Start voice typing"}
                        >
                          {chatVoiceState === "listening" ? <LoaderCircle className="spin" size={16} /> : <Mic size={16} />}
                          <span>{chatVoiceState === "listening" ? "Listening..." : "Speak"}</span>
                        </button>
                        <button className="primary-btn chat-studio__send" type="submit" disabled={chatLoading || !chatInput.trim()}>
                          {chatLoading ? <LoaderCircle className="spin" size={16} /> : <SendHorizonal size={16} />}
                          <span>{chatLoading ? "Sending..." : "Send"}</span>
                        </button>
                      </div>
                    </form>
                  </div>
                </section>
              </div>
            )}
          </div>
        )}
      </section>

      {cameraOpen ? (
        <div className="camera-modal">
          <div className="camera-modal__backdrop" onClick={closeCameraModal} />
          <div className="camera-modal__card">
            <div className="camera-modal__header">
              <div>
                <h4>Capture report photo</h4>
                <p>Use your camera inside HealthNova. The modal border follows the current theme.</p>
              </div>
              <button className="icon-btn" onClick={closeCameraModal} type="button" aria-label="Close camera">
                <X size={16} />
              </button>
            </div>

            <div className="camera-modal__preview">
              {cameraLoading ? (
                <div className="camera-modal__status">
                  <LoaderCircle className="spin" size={18} />
                  <span>Opening camera...</span>
                </div>
              ) : null}

              {cameraError && !cameraLoading ? (
                <div className="camera-modal__status camera-modal__status--error">
                  <AlertCircle size={18} />
                  <span>{cameraError}</span>
                </div>
              ) : null}

              <video
                ref={cameraVideoRef}
                className={cameraLoading || cameraError ? "is-hidden" : ""}
                autoPlay
                playsInline
                muted
              />
            </div>

            <div className="camera-modal__actions">
              <button className="ghost-btn" onClick={closeCameraModal} type="button">
                Cancel
              </button>
              <button
                className="ghost-btn camera-modal__rotate-btn"
                onClick={rotateCamera}
                type="button"
                disabled={cameraLoading || Boolean(cameraError)}
                aria-label="Rotate camera"
                title="Rotate camera"
              >
                <RefreshCcw size={16} />
              </button>
              <button className="primary-btn" onClick={captureFromCamera} type="button" disabled={cameraLoading || Boolean(cameraError)}>
                <Camera size={16} />
                <span>Capture photo</span>
              </button>
            </div>
          </div>
        </div>
      ) : null}

      {imagePreviewOpen && hasImagePreview ? (
        <div className="camera-modal">
          <div className="camera-modal__backdrop" onClick={() => setImagePreviewOpen(false)} />
          <div className="camera-modal__card camera-modal__card--preview">
            <div className="camera-modal__header">
              <div>
                <h4>Review uploaded image</h4>
                <p>Check the full report photo before analysis.</p>
              </div>
              <button className="icon-btn" onClick={() => setImagePreviewOpen(false)} type="button" aria-label="Close image preview">
                <X size={16} />
              </button>
            </div>

            <div className="camera-modal__preview camera-modal__preview--image">
              <img src={filePreviewUrl} alt={form.file?.name || "Uploaded report preview"} className="camera-modal__image" />
            </div>

            <div className="camera-modal__actions">
              <button className="ghost-btn" onClick={() => setImagePreviewOpen(false)} type="button">
                Close
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}

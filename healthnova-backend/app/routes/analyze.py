from __future__ import annotations

import ast
import json
import os
import re
import tempfile
from pathlib import Path

import httpx
from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from app.modules.analyzer import analyze_with_rag
from app.modules.extract_values import extract_lab_values
from app.modules.ocr import image_bytes_to_text
from app.modules.pdf_parser import parse_pdf_text
from app.modules.retriever import retrieve_context

router = APIRouter()

_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff"}
_TEXT_EXTENSIONS = {".txt", ".md", ".json", ".csv"}
_BLOCKED_EXTENSIONS = {".gif", ".mp4", ".mov", ".avi", ".mkv", ".webm", ".mpeg", ".mpg", ".wmv", ".m4v"}
_ALLOWED_UNIT_WORDS = {
    "mg",
    "dl",
    "ml",
    "l",
    "ul",
    "fl",
    "pg",
    "g",
    "kg",
    "iu",
    "miu",
    "uiu",
    "meq",
    "mmol",
    "mol",
    "cells",
    "cell",
    "lakh",
    "lakhs",
    "lac",
    "lacs",
    "million",
    "millions",
    "percent",
}
_MEDICAL_PRIORITY_RE = re.compile(
    r"\b("
    r"hemoglobin|haemoglobin|hb|wbc|rbc|platelet|plt|mcv|mch|mchc|rdw|mpv|"
    r"glucose|hba1c|creatinine|urea|bun|bilirubin|alt|ast|alp|tsh|t3|t4|"
    r"sodium|potassium|chloride|calcium|vitamin|ferritin|iron|crp|esr|"
    r"bp|blood pressure|pulse|heart rate|spo2|oxygen saturation|temperature|"
    r"ef|ejection fraction|pr interval|qrs|qtc|dimension|size|lesion|mass|nodule|"
    r"fracture|opacity|consolidation|effusion|impression|diagnosis|"
    r"high|low|elevated|critical|positive|negative"
    r")\b",
    re.IGNORECASE,
)


def _infer_report_hints(raw_text: str, manual_text: str = "", file_name: str = "", content_type: str = "") -> dict[str, str]:
    combined = " ".join(part for part in [_clean_text(file_name), _clean_text(content_type), _clean_text(manual_text), _clean_text(raw_text)] if part).lower()

    if re.search(r"\b(cbc|complete blood count|hemogram)\b", combined):
        return {"report_type": "CBC", "doctor_specialist": "General Physician"}
    if re.search(r"\b(lft|liver function test|hepatic panel)\b", combined):
        return {"report_type": "Liver function test", "doctor_specialist": "Gastroenterologist"}
    if re.search(r"\b(kft|kidney function test|renal function test|renal panel)\b", combined):
        return {"report_type": "Kidney function test", "doctor_specialist": "Nephrologist"}
    if re.search(r"\b(lipid profile|lipid panel|cholesterol)\b", combined):
        return {"report_type": "Lipid profile", "doctor_specialist": "General Physician"}
    if re.search(r"\b(thyroid profile|thyroid function test|tft|tsh|ft3|ft4)\b", combined):
        return {"report_type": "Thyroid profile", "doctor_specialist": "Endocrinologist"}
    if re.search(r"\b(hba1c|diabetes|glucose tolerance)\b", combined):
        return {"report_type": "Diabetes panel", "doctor_specialist": "Endocrinologist"}
    if re.search(r"\b(urine routine|urinalysis|urine examination)\b", combined):
        return {"report_type": "Urine report", "doctor_specialist": "General Physician"}
    if re.search(r"\b(ecg|ekg|electrocardiogram)\b", combined):
        return {"report_type": "ECG", "doctor_specialist": "Cardiologist"}
    if re.search(r"\b(echo|echocardiogram)\b", combined):
        return {"report_type": "Echo report", "doctor_specialist": "Cardiologist"}
    if re.search(r"\b(trop(?:onin)?|ck[- ]?mb|cardiac enzymes?)\b", combined):
        return {"report_type": "Cardiac markers", "doctor_specialist": "Cardiologist"}
    if re.search(r"\b(x[- ]?ray|xray|radiograph|fracture|bone|ortho|orthopedic|orthopaedic)\b", combined):
        return {"report_type": "X-ray report", "doctor_specialist": "Orthopedist"}
    if re.search(r"\b(chest x[- ]?ray|cxr)\b", combined):
        return {"report_type": "Chest X-ray report", "doctor_specialist": "Pulmonologist"}
    if re.search(r"\b(mri)\b", combined):
        return {"report_type": "MRI report", "doctor_specialist": "Relevant specialist"}
    if re.search(r"\b(ct|ct scan)\b", combined):
        return {"report_type": "CT report", "doctor_specialist": "Relevant specialist"}
    if re.search(r"\b(ultrasound|usg|sonography)\b", combined):
        return {"report_type": "Ultrasound report", "doctor_specialist": "Relevant specialist"}
    if re.search(r"\b(mammography|mammogram)\b", combined):
        return {"report_type": "Mammography report", "doctor_specialist": "Relevant specialist"}
    if re.search(r"\b(pft|spirometry|pulmonary function)\b", combined):
        return {"report_type": "Pulmonary function report", "doctor_specialist": "Pulmonologist"}
    if re.search(r"\b(discharge|discharge summary|hospital summary)\b", combined):
        return {"report_type": "Discharge summary", "doctor_specialist": "Relevant specialist"}
    if re.search(r"\b(prescription|rx|medication)\b", combined):
        return {"report_type": "Prescription", "doctor_specialist": "Relevant specialist"}
    if re.search(r"\b(histopathology|biopsy|pathology|fnac|cytology)\b", combined):
        return {"report_type": "Pathology report", "doctor_specialist": "Relevant specialist"}
    if re.search(r"\b(vital signs|bp|blood pressure|pulse|temperature|spo2|oxygen saturation)\b", combined):
        return {"report_type": "Clinical observation report", "doctor_specialist": "General Physician"}
    if re.search(r"\b(cbc|blood|hemoglobin|wbc|rbc|platelet|glucose|hba1c|creatinine|tsh|bilirubin|cholesterol)\b", combined):
        return {"report_type": "Blood test", "doctor_specialist": "General Physician"}
    if "image/" in combined:
        return {"report_type": "Image report", "doctor_specialist": "Relevant specialist"}
    return {"report_type": "Medical report", "doctor_specialist": "Relevant specialist"}


def _build_limited_image_result(raw_text: str, manual_text: str, file_name: str, content_type: str) -> dict:
    hints = _infer_report_hints(raw_text, manual_text, file_name, content_type)
    report_type = hints["report_type"]
    specialist = hints["doctor_specialist"]

    if specialist == "Orthopedist":
        finding_value = "This looks like a fracture or X-ray style upload, but the current pipeline could not extract enough readable report text to confirm the exact finding."
        precaution_value = "If there is severe pain, visible deformity, swelling, numbness, or trouble moving the limb, seek urgent orthopedic or emergency care."
        test_value = "Orthopedic review with official X-ray reading or repeat views if advised."
    elif specialist == "Cardiologist":
        finding_value = "This looks like an ECG-style upload, but the current pipeline could not extract enough readable report text to confirm the rhythm or abnormality."
        precaution_value = "If there is chest pain, fainting, severe breathlessness, or palpitations, seek urgent medical care."
        test_value = "Cardiology review with the original ECG or a repeat ECG if advised."
    else:
        finding_value = "This appears to be an image-based medical upload, but the current pipeline could not extract enough readable report text to interpret it reliably."
        precaution_value = "Use the original report or image in follow-up care, especially if symptoms are getting worse."
        test_value = "Relevant specialist review with the original image or written report."

    return {
        "report_type": report_type,
        "clinical_explanation": (
            f"{report_type} uploaded, but there is not enough readable text to produce a reliable structured interpretation. "
            "Please upload the written report text, a clearer scan, or the radiology/impression page if available."
        ),
        "evidence_summary": "Image-only upload with limited readable OCR text.",
        "symptoms_summary": "",
        "risk_level": "Preliminary",
        "confidence_level": "Low",
        "doctor_specialist": specialist,
        "report_findings": [{"label": "Limited image interpretation", "value": finding_value}],
        "interpreted_lab_values": [],
        "predicted_conditions": [],
        "recommended_tests": [{"label": "Recommended next step", "value": test_value}],
        "suggested_blood_tests": [],
        "diet_recommendations": [],
        "lifestyle_changes": [],
        "precautions": [{"label": "Care advice", "value": precaution_value}],
        "evidence_sources": [],
        "supporting_context": [],
        "disclaimer": "This is AI-assisted guidance and does not replace clinician review. Raw medical images may need specialist interpretation.",
    }


def _clean_text(value: object) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _load_env_value(key: str, fallback: str = "") -> str:
    env_path = Path(__file__).resolve().parents[2] / ".env"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or "=" not in stripped:
                continue
            env_key, env_value = stripped.split("=", 1)
            if env_key.strip() == key:
                cleaned = env_value.strip().strip('"').strip("'")
                if cleaned:
                    return cleaned
    value = os.getenv(key)
    return value or fallback


def _analysis_model_name() -> str:
    explicit = _clean_text(_load_env_value("GROQ_ANALYSIS_MODEL", ""))
    if explicit:
        return explicit
    shared = _clean_text(_load_env_value("GROQ_MODEL", ""))
    return shared or "llama-3.3-70b-versatile"


def _strip_json_fence(text: str) -> str:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.I)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    return cleaned.strip()


def _normalize_list_items(items: object, default_label: str) -> list[dict[str, str]]:
    normalized: list[dict[str, str]] = []
    if isinstance(items, list):
        for index, item in enumerate(items):
            if isinstance(item, dict):
                label = _clean_text(item.get("label") or item.get("name") or item.get("title") or f"{default_label} {index + 1}")
                value = _clean_text(item.get("value") or item.get("detail") or item.get("content") or item.get("reason"))
            else:
                label = f"{default_label} {index + 1}"
                value = _clean_text(item)
            if default_label == "Condition" and label.lower() in {f"condition {index + 1}".lower(), "condition", "predicted condition"}:
                parts = [segment.strip(" -:.") for segment in re.split(r"[:|-]", value, maxsplit=1) if segment.strip()]
                if parts:
                    label = parts[0][:72]
            if label and value:
                normalized.append({"label": label, "value": value})
    return normalized


def _normalize_analysis_payload(payload: dict, lab_values: dict, context_chunks: list[dict[str, str | float]]) -> dict:
    extracted_values = _merge_extracted_values(_normalize_extracted_values(lab_values), _normalize_extracted_values(payload.get("extracted_values")))
    supporting_context = []
    for item in context_chunks or []:
        source = _clean_text(item.get("source", "Medical context")) if isinstance(item, dict) else "Medical context"
        content = _clean_text(item.get("content", "")) if isinstance(item, dict) else ""
        if source and content:
            supporting_context.append({"label": source, "value": content[:380]})

    return {
        "report_type": _clean_text(payload.get("report_type")) or "Medical report",
        "clinical_explanation": _clean_text(payload.get("clinical_explanation")),
        "evidence_summary": _clean_text(payload.get("evidence_summary")),
        "symptoms_summary": _clean_text(payload.get("symptoms_summary")),
        "risk_level": _clean_text(payload.get("risk_level")) or "Preliminary",
        "confidence_level": _clean_text(payload.get("confidence_level")) or "Moderate",
        "doctor_specialist": _clean_text(payload.get("doctor_specialist")) or "Relevant specialist",
        "report_findings": _normalize_list_items(payload.get("report_findings"), "Finding"),
        "interpreted_lab_values": _normalize_list_items(payload.get("interpreted_lab_values"), "Lab value"),
        "predicted_conditions": _normalize_list_items(payload.get("predicted_conditions"), "Condition"),
        "recommended_tests": _normalize_list_items(payload.get("recommended_tests"), "Recommended test"),
        "suggested_blood_tests": _normalize_list_items(payload.get("suggested_blood_tests"), "Blood test"),
        "diet_recommendations": _normalize_list_items(payload.get("diet_recommendations"), "Diet"),
        "lifestyle_changes": _normalize_list_items(payload.get("lifestyle_changes"), "Lifestyle"),
        "precautions": _normalize_list_items(payload.get("precautions"), "Precaution"),
        "evidence_sources": _normalize_list_items(payload.get("evidence_sources"), "Evidence"),
        "supporting_context": _normalize_list_items(payload.get("supporting_context"), "Context") or supporting_context,
        "extracted_values": extracted_values,
        "disclaimer": _clean_text(payload.get("disclaimer"))
        or "This is AI-assisted medical guidance and does not replace an in-person clinician review.",
    }


def _collapse_value(value: object) -> str:
    if isinstance(value, list):
        parts: list[str] = []
        for item in value:
            if isinstance(item, dict):
                text = _clean_text(item.get("value") or item.get("label"))
            else:
                text = _clean_text(item)
            if text:
                parts.append(text)
        return " ".join(parts).strip()
    if isinstance(value, dict):
        return _clean_text(value.get("value") or value.get("label") or json.dumps(value, ensure_ascii=True))
    return _clean_text(value)


def _normalize_scalar_field(value: object) -> str:
    if isinstance(value, str):
        stripped = value.strip()
        if stripped.startswith("[") or stripped.startswith("{"):
            try:
                parsed = ast.literal_eval(stripped)
                return _collapse_value(parsed)
            except Exception:
                return _clean_text(stripped)
    return _collapse_value(value)


def _normalize_existing_result(result: dict, lab_values: dict, context_chunks: list[dict[str, str | float]]) -> dict:
    normalized = dict(result or {})
    scalar_fields = [
        "report_type",
        "clinical_explanation",
        "evidence_summary",
        "symptoms_summary",
        "risk_level",
        "confidence_level",
        "doctor_specialist",
        "disclaimer",
    ]
    for key in scalar_fields:
        normalized[key] = _normalize_scalar_field(normalized.get(key))

    list_fields = {
        "report_findings": "Finding",
        "interpreted_lab_values": "Lab value",
        "predicted_conditions": "Condition",
        "recommended_tests": "Recommended test",
        "suggested_blood_tests": "Blood test",
        "diet_recommendations": "Diet",
        "lifestyle_changes": "Lifestyle",
        "precautions": "Precaution",
        "evidence_sources": "Evidence",
        "supporting_context": "Context",
    }
    for key, label in list_fields.items():
        normalized[key] = _normalize_list_items(normalized.get(key), label)

    normalized["extracted_values"] = _merge_extracted_values(
        _normalize_extracted_values(lab_values),
        _normalize_extracted_values(normalized.get("extracted_values")),
    )
    if not normalized["supporting_context"]:
        normalized["supporting_context"] = [
            {"label": _clean_text(item.get("source", "Medical context")), "value": _clean_text(item.get("content", ""))[:380]}
            for item in context_chunks or []
            if isinstance(item, dict) and _clean_text(item.get("content", ""))
        ]
    normalized["risk_level"] = normalized.get("risk_level") or "Preliminary"
    normalized["confidence_level"] = normalized.get("confidence_level") or "Moderate"
    normalized["report_type"] = normalized.get("report_type") or "Medical report"
    normalized["doctor_specialist"] = normalized.get("doctor_specialist") or "Relevant specialist"
    normalized["disclaimer"] = normalized.get("disclaimer") or "This is AI-assisted medical guidance and does not replace an in-person clinician review."
    return normalized


def _merge_analysis_results(base_result: dict, groq_result: dict | None) -> dict:
    if not isinstance(base_result, dict):
        base_result = {}
    if not isinstance(groq_result, dict):
        return base_result

    merged = dict(base_result)
    list_fields = {
        "report_findings",
        "interpreted_lab_values",
        "predicted_conditions",
        "recommended_tests",
        "suggested_blood_tests",
        "diet_recommendations",
        "lifestyle_changes",
        "precautions",
        "evidence_sources",
        "supporting_context",
    }
    for key, value in groq_result.items():
        if key == "extracted_values":
            merged[key] = _merge_extracted_values(
                _normalize_extracted_values(merged.get(key)),
                _normalize_extracted_values(value),
            )
            continue
        if key in list_fields:
            if value:
                merged[key] = value
            elif key not in merged:
                merged[key] = []
            continue
        if _clean_text(value):
            merged[key] = value
        elif key not in merged:
            merged[key] = value
    return merged


def _normalize_extracted_value(value: object) -> float | str | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value) if isinstance(value, float) else value

    text = _normalize_scalar_field(value)
    if not text:
        return None
    if len(text) > 120:
        text = text[:120].rstrip(" ,;:.")

    if re.fullmatch(r"[-+]?\d+(?:\.\d+)?", text):
        try:
            numeric = float(text)
            return int(numeric) if numeric.is_integer() else numeric
        except ValueError:
            return text

    if re.fullmatch(r"[-+]?\d+(?:\.\d+)?\s*[A-Za-z/%^0-9._()/-]{1,24}", text):
        return text

    if re.fullmatch(r"[A-Za-z][A-Za-z0-9 ,:/()%+._-]{1,100}", text):
        return text

    return None


def _normalize_extracted_key(key: object) -> str:
    text = _clean_text(key)
    if not text:
        return ""
    text = re.sub(r"[_]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip(" :-,._")
    if not text or len(text) > 64:
        return ""
    acronym_map = {
        "bp": "BP",
        "spo2": "SpO2",
        "pr interval": "PR Interval",
        "qrs duration": "QRS Duration",
        "qtc": "QTc",
        "qtc interval": "QTc Interval",
        "ef": "Ejection Fraction",
        "hr": "Heart Rate",
        "rr": "Respiratory Rate",
        "st-t changes": "ST-T Changes",
    }
    lowered = text.lower()
    if lowered in acronym_map:
        return acronym_map[lowered]
    if re.fullmatch(r"[A-Za-z]{1,5}", text):
        return text.upper()
    return text.title()


def _normalize_extracted_values(values: object) -> dict[str, float | str]:
    normalized: dict[str, float | str] = {}
    if not isinstance(values, dict):
        return normalized

    for key, value in values.items():
        normalized_key = _normalize_extracted_key(key)
        normalized_value = _normalize_extracted_value(value)
        if not normalized_key or normalized_value is None:
            continue
        normalized[normalized_key] = normalized_value

    return normalized


def _merge_extracted_values(*sources: object) -> dict[str, float | str]:
    merged: dict[str, float | str] = {}
    for source in sources:
        for key, value in _normalize_extracted_values(source).items():
            if key not in merged or not _clean_text(merged.get(key)):
                merged[key] = value
    return merged


def _groq_analysis(
    compact_text: str,
    lab_values: dict,
    context_chunks: list[dict[str, str | float]],
) -> dict | None:
    api_key = _clean_text(_load_env_value("GROQ_API_KEY", ""))
    if not api_key:
        return None

    model = _analysis_model_name()
    context_block = "\n".join(
        f"- {_clean_text(item.get('source', 'Medical context'))}: {_clean_text(item.get('content', ''))[:480]}"
        for item in context_chunks[:3]
        if isinstance(item, dict) and _clean_text(item.get("content", ""))
    ) or "No additional retrieved context."
    values_block = json.dumps(lab_values or {}, ensure_ascii=True)

    prompt = (
        "You are HealthNova's medical report analysis engine.\n"
        "Use the report text, extracted lab values, and retrieved medical context together.\n"
        "The report may be any medical document: CBC, biochemistry, thyroid, ECG, X-ray report, CT, MRI, ultrasound, discharge summary, prescription, or other clinical report.\n"
        "If the report is not a lab panel, focus on the written impression, findings, abnormalities, rhythm, imaging observations, and follow-up advice instead of forcing lab-style output.\n"
        "Return only valid JSON with these keys: report_type, clinical_explanation, evidence_summary, symptoms_summary, "
        "risk_level, confidence_level, doctor_specialist, report_findings, interpreted_lab_values, "
        "predicted_conditions, recommended_tests, suggested_blood_tests, diet_recommendations, "
        "lifestyle_changes, precautions, evidence_sources, supporting_context, disclaimer.\n"
        "Also include extracted_values as an object of concise key-value pairs.\n"
        "Each list field must be an array of objects with label and value.\n"
        "Set report_type to a concise label like CBC, Blood test, ECG, X-ray report, CT report, MRI report, Ultrasound report, Prescription, Discharge summary, Pathology report, or Medical report.\n"
        "Use extracted_values to capture clinically relevant measurements or structured observations that appear in the report.\n"
        "For lab reports, include markers and values with units when available.\n"
        "For ECG reports, include items like heart rate, rhythm, PR interval, QRS duration, QTc, axis, and key abnormalities when present.\n"
        "For imaging reports, include measurable or named findings such as lesion size, mass size, stone size, organ size, ejection fraction, chamber dilation, fracture location, opacity, effusion, or impression when present.\n"
        "For discharge summaries or prescriptions, include important diagnoses, procedures, medicines, dosages, and follow-up intervals when they are explicitly present.\n"
        "Do not invent measurements. If a value is not shown, omit it.\n"
        "For predicted_conditions, provide 3 to 5 distinct differential possibilities when the data supports them.\n"
        "Do not repeat the same diagnosis with slightly different wording.\n"
        "Do not use generic labels like 'Condition'. Use the label as the actual disease or syndrome name.\n"
        "For each predicted condition value, explain briefly why it is possible from the report.\n"
        "Prefer clinically meaningful possibilities such as iron deficiency anemia, anemia of inflammation, thalassemia trait, hypothyroidism, infection, dehydration, etc when supported by the data.\n"
        "For ECG or imaging-style reports, it is acceptable for interpreted_lab_values and suggested_blood_tests to be empty.\n"
        "For imaging-style reports, report_findings should capture the key observations or impression in plain clinical terms.\n"
        "Only suggest blood tests when the uploaded report is actually blood-test related or when blood work is clearly needed as follow-up.\n"
        "For discharge summaries, prescriptions, pathology, ECG, and imaging reports, give report-specific interpretation and follow-up instead of generic CBC-style advice.\n"
        "If the report is readable but incomplete, summarize what is actually present and say what key details are missing.\n"
        "Keep it medically grounded and cautious. Do not invent unavailable facts.\n\n"
        f"Extracted lab values:\n{values_block}\n\n"
        f"Retrieved medical context:\n{context_block}\n\n"
        f"Report text:\n{compact_text[:2200]}"
    )

    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.2,
        "max_completion_tokens": 1200,
        "response_format": {"type": "json_object"},
    }

    try:
        response = httpx.post(
            "https://api.groq.com/openai/v1/chat/completions",
            json=payload,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}",
            },
            timeout=20,
        )
        response.raise_for_status()
        body = response.json()
        content = _clean_text(body["choices"][0]["message"]["content"])
        parsed = json.loads(_strip_json_fence(content))
        if not isinstance(parsed, dict):
            return None
        return _normalize_analysis_payload(parsed, lab_values, context_chunks)
    except Exception:
        return None


def _decode_text_bytes(file_bytes: bytes) -> str:
    for encoding in ("utf-8", "utf-16", "latin-1"):
        try:
            return file_bytes.decode(encoding, errors="ignore")
        except Exception:
            continue
    return ""


def _read_pdf_text(file_bytes: bytes, suffix: str) -> str:
    temp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix or ".pdf") as handle:
            handle.write(file_bytes)
            temp_path = Path(handle.name)
        return parse_pdf_text(temp_path)
    finally:
        if temp_path and temp_path.exists():
            try:
                temp_path.unlink()
            except Exception:
                pass


def _sanitize_raw_text(raw_text: str) -> str:
    if not raw_text:
        return ""

    sanitized_lines: list[str] = []
    for raw_line in raw_text.splitlines():
        line = re.sub(r"\s+", " ", raw_line).strip()
        if not line:
            continue

        def replace_suspicious_token(match: re.Match[str]) -> str:
            number = match.group(1)
            token = match.group(2).lower()
            return match.group(0) if token in _ALLOWED_UNIT_WORDS else number

        line = re.sub(r"\b(-?\d+(?:\.\d+)?)\s+([A-Za-z]{3,})\b", replace_suspicious_token, line)
        line = re.sub(r"(?<=\d)\s+(?=[A-Za-z]{4,}\b)", " ", line)
        line = re.sub(r"\b0\s+stic\b", "0", line, flags=re.I)
        sanitized_lines.append(line)

    return "\n".join(sanitized_lines).strip()


def _prepare_lab_values(values: dict) -> dict:
    prepared: dict = {}
    for key, value in (values or {}).items():
        if value is None:
            continue
        if isinstance(value, bool):
            continue
        if isinstance(value, (int, float)):
            prepared[key] = value
            continue
        text = str(value).strip()
        if not text:
            continue
        if len(text) > 48:
            continue
        if re.fullmatch(r"[-+]?(\d+(?:\.\d+)?)\s*[A-Za-z/%^0-9._/-]{0,16}", text):
            prepared[key] = text
            continue
        if re.fullmatch(r"[A-Za-z][A-Za-z0-9 .,_/%^+-]{1,32}", text):
            prepared[key] = text
    return prepared


def _build_query(raw_text: str, manual_text: str) -> str:
    combined = "\n".join(part for part in [manual_text.strip(), raw_text.strip()] if part.strip())
    return combined[:320]


def _compact_analysis_text(raw_text: str, manual_text: str) -> str:
    manual = manual_text.strip()
    lines = [re.sub(r"\s+", " ", line).strip() for line in raw_text.splitlines()]
    lines = [line for line in lines if line]

    selected: list[str] = []
    seen: set[str] = set()

    def push(line: str) -> None:
        normalized = line.lower()
        if not line or normalized in seen:
            return
        seen.add(normalized)
        selected.append(line)

    for line in lines:
        if _MEDICAL_PRIORITY_RE.search(line) or re.search(r"\d", line):
            push(line)
        if len(selected) >= 18:
            break

    if not selected:
        for line in lines[:12]:
            push(line)

    compact = "\n".join(selected)[:1500]
    return "\n".join(part for part in [manual, compact] if part).strip()[:1800]


def _summarize_lab_values_for_findings(lab_values: dict) -> list[dict[str, str]]:
    important_order = [
        "Hemoglobin",
        "WBC",
        "RBC",
        "Platelets",
        "Hematocrit",
        "PCV",
        "MCV",
        "MCH",
        "MCHC",
        "RDW",
        "MPV",
        "Neutrophils",
        "Lymphocytes",
        "Monocytes",
        "Eosinophils",
        "Basophils",
        "Glucose",
        "HbA1c",
        "Creatinine",
        "Urea",
        "BUN",
        "Bilirubin",
        "Total Bilirubin",
        "Direct Bilirubin",
        "Indirect Bilirubin",
        "ALT",
        "AST",
        "ALP",
        "TSH",
        "T3",
        "T4",
        "Free T3",
        "Free T4",
        "Sodium",
        "Potassium",
        "Chloride",
        "Calcium",
        "Ferritin",
        "Iron",
        "Vitamin B12",
        "Vitamin D",
        "CRP",
        "ESR",
    ]
    findings: list[dict[str, str]] = []
    for key in important_order:
        if key not in lab_values:
          continue
        value_text = _clean_text(lab_values.get(key))
        if value_text:
            findings.append({"label": key, "value": value_text})
    for key, value in (lab_values or {}).items():
        if any(item["label"] == key for item in findings):
            continue
        value_text = _clean_text(value)
        if value_text:
            findings.append({"label": key, "value": value_text})
    return findings[:16]


@router.post("/analyze")
async def analyze_report(file: UploadFile | None = File(None), manual_text: str | None = Form(None)) -> dict:
    manual_text = (manual_text or "").strip()
    if file is None and not manual_text:
        raise HTTPException(status_code=400, detail="Upload a report file or provide report text.")

    raw_text = ""
    suffix = ""
    file_name = _clean_text(getattr(file, "filename", ""))
    content_type = _clean_text(getattr(file, "content_type", "")).lower()

    if file is not None:
        suffix = Path(file.filename or "").suffix.lower()
        content_type = (file.content_type or "").lower()
        if suffix in _BLOCKED_EXTENSIONS or content_type.startswith("video/") or content_type == "image/gif":
            raise HTTPException(
                status_code=400,
                detail="Video and GIF files are not supported for report analysis. Upload a PDF, photo, or text-based report instead.",
            )
        file_bytes = await file.read()
        if not file_bytes and not manual_text:
            raise HTTPException(status_code=400, detail="The uploaded file is empty.")

        try:
            if suffix == ".pdf":
                raw_text = _read_pdf_text(file_bytes, suffix)
            elif suffix in _IMAGE_EXTENSIONS or content_type.startswith("image/"):
                raw_text = image_bytes_to_text(file_bytes)
            elif suffix in _TEXT_EXTENSIONS:
                raw_text = _decode_text_bytes(file_bytes)
            else:
                raw_text = _decode_text_bytes(file_bytes)
        except HTTPException:
            raise
        except Exception as error:
            raise HTTPException(status_code=422, detail=f"Could not read the uploaded report: {error}") from error

    combined_text = "\n".join(part for part in [manual_text, raw_text] if part).strip()
    sanitized_text = _sanitize_raw_text(combined_text)
    limited_image_capture = bool(file is not None and content_type.startswith("image/") and len(sanitized_text) < 40)
    if not sanitized_text:
        if file is not None and content_type.startswith("image/"):
            return _build_limited_image_result(raw_text, manual_text, file_name, content_type)
        raise HTTPException(
            status_code=422,
            detail="The uploaded report did not produce readable text. Try a clearer image or PDF, crop the report area, or upload another copy.",
        )

    try:
        lab_values = _prepare_lab_values(extract_lab_values(sanitized_text))
        hint_text = " ".join(part for part in [file_name, manual_text] if part).strip()
        compact_text = _compact_analysis_text(sanitized_text, hint_text)
        if limited_image_capture and not lab_values:
            return _build_limited_image_result(raw_text or sanitized_text, manual_text, file_name, content_type)
        numeric_value_count = sum(1 for value in lab_values.values() if isinstance(value, (int, float)))
        context_chunks = []
        if numeric_value_count <= 1 and len(compact_text) < 500:
            query = _build_query(compact_text, manual_text)
            context_chunks = retrieve_context(query, top_k=2)
        result = analyze_with_rag(lab_values=lab_values, context_chunks=context_chunks, raw_text=compact_text)
        result = _normalize_existing_result(result, lab_values, context_chunks)
        result = _merge_analysis_results(result, _groq_analysis(compact_text, lab_values, context_chunks))
        if not result.get("report_findings"):
            result["report_findings"] = _summarize_lab_values_for_findings(lab_values)
        if len(result.get("report_findings") or []) < 5:
            merged_findings = {item["label"]: item for item in _summarize_lab_values_for_findings(lab_values)}
            for item in result.get("report_findings") or []:
                merged_findings[item.get("label", "")] = item
            result["report_findings"] = [item for item in merged_findings.values() if item.get("label") and item.get("value")][:16]
        if not isinstance(result, dict):
            raise HTTPException(status_code=500, detail="The analysis engine returned an unexpected response.")
        return result
    except HTTPException:
        raise
    except ValueError as error:
        try:
            fallback_text = _compact_analysis_text(raw_text or sanitized_text, manual_text)
            fallback_context = retrieve_context(_build_query(fallback_text, manual_text), top_k=1) if fallback_text else []
            fallback_result = analyze_with_rag(lab_values={}, context_chunks=fallback_context, raw_text=fallback_text)
            fallback_result = _normalize_existing_result(fallback_result, {}, fallback_context)
            fallback_result = _merge_analysis_results(fallback_result, _groq_analysis(fallback_text, {}, fallback_context))
            if isinstance(fallback_result, dict):
                return fallback_result
        except Exception:
            pass
        raise HTTPException(
            status_code=422,
            detail="The uploaded report contains OCR text that could not be interpreted cleanly. Try a clearer image or PDF, crop the report area, or upload another copy.",
        ) from error
    except Exception as error:
        raise HTTPException(status_code=500, detail=f"Report analysis failed on the backend: {error}") from error

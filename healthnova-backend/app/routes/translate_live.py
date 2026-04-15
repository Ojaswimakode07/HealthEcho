from __future__ import annotations

import json
import os
import re
from pathlib import Path

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field


router = APIRouter(prefix="/translate", tags=["translate"])


class HindiTranslateRequest(BaseModel):
    texts: list[str] = Field(default_factory=list)


class HindiTranslateResponse(BaseModel):
    translations: list[str]


_TRANSLATE_BATCH_SIZE = 12


_PHRASE_TRANSLATIONS = {
    "high concern": "उच्च चिंता",
    "moderate concern": "मध्यम चिंता",
    "lower concern": "कम चिंता",
    "critical concern": "गंभीर चिंता",
    "report summary": "रिपोर्ट सारांश",
    "risk level": "जोखिम स्तर",
    "confidence": "विश्वास स्तर",
    "suggested specialist": "सुझाए गए विशेषज्ञ",
    "critical": "गंभीर",
    "high": "उच्च",
    "moderate": "मध्यम",
    "low": "कम",
    "normal": "सामान्य",
    "abnormal": "असामान्य",
    "doctor": "डॉक्टर",
    "follow-up": "फॉलो-अप",
    "next steps": "अगले कदम",
    "medical review": "चिकित्सीय जांच",
}

_WORD_TRANSLATIONS = {
    "report": "रिपोर्ट",
    "summary": "सारांश",
    "risk": "जोखिम",
    "level": "स्तर",
    "confidence": "विश्वास",
    "specialist": "विशेषज्ञ",
    "value": "मान",
    "values": "मान",
    "result": "परिणाम",
    "results": "परिणाम",
    "marker": "मार्कर",
    "markers": "मार्कर",
    "range": "सीमा",
    "normal": "सामान्य",
    "high": "उच्च",
    "low": "कम",
    "critical": "गंभीर",
    "positive": "पॉजिटिव",
    "negative": "नेगेटिव",
    "doctor": "डॉक्टर",
    "review": "जांच",
    "urgent": "तत्काल",
    "follow": "फॉलो",
    "up": "अप",
    "concern": "चिंता",
    "advice": "सलाह",
    "history": "इतिहास",
    "heart": "हृदय",
    "liver": "यकृत",
    "kidney": "किडनी",
    "thyroid": "थायरॉइड",
    "glucose": "ग्लूकोज",
    "platelets": "प्लेटलेट्स",
    "platelet": "प्लेटलेट",
    "hemoglobin": "हीमोग्लोबिन",
    "haemoglobin": "हीमोग्लोबिन",
    "creatinine": "क्रिएटिनिन",
    "bilirubin": "बिलिरुबिन",
    "summary:": "सारांश:",
}


def _load_env_value(key: str) -> str:
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
    if value:
        return value.strip().strip('"').strip("'")

    return ""


def _extract_json_payload(text: str) -> str:
    cleaned = str(text or "").strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip()
        cleaned = cleaned.removeprefix("```json").removeprefix("```JSON").removeprefix("```")
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()

    start_object = cleaned.find("{")
    end_object = cleaned.rfind("}")
    if start_object != -1 and end_object != -1 and end_object > start_object:
        return cleaned[start_object : end_object + 1]

    start_array = cleaned.find("[")
    end_array = cleaned.rfind("]")
    if start_array != -1 and end_array != -1 and end_array > start_array:
        return cleaned[start_array : end_array + 1]

    return cleaned


def _coerce_translations(parsed: object, texts: list[str]) -> list[str]:
    if isinstance(parsed, list):
        values = [str(item) for item in parsed]
    elif isinstance(parsed, dict):
        candidate = (
            parsed.get("translations")
            or parsed.get("translated_texts")
            or parsed.get("items")
            or parsed.get("results")
        )
        if isinstance(candidate, list):
            values = [str(item) for item in candidate]
        elif isinstance(candidate, dict):
            values = [str(candidate.get(str(index), "")) for index in range(len(texts))]
        else:
            values = []
    else:
        values = []

    if not values:
        return []

    if len(values) < len(texts):
        values.extend(texts[len(values) :])

    return values[: len(texts)]


def _call_groq_translate_batch(texts: list[str]) -> list[str]:
    api_key = _load_env_value("GROQ_API_KEY")
    model = _load_env_value("GROQ_MODEL") or "llama-3.3-70b-versatile"
    if not api_key:
        raise HTTPException(status_code=500, detail="Hindi translation is not configured on the backend.")

    prompt = (
        "Translate every input string to natural Hindi.\n"
        "Preserve medical numbers, units, abbreviations, lab markers, filenames, and structure.\n"
        "Do not invent new values.\n"
        "Return JSON only in this exact format: {\"translations\": [\"...\"]}.\n"
        "Keep the same order and same number of items as the input.\n\n"
        f"Input strings:\n{json.dumps(texts, ensure_ascii=False)}"
    )

    payload = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You translate medical UI/report text into natural Hindi. "
                    "Preserve numbers, units, marker names, filenames, and structure. "
                    "Return only valid JSON."
                ),
            },
            {
                "role": "user",
                "content": prompt,
            }
        ],
        "temperature": 0.2,
        "max_completion_tokens": 1800,
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
            timeout=90,
        )
        response.raise_for_status()
        body = response.json()
    except httpx.HTTPStatusError as exc:
        detail = exc.response.text if exc.response is not None else ""
        raise HTTPException(status_code=502, detail=f"Translation request failed: {detail or exc}") from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Translation request failed: {exc}") from exc

    try:
        text = body["choices"][0]["message"]["content"]
        if isinstance(text, list):
            text = "".join(str(part.get("text", "")) if isinstance(part, dict) else str(part) for part in text)
        parsed = json.loads(_extract_json_payload(text))
        translations = _coerce_translations(parsed, texts)
    except Exception as exc:
        raise HTTPException(status_code=502, detail="The translation service returned an unexpected response.") from exc

    if not isinstance(translations, list) or not translations:
        raise HTTPException(status_code=502, detail="The translation service returned an incomplete translation set.")

    return [str(item) for item in translations]


def _call_groq_translate(texts: list[str]) -> list[str]:
    if not texts:
        return []

    translated: list[str] = []
    for start in range(0, len(texts), _TRANSLATE_BATCH_SIZE):
        batch = texts[start : start + _TRANSLATE_BATCH_SIZE]
        translated.extend(_call_groq_translate_batch(batch))
    return translated


def _replace_phrase(text: str, phrase: str, replacement: str) -> str:
    return re.sub(rf"(?i)\b{re.escape(phrase)}\b", replacement, text)


def _fallback_translate_text(text: str) -> str:
    translated = str(text or "")
    if not translated.strip():
        return translated

    for phrase, replacement in _PHRASE_TRANSLATIONS.items():
        translated = _replace_phrase(translated, phrase, replacement)

    parts = re.split(r"(\s+|[():;,\-.])", translated)
    mapped: list[str] = []
    for part in parts:
        key = part.strip().lower()
        if key and key in _WORD_TRANSLATIONS:
            replacement = _WORD_TRANSLATIONS[key]
            suffix = part[len(part.rstrip()):] if part.rstrip() != part else ""
            prefix = part[: len(part) - len(part.lstrip())] if part.lstrip() != part else ""
            mapped.append(f"{prefix}{replacement}{suffix}")
        else:
            mapped.append(part)

    final_text = "".join(mapped)
    final_text = re.sub(r"\bThis report\b", "यह रिपोर्ट", final_text, flags=re.I)
    final_text = re.sub(r"\bThis result\b", "यह परिणाम", final_text, flags=re.I)
    final_text = re.sub(r"\bneeds urgent medical review\b", "के लिए तुरंत चिकित्सीय जांच जरूरी है", final_text, flags=re.I)
    final_text = re.sub(r"\bplease contact a clinician right away\b", "कृपया तुरंत डॉक्टर से संपर्क करें", final_text, flags=re.I)
    return final_text


def _fallback_translate_batch(texts: list[str]) -> list[str]:
    return [_fallback_translate_text(text) for text in texts]


@router.post("/hindi", response_model=HindiTranslateResponse)
async def translate_hindi(payload: HindiTranslateRequest) -> HindiTranslateResponse:
    texts = [text.strip() for text in payload.texts if isinstance(text, str) and text.strip()]
    if not texts:
        return HindiTranslateResponse(translations=[])

    try:
        translations = _call_groq_translate(texts)
    except HTTPException:
        translations = _fallback_translate_batch(texts)
    return HindiTranslateResponse(translations=translations)

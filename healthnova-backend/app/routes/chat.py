from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any
from urllib import error

import httpx
from fastapi import APIRouter

from app.core.config import settings
from app.core.schemas import ChatRequest, ChatResponse
from app.modules.retriever import retrieve_context

router = APIRouter()

DISCLAIMER = "This system provides AI-based health risk insights and is not a substitute for professional medical advice."


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
    if value:
        return value

    return fallback


def _chat_model_name() -> str:
    explicit = _clean_text(_load_env_value("GROQ_CHAT_MODEL", ""))
    if explicit:
        return explicit

    shared = _clean_text(_load_env_value("GROQ_MODEL", ""))
    if shared and "70b" not in shared.lower() and "versatile" not in shared.lower():
        return shared

    return "llama-3.1-8b-instant"


def _clean_text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _trim_history(history: list[Any], limit: int = 24) -> list[dict[str, str]]:
    normalized: list[dict[str, str]] = []
    for item in history or []:
        role = _clean_text(getattr(item, "role", "") or (item.get("role") if isinstance(item, dict) else ""))
        content = _clean_text(getattr(item, "content", "") or (item.get("content") if isinstance(item, dict) else ""))
        if role in {"user", "assistant"} and content:
            normalized.append({"role": role, "content": content})
    return normalized[-limit:]


def _summary_lines(analysis_summary: dict[str, Any] | None) -> list[str]:
    summary = analysis_summary or {}
    lines: list[str] = []

    title = _clean_text(summary.get("title"))
    report_summary = _clean_text(summary.get("summary"))
    risk_level = _clean_text(summary.get("risk_level"))
    confidence_level = _clean_text(summary.get("confidence_level"))
    doctor_specialist = _clean_text(summary.get("doctor_specialist"))

    if title:
        lines.append(f"Report title: {title}")
    if report_summary:
        lines.append(f"Report summary: {report_summary}")
    if risk_level:
        lines.append(f"Risk level: {risk_level}")
    if confidence_level:
        lines.append(f"Confidence: {confidence_level}")
    if doctor_specialist:
        lines.append(f"Suggested specialist: {doctor_specialist}")

    extracted_values = summary.get("extracted_values")
    if isinstance(extracted_values, dict) and extracted_values:
        values_preview = []
        for key, value in list(extracted_values.items())[:8]:
            key_text = _clean_text(key)
            value_text = _clean_text(value)
            if key_text and value_text:
                values_preview.append(f"{key_text}: {value_text}")
        if values_preview:
            lines.append("Report values: " + "; ".join(values_preview))

    return lines


def _history_block(history: list[dict[str, str]]) -> str:
    if not history:
        return "No prior conversation."
    rendered = []
    for turn in history:
        speaker = "Patient" if turn["role"] == "user" else "Assistant"
        rendered.append(f"{speaker}: {turn['content']}")
    return "\n".join(rendered)


def _recent_assistant_replies(history: list[dict[str, str]], limit: int = 3) -> list[str]:
    replies = [_clean_text(turn.get("content")) for turn in history if turn.get("role") == "assistant"]
    return [reply for reply in replies[-limit:] if reply]


def _context_block(question: str, analysis_summary: dict[str, Any] | None) -> str:
    cleaned_question = _clean_text(question)
    if len(cleaned_question) > 220:
        return "No external medical context retrieved."

    summary = analysis_summary or {}
    extracted_values = summary.get("extracted_values")
    if isinstance(extracted_values, dict) and len(extracted_values) >= 4:
        return "No external medical context retrieved."
    if not summary and (
        len(re.findall(r"[a-z0-9]+", cleaned_question.lower())) <= 12
        or _contains_nausea_context(cleaned_question.lower())
        or _contains_period_context(cleaned_question.lower())
    ):
        return "No external medical context retrieved."

    query_parts = [question]
    query_parts.extend(_summary_lines(analysis_summary))
    query = "\n".join(part for part in query_parts if part).strip()
    chunks = retrieve_context(query=query, top_k=1)
    if not chunks:
        return "No external medical context retrieved."

    formatted = []
    for item in chunks[:3]:
        source = _clean_text(item.get("source", "Medical context"))
        content = _clean_text(item.get("content", ""))[:600]
        if content:
            formatted.append(f"[{source}] {content}")
    return "\n".join(formatted) if formatted else "No external medical context retrieved."


def _needs_follow_up(question: str) -> bool:
    text = question.lower()
    tokens = re.findall(r"[a-z0-9]+", text)
    if len(tokens) <= 4:
        return True
    broad_patterns = [
        r"\bwhat should i do\b",
        r"\bis this serious\b",
        r"\bhelp me\b",
        r"\bwhat does this mean\b",
        r"\bfeeling (bad|sick|weak|tired)\b",
    ]
    return any(re.search(pattern, text) for pattern in broad_patterns)


def _is_simple_smalltalk(question: str) -> bool:
    text = _clean_text(question).lower().strip("?.!, ")
    if not text:
        return True
    simple_phrases = {
        "hi",
        "hello",
        "hey",
        "hii",
        "hiii",
        "ok",
        "okay",
        "thanks",
        "thank you",
        "thx",
        "hmm",
        "hmmm",
        "yes",
        "no",
    }
    if text in simple_phrases:
        return True
    tokens = re.findall(r"[a-z0-9]+", text)
    return len(tokens) <= 2 and all(token in {"hi", "hello", "hey", "thanks", "ok", "okay", "yes", "no"} for token in tokens)


def _should_use_fast_local_reply(question: str, analysis_summary: dict[str, Any] | None, history: list[dict[str, str]]) -> bool:
    text = _clean_text(question).lower()
    token_count = len(re.findall(r"[a-z0-9]+", text))
    if _is_simple_smalltalk(text):
        return True
    if token_count <= 2 and not analysis_summary and not history:
        return True
    if len(text) <= 8 and not re.search(r"[0-9]", text) and not any(
        (
            _contains_period_context(text),
            _contains_nausea_context(text),
            _contains_sexual_context(text),
        )
    ):
        return True
    return False


def _recent_user_context(history: list[dict[str, str]], limit: int = 3) -> str:
    recent = [turn["content"] for turn in history if turn.get("role") == "user"]
    cleaned = [_clean_text(item) for item in recent[-limit:] if _clean_text(item)]
    return " | ".join(cleaned)


def _contains_period_context(text: str) -> bool:
    return bool(
        re.search(
            r"\b(period|periods|menstrual|mens|menses|cramps?)\b|perio[dfl]\b|perio\b",
            text,
        )
    )


def _contains_nausea_context(text: str) -> bool:
    return bool(re.search(r"\b(nausea|nauseous|vomit|vomiting|feeling sick)\b", text))


def _contains_sexual_context(text: str) -> bool:
    return bool(
        re.search(
            r"\b(sex|sexual|intercourse|pregnan|pregnancy|pregnant|condom|contracept|protected sex|unprotected sex|std|sti)\b",
            text,
        )
    )


def _lab_trend_reply(text: str) -> str:
    patterns = [
        (
            r"\blow\b.*\b(hemoglobin|haemoglobin|hb)\b|\b(hemoglobin|haemoglobin|hb)\b.*\blow\b",
            "Low hemoglobin usually suggests anemia or blood loss. Common causes include iron deficiency, vitamin B12 or folate deficiency, heavy periods, chronic disease, or less commonly bleeding from the stomach or bowel. If you also have shortness of breath, chest pain, black stools, or severe weakness, get medical care urgently.",
        ),
        (
            r"\bhigh\b.*\bplatelet|\bplatelets?\b.*\bhigh\b",
            "High platelets can happen with infection, inflammation, iron deficiency, recent bleeding, or sometimes bone marrow-related conditions. Doctors usually interpret it together with hemoglobin, ferritin, CRP, and symptoms rather than as a single number alone.",
        ),
        (
            r"\blow\b.*\bplatelet|\bplatelets?\b.*\blow\b",
            "Low platelets can increase bleeding or bruising risk. Causes range from viral illness and medicines to immune conditions or liver problems. Urgent review is important if you have gum bleeding, nosebleeds, black stools, or unusual bruising.",
        ),
        (
            r"\bhigh\b.*\btsh\b|\btsh\b.*\bhigh\b",
            "A high TSH often suggests the thyroid may be underactive, especially if free T4 is low. People may notice tiredness, weight gain, constipation, dry skin, hair fall, or feeling cold. Doctors usually confirm it with T3 and T4 and sometimes thyroid antibodies.",
        ),
        (
            r"\blow\b.*\btsh\b|\btsh\b.*\blow\b",
            "A low TSH can suggest an overactive thyroid, especially if T3 or T4 are high. Symptoms can include palpitations, anxiety, weight loss, tremor, sweating, or loose motions. It should be interpreted with the full thyroid panel.",
        ),
        (
            r"\bhigh\b.*\b(glucose|sugar|hba1c)\b|\b(glucose|sugar|hba1c)\b.*\bhigh\b",
            "High glucose or HbA1c can suggest diabetes or stress-related high sugar, depending on the exact number and whether the sample was fasting. Excess thirst, frequent urination, weight loss, vomiting, or drowsiness need quicker medical review.",
        ),
        (
            r"\bhigh\b.*\bcreatinine\b|\bcreatinine\b.*\bhigh\b",
            "High creatinine can suggest reduced kidney filtration, dehydration, or a medicine-related effect. Doctors usually compare it with older values, urine findings, blood pressure, and symptoms like swelling or reduced urine output.",
        ),
    ]
    for pattern, message in patterns:
        if re.search(pattern, text):
            return message
    return ""


def _is_clear_topic_shift(text: str, recent_user_notes: str) -> bool:
    if not text or not recent_user_notes:
        return False

    current_is_sexual = _contains_sexual_context(text)
    recent_is_sexual = _contains_sexual_context(recent_user_notes)
    current_is_period = _contains_period_context(text)
    recent_is_period = _contains_period_context(recent_user_notes)
    current_is_nausea = _contains_nausea_context(text)
    recent_is_nausea = _contains_nausea_context(recent_user_notes)

    return any(
        [
            current_is_sexual and not recent_is_sexual,
            current_is_period and not recent_is_period,
            current_is_nausea and not recent_is_nausea,
        ]
    )


def _explain_report_term(term: str) -> str:
    normalized = _clean_text(term).lower().strip(" ?.!:,;")
    definitions = {
        "anemia": "Anemia means your blood may not be carrying enough oxygen efficiently, usually because hemoglobin is low. It can cause tiredness, weakness, dizziness, shortness of breath, or paleness. Common causes include iron deficiency, vitamin deficiency, blood loss, or some chronic illnesses.",
        "haemoglobin": "Hemoglobin is the protein in red blood cells that carries oxygen around the body. If it is low, doctors often think about anemia or blood loss. If it is high, they may look at dehydration or other causes.",
        "hemoglobin": "Hemoglobin is the protein in red blood cells that carries oxygen around the body. If it is low, doctors often think about anemia or blood loss. If it is high, they may look at dehydration or other causes.",
        "rbc": "RBC means red blood cell count. Red blood cells help carry oxygen. Doctors look at RBC together with hemoglobin, MCV, and other CBC values to understand anemia or other blood patterns.",
        "wbc": "WBC means white blood cell count. White blood cells help fight infection and inflammation. Doctors interpret WBC together with symptoms and the differential count like neutrophils and lymphocytes.",
        "platelets": "Platelets help your blood clot and stop bleeding. Low platelets can increase bruising or bleeding risk, while high platelets can happen with inflammation, infection, iron deficiency, or other causes.",
        "platelet": "Platelets help your blood clot and stop bleeding. Low platelets can increase bruising or bleeding risk, while high platelets can happen with inflammation, infection, iron deficiency, or other causes.",
        "creatinine": "Creatinine is a blood marker used to estimate how well the kidneys are filtering. Higher values can suggest reduced kidney function, dehydration, or other kidney-related issues, but doctors interpret it with age, muscle mass, medicines, and other labs.",
        "tsh": "TSH is a thyroid-related hormone. It helps doctors understand whether the thyroid may be underactive or overactive, usually together with T3 and T4 values.",
        "glucose": "Glucose is your blood sugar level. Doctors use it to check for low sugar, high sugar, diabetes, or stress-related rises, depending on timing and other tests like HbA1c.",
        "hba1c": "HbA1c reflects your average blood sugar over the last two to three months. It is commonly used to screen for diabetes or to monitor how well diabetes is controlled.",
    }
    return definitions.get(normalized, "")


def _build_prompt(question: str, analysis_summary: dict[str, Any] | None, history: list[dict[str, str]]) -> str:
    summary_lines = _summary_lines(analysis_summary)
    report_context = "\n".join(summary_lines) if summary_lines else "No report summary available."
    medical_context = _context_block(question, analysis_summary)
    recent_context = _recent_user_context(history)
    recent_assistant_replies = _recent_assistant_replies(history)
    follow_up_rule = (
        "If key medical detail is missing, end with exactly one short follow-up question."
        if _needs_follow_up(question)
        else "Do not ask a follow-up question unless it is necessary for safe guidance."
    )

    return (
        "You are HealthNova, a fast, practical health and medical follow-up assistant.\n"
        "Stay strictly within health, medical, report-interpretation, symptom, medicine-safety, and care-navigation topics.\n"
        "If the user asks a non-medical question, briefly say this chat is for health and medical help and ask them to send a health-related question.\n"
        "Answer like a careful clinician chatting with a patient: warm, clear, specific, and interactive.\n"
        "Sound natural and concise, not robotic, not like a template, and not like a discharge note.\n"
        "Keep answers brief by default.\n"
        "Give a direct answer first, then the likely explanation, then what to do next.\n"
        "Use the conversation history so each answer feels connected and real.\n"
        "Treat short follow-up questions as part of the current health discussion unless the user clearly changes topic.\n"
        "Do not repeat previous assistant wording, repeated summaries, or the same closing advice from earlier turns.\n"
        "If the user asks a follow-up, answer that new point directly instead of restating the whole report unless needed.\n"
        "If symptoms or report values suggest more than one possibility, mention the most likely 2 to 4 possibilities, not just one repeated condition.\n"
        "If the question is about symptoms, discuss the likely cause, home care, red flags, and when to get medical help.\n"
        "If the question is about a report, explain the important values in simple language and what they may suggest.\n"
        "If the user asks a very broad question, ask at most one short follow-up question.\n"
        "Never say you are an AI. Do not give a stock disclaimer unless there is a real safety reason.\n"
        "Avoid vague generic filler like 'consult a doctor' unless you also say why or when.\n"
        "Do not start with phrases like 'You're experiencing', 'This can be concerning', or 'The most likely possibilities include'.\n"
        "Do not use bold markdown labels like '**Direct Medical Answer:**' or '**What to Do Next:**'.\n"
        "If structure helps, use 2 to 4 short plain bullets.\n"
        "Prefer clean bullets or 1 to 2 short paragraphs.\n"
        "Keep the tone calm, plain-English, and conversational.\n"
        "Priorities:\n"
        "1. Answer the patient's exact question first.\n"
        "2. Connect the answer to their symptoms and report data when available.\n"
        "3. Mention the most important likely causes or interpretations.\n"
        "4. Say what is reassuring vs concerning.\n"
        "5. Give practical next steps.\n"
        "6. Escalate urgent red flags immediately.\n"
        f"6. {follow_up_rule}\n"
        "Keep the answer around 35 to 70 words unless the user explicitly asks for more detail.\n"
        "Use short paragraphs and short sentences.\n"
        "Do not add extra background unless it changes what the user should do next.\n"
        "When using bullets, keep each bullet short and useful.\n"
        "Avoid repeating the same sentence structure across replies.\n"
        "If the question is outside the available data, say what is missing and answer cautiously.\n\n"
        f"Report context:\n{report_context}\n\n"
        f"Conversation so far:\n{_history_block(history)}\n\n"
        f"Recent assistant replies to avoid repeating:\n{chr(10).join(recent_assistant_replies) if recent_assistant_replies else 'None.'}\n\n"
        f"Recent user health context:\n{recent_context or 'No recent user context.'}\n\n"
        f"Retrieved medical context:\n{medical_context}\n\n"
        f"Latest patient question:\n{_clean_text(question)}"
    )


def _groq_generate(prompt: str) -> str:
    api_key = _clean_text(_load_env_value("GROQ_API_KEY", ""))
    model = _chat_model_name()
    if not api_key:
        return ""

    payload = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": prompt,
            }
        ],
        "temperature": 0.2,
        "max_completion_tokens": 260,
    }
    request_error: Exception | None = None
    body: dict[str, Any] | None = None
    for attempt in range(2):
        try:
            response = httpx.post(
                "https://api.groq.com/openai/v1/chat/completions",
                json=payload,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {api_key}",
                },
                timeout=12,
            )
            response.raise_for_status()
            body = response.json()
            break
        except httpx.HTTPStatusError as exc:
            detail = exc.response.text
            try:
                parsed = json.loads(detail)
                message = _clean_text(parsed.get("error", {}).get("message", ""))
            except Exception:
                message = ""
            status_code = exc.response.status_code if exc.response is not None else "unknown"
            raise RuntimeError(message or f"Groq request failed with HTTP {status_code}.") from exc
        except (httpx.TimeoutException, httpx.NetworkError, httpx.TransportError, OSError) as exc:
            request_error = exc
            if attempt == 0:
                continue
            raise RuntimeError("Groq chat timed out or could not be reached.") from exc
    if body is None and request_error is not None:
        raise RuntimeError("Groq chat timed out or could not be reached.") from request_error
    try:
        return _clean_text(body["choices"][0]["message"]["content"])
    except Exception:
        return ""


def _fallback_chat_reply(question: str, analysis_summary: dict[str, Any] | None, history: list[dict[str, str]] | None = None) -> str:
    summary = _clean_text((analysis_summary or {}).get("summary"))
    risk_level = _clean_text((analysis_summary or {}).get("risk_level"))
    specialist = _clean_text((analysis_summary or {}).get("doctor_specialist")) or "doctor"
    text = question.lower()
    recent_user_notes = " ".join(turn["content"] for turn in (history or []) if turn.get("role") == "user").lower()
    vague_question = len(re.findall(r"[a-z0-9]+", text)) <= 4 or bool(
        re.search(r"\bwhat about this\b|\band this\b|\bwhat now\b|\bthen what\b|\bis it serious\b", text)
    )
    current_has_period_context = _contains_period_context(text)
    current_has_nausea_context = _contains_nausea_context(text)
    current_has_sexual_context = _contains_sexual_context(text)

    if current_has_period_context:
        context_text = text
    elif current_has_nausea_context:
        context_text = text
    elif current_has_sexual_context:
        context_text = text
    elif _is_clear_topic_shift(text, recent_user_notes):
        context_text = text
    elif vague_question:
        context_text = f"{recent_user_notes} {text}".strip()
    else:
        context_text = text

    def with_context(message: str) -> str:
        extra = f" Your report summary suggests: {summary}." if summary else ""
        return f"{message}{extra}".strip()

    explain_match = re.search(r"\bwhat is ([a-z][a-z\s]{1,40})\b", text)
    explain_term = _clean_text(explain_match.group(1)) if explain_match else ""
    if not explain_term and re.fullmatch(r"[a-z][a-z\s]{1,30}\??", text):
        explain_term = _clean_text(text.rstrip("?"))
    if explain_term:
        direct_explanation = _explain_report_term(explain_term)
        if direct_explanation:
            return with_context(direct_explanation)

    lab_trend_message = _lab_trend_reply(text)
    if lab_trend_message:
        return with_context(lab_trend_message)

    if re.search(r"\bwhat disease do i have\b|\bwhat problem do i have\b|\bwhat illness do i have\b", text):
        if summary:
            return with_context(
                "I cannot name a final disease from this alone. The report points more toward findings that need doctor interpretation than a confirmed diagnosis."
            )
        return "I cannot diagnose a disease from this alone. Share the main report values, symptoms, and how long they have been present, and I can help interpret what they may suggest."

    if re.search(r"\bexplain\b.*\breport\b|\bsimpler language\b|\bwhat does this report mean\b", text):
        if summary:
            return f"In simple terms, your report looks {risk_level.lower() if risk_level else 'not immediately dangerous'} overall. {summary} Tell me which exact value or finding confused you most, and I will explain that part in plain language."
        return "In simple terms, I need the main values or findings from the report to explain it properly. Share the numbers or upload summary, and I will translate it into plain language."

    if re.search(r"\bwhich values?\b.*\bcloser follow[- ]?up\b|\bwhich values?\b.*\bhigh\b|\bwhich values?\b.*\blow\b|\bwhich values?\b.*\babnormal\b", text):
        if summary:
            return with_context(
                "The values worth closer follow-up are the ones marked outside range, borderline, or repeatedly changing over time. If you paste the exact CBC, thyroid, sugar, kidney, or liver values, I can point out which ones matter most."
            )
        return "The main values needing closer follow-up are usually the ones outside the lab range, borderline, or changing from earlier tests. Paste the exact values and ranges, and I will sort them by priority."

    if re.search(r"\bwhat should i ask my doctor\b|\bquestions? for my doctor\b", text):
        return (
            f"You can ask: what is the main abnormal finding, how serious is it, what could be causing it, do I need repeat testing, "
            f"what symptoms should make me seek urgent care, and should I see a {specialist.lower()}? "
            "If you want, I can turn your exact report into 5 specific doctor questions."
        )

    if re.search(r"\bwhat is in the report\b|\bwhat is in the reports\b|\bwhat does the report say\b|\bwhat's in the report\b|\bsummary of the report\b", text):
        if summary:
            return f"Your report summary says: {summary} The overall reported risk is {risk_level or 'not clearly stated'}. If you want, I can break it into simple language, abnormal values, and questions to ask your doctor."
        return "I can summarize the report, but I need the extracted values or findings first. Share the report summary or upload results, and I will explain what is in it."

    if re.search(r"\bwhich medicine\b|\bwhat medicine\b|\bwhich tablet\b|\bwhat tablet\b|\bwhat should i take\b|\bwhat medicine should i take\b", text):
        return (
            "I cannot safely prescribe a medicine for you here. The right choice depends on the symptom, your age, allergies, pregnancy status, stomach or kidney problems, and other medicines you take. "
            "Tell me the exact symptom you want relief for, how severe it is, and whether you are pregnant or have ulcers, and I can tell you the usual over-the-counter options people discuss with a clinician."
        )

    if current_has_period_context:
        return (
            "If this is related to your period, tell me whether you mean cramps, nausea, heavy bleeding, delayed periods, or something else. "
            "If you have severe pain, fainting, soaking pads quickly, or think you might be pregnant, get urgent medical care."
        )

    if current_has_sexual_context:
        return (
            "If this is about sex, tell me what you mean exactly: pain during sex, whether sex is safe with your symptom, pregnancy risk, contraception, or concern about infection. "
            "If there was unprotected sex, severe pain, bleeding, fever, genital sores, or unusual discharge, get medical advice promptly."
        )

    if re.search(r"\bnausea|nauseous|vomit|vomiting|feeling sick\b", context_text):
        return (
            "For nausea right now, sip water or ORS slowly, avoid oily or heavy food, and rest. "
            "Get urgent care if you cannot keep fluids down, have severe belly pain, blood in vomit, fainting, chest pain, or signs of dehydration. "
            "How long have you felt nauseous, and have you vomited?"
        )

    if re.search(r"\b(go to school|go school|school|college|office|work)\b", text) and re.search(
        r"\b(feel|feeling|felt|sick|unwell|ill|fever|cough|cold|vomit|vomiting|nausea|pain|weak|weakness|tired|fatigue|headache|diarrhea)\b",
        context_text,
    ):
        return (
            "If you are still feeling unwell, have fever, vomiting, diarrhea, significant weakness, or symptoms that are getting worse, it is better to rest and avoid going to school today. "
            "If symptoms are mild, improving, and you can eat, drink, and manage normal activity, you may be able to go, but monitor yourself closely. "
            "Tell me your main symptom right now and whether you have fever."
        )

    if re.search(r"\bhow to increase\b.*\bplatelet|\bplatelets?\b.*\b(increase|improve|raise)\b", context_text):
        return (
            "To help support low platelets, the first step is understanding the cause. Supportive steps usually include treating infection if present, avoiding alcohol, avoiding aspirin or similar painkillers unless a doctor advised them, and using balanced meals with enough protein, folate, B12, iron, and vitamin C. "
            "Get medical review sooner if you have bruising, gum bleeding, black stools, or a clearly falling platelet count. "
            "If you share the platelet value and range, I can tell you how concerning it looks."
        )

    if re.search(r"\bperiod cramps\b|\bmenstrual cramps\b|\bcramps\b", context_text) or _contains_period_context(context_text):
        return (
            "For period cramps, try a heating pad on the lower abdomen, rest, drink water, and if you normally tolerate them, use your usual pain relief such as ibuprofen or mefenamic acid only as previously advised by a clinician. "
            "Get checked urgently if the pain is unusually severe, you are soaking pads quickly, feel faint, or might be pregnant. "
            "Is this pain similar to your usual periods or much worse than normal?"
        )

    response_parts = []
    if summary:
        response_parts.append(f"Based on your report, {summary[0].lower() + summary[1:] if len(summary) > 1 else summary}")
    else:
        response_parts.append("I can help with that, but I need to stay close to the symptoms or report details you shared.")

    question_lower = question.lower()
    if any(token in question_lower for token in ["serious", "urgent", "emergency", "danger"]):
        response_parts.append("If you have chest pain, trouble breathing, fainting, severe bleeding, or confusion, get urgent in-person care now.")
    elif risk_level:
        response_parts.append(f"Your current report risk level appears to be {risk_level}.")

    response_parts.append("Tell me the exact symptom duration, severity, and any recent test value, and I will answer more precisely.")
    return " ".join(response_parts)


def _clean_chat_reply(text: str) -> str:
    cleaned = _clean_text(text)
    cleaned = re.sub(r"\b(as an ai|i am an ai|i'm an ai)\b[^.]*\.?", "", cleaned, flags=re.I)
    cleaned = re.sub(r"\bmedical disclaimer:\b", "", cleaned, flags=re.I)
    return _clean_text(cleaned)


def _normalize_for_similarity(text: str) -> str:
    return re.sub(r"[^a-z0-9\s]", "", _clean_text(text).lower())


def _is_too_similar_to_recent_reply(answer: str, history: list[dict[str, str]]) -> bool:
    normalized_answer = _normalize_for_similarity(answer)
    if not normalized_answer:
        return False
    for previous in _recent_assistant_replies(history, limit=2):
        normalized_previous = _normalize_for_similarity(previous)
        if not normalized_previous:
            continue
        if normalized_answer == normalized_previous:
            return True
        answer_words = set(normalized_answer.split())
        previous_words = set(normalized_previous.split())
        if not answer_words or not previous_words:
            continue
        overlap = len(answer_words & previous_words) / max(1, min(len(answer_words), len(previous_words)))
        if overlap >= 0.82:
            return True
    return False


def chat_follow_up(question: str, analysis_summary: dict[str, Any] | None = None, history: list[Any] | None = None) -> str:
    normalized_question = _clean_text(question)
    normalized_history = _trim_history(history or [])
    api_key_present = bool(_clean_text(_load_env_value("GROQ_API_KEY", "")))

    if not api_key_present:
        return "Groq chat is not configured on the backend yet. Add a valid Groq API key to enable medical answers."

    answer = ""
    provider_error = ""
    try:
        prompt = _build_prompt(normalized_question, analysis_summary, normalized_history)
        answer = _groq_generate(prompt)
        if answer and _is_too_similar_to_recent_reply(answer, normalized_history):
            retry_prompt = (
                f"{prompt}\n\n"
                "Your first draft was too similar to a recent assistant reply. "
                "Write a fresh answer that directly addresses only the newest question, "
                "without repeating the previous explanation."
            )
            retry_answer = _groq_generate(retry_prompt)
            if retry_answer:
                answer = retry_answer
    except (httpx.HTTPError, error.URLError, TimeoutError, OSError, ValueError, RuntimeError) as exc:
        provider_error = _clean_text(exc)
        answer = ""

    if not answer:
        if provider_error:
            answer = f"Groq chat is unavailable right now: {provider_error}"
        else:
            answer = "Groq chat is temporarily unavailable right now. Please try again in a moment."

    cleaned = _clean_chat_reply(answer)
    return cleaned or "Groq chat is temporarily unavailable right now. Please try again in a moment."


@router.post("/chat", response_model=ChatResponse)
async def chat(payload: ChatRequest) -> ChatResponse:
    answer = chat_follow_up(
        question=payload.question,
        analysis_summary=payload.analysis_summary or {},
        history=payload.history or [],
    )
    return ChatResponse(answer=answer, disclaimer=DISCLAIMER)


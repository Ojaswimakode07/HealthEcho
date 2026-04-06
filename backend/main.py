from datetime import datetime
from pathlib import Path
from typing import Optional
import json
import os
import re
import sqlite3
import subprocess

from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image
from pydantic import BaseModel
import pytesseract
import requests


BASE_DIR = Path(__file__).resolve().parent


def load_env_file(path: Path) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


load_env_file(BASE_DIR / ".env")

DB_PATH = os.getenv("HEALTHECHO_DB_PATH", str(BASE_DIR / "healthecho.db"))
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2")
HOST = os.getenv("HEALTHECHO_HOST", "0.0.0.0")
PORT = int(os.getenv("HEALTHECHO_PORT", "8000"))
ALLOW_ORIGINS = [
    origin.strip()
    for origin in os.getenv("HEALTHECHO_ALLOW_ORIGINS", "*").split(",")
    if origin.strip()
]

app = FastAPI(title="HealthEcho API", version="5.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOW_ORIGINS or ["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def init_db() -> None:
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        """CREATE TABLE IF NOT EXISTS consultations
                 (id INTEGER PRIMARY KEY, symptoms TEXT, result TEXT, timestamp TEXT)"""
    )
    c.execute(
        """CREATE TABLE IF NOT EXISTS reports
                 (id INTEGER PRIMARY KEY, filename TEXT, extracted_text TEXT, timestamp TEXT)"""
    )
    conn.commit()
    conn.close()


init_db()

TRUSTED_SOURCES = [
    {"name": "WHO", "url": "https://www.who.int"},
    {"name": "ICMR", "url": "https://www.icmr.gov.in"},
    {"name": "CDC", "url": "https://www.cdc.gov"},
    {"name": "AIIMS", "url": "https://www.aiims.edu"},
    {"name": "NIH", "url": "https://www.nih.gov"},
    {"name": "Mayo Clinic", "url": "https://www.mayoclinic.org"},
]

MEDICAL_SYSTEM_PROMPT = """You are HealthEcho, an expert AI medical assistant trained on:
WHO, ICMR, CDC, AIIMS, NIH, Mayo Clinic guidelines.
Focus: Diseases prevalent in India - Diabetes, TB, Dengue, Malaria, Typhoid, Thyroid, PCOS, Anemia, Hypertension, Asthma.

STRICT RULES:
1. Never fabricate medical information
2. Always cite specific trusted sources
3. Include realistic confidence levels
4. Always recommend professional consultation
5. Flag emergencies clearly
6. Return ONLY valid JSON

Return EXACTLY this JSON:
{
  "predicted_conditions": [{"name": "...", "confidence": 75, "sources": ["WHO", "ICMR"], "reason": "...", "clinical_explanation": "..."}],
  "risk_level": "Low|Moderate|High",
  "diet_recommendations": ["..."],
  "lifestyle_changes": ["..."],
  "recommended_tests": ["..."],
  "doctor_specialist": "...",
  "emergency": false,
  "disclaimer": "This system provides informational insights only. Please consult a qualified healthcare professional."
}"""


class SymptomRequest(BaseModel):
    symptoms: str
    user_id: Optional[str] = None
    age: Optional[int] = None
    gender: Optional[str] = None


def run_ollama(prompt: str, model: str = OLLAMA_MODEL) -> str:
    try:
        result = subprocess.run(
            ["ollama", "run", model],
            input=MEDICAL_SYSTEM_PROMPT + "\n\nPatient symptoms: " + prompt,
            text=True,
            capture_output=True,
            timeout=30,
        )
        return result.stdout.strip()
    except Exception:
        return ""


def parse_json_response(text: str) -> Optional[dict]:
    try:
        cleaned = re.sub(r"```json\n?|\n?```", "", text).strip()
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start != -1 and end != -1:
            return json.loads(cleaned[start : end + 1])
    except Exception:
        pass
    return None


def fallback_response() -> dict:
    return {
        "predicted_conditions": [
            {
                "name": "General Health Observation",
                "confidence": 50,
                "sources": ["WHO"],
                "reason": "Unable to process symptoms with AI - please try again",
                "clinical_explanation": "Please describe your symptoms in more detail.",
            }
        ],
        "risk_level": "Low",
        "diet_recommendations": [
            "Stay hydrated - 8-10 glasses of water daily",
            "Eat balanced, nutritious meals",
        ],
        "lifestyle_changes": ["Get adequate rest", "Monitor your symptoms"],
        "recommended_tests": ["Basic Blood Count (CBC)", "Blood Glucose"],
        "doctor_specialist": "General Physician",
        "emergency": False,
        "disclaimer": "This system provides informational insights only. Please consult a qualified healthcare professional.",
    }


@app.get("/health")
def health_check():
    try:
        response = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=2)
        ollama_status = "online" if response.ok else "offline"
    except Exception:
        ollama_status = "offline"
    return {
        "status": "running",
        "ollama": ollama_status,
        "version": "5.0",
        "sources": TRUSTED_SOURCES,
    }


@app.post("/predict")
def predict_disease(data: SymptomRequest):
    context = data.symptoms
    if data.age:
        context += f" (Patient age: {data.age})"
    if data.gender:
        context += f" (Gender: {data.gender})"

    raw_response = run_ollama(context, OLLAMA_MODEL)
    result = parse_json_response(raw_response) if raw_response else None

    if not result:
        result = fallback_response()

    source_links = {source["name"]: source["url"] for source in TRUSTED_SOURCES}
    for condition in result.get("predicted_conditions", []):
        condition["source_links"] = source_links

    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute(
            "INSERT INTO consultations (symptoms, result, timestamp) VALUES (?,?,?)",
            (data.symptoms, json.dumps(result), datetime.now().isoformat()),
        )
        conn.commit()
        conn.close()
    except Exception:
        pass

    return result


@app.post("/upload")
async def upload_report(file: UploadFile = File(...)):
    contents = await file.read()
    temp_path = BASE_DIR / f"temp_{file.filename}"
    temp_path.write_bytes(contents)
    try:
        if file.filename.endswith(".pdf"):
            try:
                from pdf2image import convert_from_path

                images = convert_from_path(str(temp_path))
                text = "\n".join([pytesseract.image_to_string(img) for img in images])
            except Exception:
                text = "PDF processing requires pdf2image: pip install pdf2image"
        else:
            image = Image.open(temp_path)
            text = pytesseract.image_to_string(image)

        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute(
            "INSERT INTO reports (filename, extracted_text, timestamp) VALUES (?,?,?)",
            (file.filename, text, datetime.now().isoformat()),
        )
        conn.commit()
        conn.close()

        temp_path.unlink(missing_ok=True)
        return {"extracted_text": text, "filename": file.filename, "status": "success"}
    except Exception as exc:
        temp_path.unlink(missing_ok=True)
        return {"extracted_text": "", "error": str(exc), "status": "error"}


@app.get("/history")
def get_history():
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT id, symptoms, result, timestamp FROM consultations ORDER BY id DESC LIMIT 50")
        rows = c.fetchall()
        conn.close()
        return [
            {"id": row[0], "symptoms": row[1], "result": json.loads(row[2]), "timestamp": row[3]}
            for row in rows
        ]
    except Exception:
        return []


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host=HOST, port=PORT)

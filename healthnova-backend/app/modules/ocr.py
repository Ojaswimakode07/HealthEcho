from __future__ import annotations

from io import BytesIO
import re

import pytesseract
from PIL import Image, ImageFilter, ImageOps
from pytesseract import Output


def _score_text(text: str) -> tuple[int, int]:
    digits = sum(char.isdigit() for char in text)
    decimals = len(re.findall(r"\d+\.\d+", text))
    keywords = sum(
        text.lower().count(word)
        for word in (
            "hemoglobin",
            "hematocrit",
            "wbc",
            "rbc",
            "platelet",
            "plt",
            "mcv",
            "mch",
            "mchc",
            "rdw",
            "mpv",
            "neut",
            "lymph",
            "mono",
            "eos",
            "baso",
            "glucose",
            "cholesterol",
            "hba1c",
            "tsh",
            "creatinine",
            "urea",
            "bun",
            "bilirubin",
            "alt",
            "ast",
            "vitamin",
            "iron",
        )
    )
    return (digits + decimals * 3 + keywords * 10, len(text.strip()))


def _normalize_ocr_text(text: str) -> str:
    cleaned = text.replace("|", "1").replace("O.", "0.").replace("o.", "0.")
    cleaned = cleaned.replace("mg/d!", "mg/dL").replace("uIU/m1", "uIU/mL")
    cleaned = cleaned.replace("Vitarnin", "Vitamin").replace("Hernoglobin", "Hemoglobin")
    cleaned = cleaned.replace("Plateleis", "Platelets").replace("Creatinlne", "Creatinine")
    cleaned = cleaned.replace("Bilirubin,", "Bilirubin")
    cleaned = re.sub(r"\bW8C\b", "WBC", cleaned, flags=re.I)
    cleaned = re.sub(r"\bR8C\b", "RBC", cleaned, flags=re.I)
    cleaned = re.sub(r"\bPL[1I]?\b", "PLT", cleaned, flags=re.I)
    cleaned = re.sub(r"\bP1atelets?\b", "Platelets", cleaned, flags=re.I)
    cleaned = re.sub(r"\bHaemogiobin\b", "Haemoglobin", cleaned, flags=re.I)
    cleaned = re.sub(r"\bMCVV\b", "MCV", cleaned, flags=re.I)
    cleaned = re.sub(r"\bMC HC\b", "MCHC", cleaned, flags=re.I)
    cleaned = re.sub(r"(?<=\d),(?=\d)", ".", cleaned)
    cleaned = re.sub(r"(?<=\d)\s+[.,]\s*(?=\d)", ".", cleaned)
    cleaned = re.sub(r"(?<=\d)\s+(?=\d{1,2}\b)", ".", cleaned)

    normalized_lines: list[str] = []
    for raw_line in cleaned.splitlines():
        line = " ".join(raw_line.split())
        if not line:
            continue

        chars = list(line)
        for index, char in enumerate(chars):
            prev_char = chars[index - 1] if index > 0 else ""
            next_char = chars[index + 1] if index < len(chars) - 1 else ""

            if char in {"O", "o"} and (
                prev_char.isdigit() or next_char.isdigit() or prev_char == "." or next_char == "."
            ):
                chars[index] = "0"

            if char in {"I", "l"} and prev_char.isdigit() and next_char.isdigit():
                chars[index] = "1"

        normalized_lines.append("".join(chars))

    return "\n".join(normalized_lines)


def _normalize_token(token: str) -> str:
    token = token.strip()
    if not token:
        return ""
    token = token.replace("|", "1").replace("O", "0").replace("o", "0")
    token = re.sub(r"(?<=\d),(?=\d)", ".", token)
    token = re.sub(r"(?<=\d)\s+(?=\d)", ".", token)
    return token


def _ocr_text_from_boxes(image: Image.Image, config: str) -> str:
    data = pytesseract.image_to_data(image, config=config, output_type=Output.DICT)
    grouped: dict[tuple[int, int, int], list[tuple[int, str]]] = {}

    total = len(data.get("text", []))
    for index in range(total):
        raw_text = str(data["text"][index] or "").strip()
        if not raw_text:
            continue

        confidence_raw = str(data.get("conf", ["-1"] * total)[index]).strip()
        try:
            confidence = float(confidence_raw)
        except ValueError:
            confidence = -1.0
        if confidence < 25:
            continue

        token = _normalize_token(raw_text)
        if not token:
            continue

        key = (
            int(data.get("block_num", [0] * total)[index]),
            int(data.get("par_num", [0] * total)[index]),
            int(data.get("line_num", [0] * total)[index]),
        )
        left = int(data.get("left", [0] * total)[index])
        grouped.setdefault(key, []).append((left, token))

    lines: list[str] = []
    for key in sorted(grouped):
        ordered_tokens = [token for _, token in sorted(grouped[key], key=lambda item: item[0])]
        line = " ".join(ordered_tokens).strip()
        if line:
            lines.append(line)

    return "\n".join(lines)


def _prepare_variants(image: Image.Image) -> list[Image.Image]:
    base = ImageOps.exif_transpose(image).convert("L")
    enlarged = base.resize((max(1, base.width * 2), max(1, base.height * 2)))
    autocontrast = ImageOps.autocontrast(enlarged)
    sharpened = autocontrast.filter(ImageFilter.SHARPEN)
    median = autocontrast.filter(ImageFilter.MedianFilter(size=3))
    threshold = autocontrast.point(lambda pixel: 255 if pixel > 170 else 0)
    return [autocontrast, sharpened, median, threshold]


def _ocr_configs() -> list[str]:
    return [
        "--oem 3 --psm 6",
        "--oem 3 --psm 4",
        "--oem 3 --psm 11",
    ]


def image_bytes_to_text(image_bytes: bytes) -> str:
    image = Image.open(BytesIO(image_bytes))
    candidates: list[str] = []

    for variant in _prepare_variants(image):
        for config in _ocr_configs():
            try:
                plain_text = pytesseract.image_to_string(variant, config=config)
                if plain_text.strip():
                    candidates.append(plain_text)
            except Exception:
                continue
            try:
                boxed_text = _ocr_text_from_boxes(variant, config)
                if boxed_text.strip():
                    candidates.append(boxed_text)
            except Exception:
                continue

    if not candidates:
        return ""

    best_text = max(candidates, key=_score_text)
    return _normalize_ocr_text(best_text)

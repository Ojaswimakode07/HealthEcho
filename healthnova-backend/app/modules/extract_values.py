from __future__ import annotations

import re

VALUE_CAPTURE = r"([0-9]+(?:\.[0-9]+)?)"
NUMBER_RE = re.compile(r"-?\d+(?:\.\d+)?")
RANGE_RE = re.compile(r"-?\d+(?:\.\d+)?\s*[-?]\s*-?\d+(?:\.\d+)?")
GENERIC_MEASURE_RE = re.compile(
    r"(?P<label>[A-Za-z][A-Za-z0-9/%() .,_+-]{1,60}?)\s*(?:[:=-]|\bis\b)?\s*(?P<value>-?\d+(?:\.\d+)?)\s*(?P<unit>[A-Za-z/%^0-9._/-]{0,20})",
    re.IGNORECASE,
)
GENERIC_LABEL_BLACKLIST = {
    "report",
    "patient",
    "patient profile",
    "age",
    "name",
    "date",
    "time",
    "gender",
    "male",
    "female",
    "normal",
    "range",
    "reference range",
    "reference",
    "result",
    "findings",
    "impression",
    "clinical",
    "history",
    "referring doctor",
    "doctor",
    "dr",
    "male patient",
    "female patient",
    "profile",
    "department",
    "sample",
    "collected",
    "referred by",
    "bill no",
    "lab no",
}

LAB_PATTERNS: dict[str, list[str]] = {
    "Hemoglobin": [r"\bhemoglobin\b", r"\bhaemoglobin\b", r"\bhb\b", r"\bhgb\b"],
    "Hematocrit": [r"\bhematocrit\b", r"\bhaematocrit\b", r"\bhct\b", r"\bpcv\b", r"packed\s+cell\s+volume"],
    "WBC": [r"\bwbc\b", r"white\s+blood\s+cells?", r"total\s+leucocyte\s+count", r"\btlc\b"],
    "RBC": [r"\brbc\b", r"red\s+blood\s+cells?", r"\btrbc\b"],
    "Platelets": [r"\bplatelets?\b", r"\bplt\b", r"platelet\s+count"],
    "MCV": [r"\bmcv\b", r"mean\s+corpuscular\s+volume"],
    "MCH": [r"\bmch\b", r"mean\s+corpuscular\s+hemoglobin"],
    "MCHC": [r"\bmchc\b", r"mean\s+corpuscular\s+hemoglobin\s+concentration"],
    "RDW": [r"\brdw\b", r"red\s+cell\s+distribution\s+width"],
    "MPV": [r"\bmpv\b", r"mean\s+platelet\s+volume"],
    "Neutrophils": [r"(?<!abs\s)\bneut(?:rophils?)?\b(?!\s*\d)", r"\bneut\s*%"],
    "Absolute Neutrophils": [r"\babs\.?\s*neut(?:rophils?)?\b", r"\babsolute\s+neut(?:rophils?)?\b"],
    "Lymphocytes": [r"(?<!abs\s)\blymphocytes?\b", r"\bly\s*%"],
    "Absolute Lymphocytes": [r"\babs\.?\s*ly(?:mphocytes?)?\b", r"\babsolute\s+lymphocytes?\b"],
    "Monocytes": [r"(?<!abs\s)\bmonocytes?\b", r"\bmo\s*%"],
    "Absolute Monocytes": [r"\babs\.?\s*mono(?:cytes?)?\b", r"\babsolute\s+monocytes?\b"],
    "Eosinophils": [r"(?<!abs\s)\beos(?:inophils?)?\b", r"\beos\s*%"],
    "Absolute Eosinophils": [r"\babs\.?\s*eos(?:inophils?)?\b", r"\babsolute\s+eosinophils?\b"],
    "Basophils": [r"(?<!abs\s)\bbaso(?:phils?)?\b", r"\bbaso\s*%"],
    "Absolute Basophils": [r"\babs\.?\s*baso(?:phils?)?\b", r"\babsolute\s+basophils?\b"],
    "Glucose": [r"\bglucose\b", r"fasting\s+blood\s+sugar", r"\bfbs\b", r"blood\s+sugar"],
    "Cholesterol": [r"\bcholesterol\b", r"total\s+cholesterol"],
    "HbA1c": [r"\bhba1c\b", r"glyc(?:ated|osylated)\s+hemoglobin", r"\ba1c\b"],
    "TSH": [r"\btsh\b", r"thyroid\s+stimulating\s+hormone"],
    "Creatinine": [r"\bcreatinine\b"],
    "Urea": [r"\burea\b", r"blood\s+urea"],
    "BUN": [r"\bbun\b", r"blood\s+urea\s+nitrogen"],
    "Bilirubin": [r"\bbilirubin\b", r"total\s+bilirubin"],
    "ALT": [r"\balt\b", r"\bsgpt\b", r"alanine\s+aminotransferase"],
    "AST": [r"\bast\b", r"\bsgot\b", r"aspartate\s+aminotransferase"],
    "Vitamin D": [r"vitamin\s*d", r"25\s*\(?oh\)?d"],
    "Iron": [r"serum\s+iron", r"\biron\b"],
    "Sodium": [r"\bsodium\b", r"\bna\+?\b"],
    "Potassium": [r"\bpotassium\b", r"\bk\+?\b"],
    "Chloride": [r"\bchloride\b", r"\bcl-?\b"],
    "Calcium": [r"\bcalcium\b"],
    "Phosphorus": [r"\bphosph(?:orus|ate)\b"],
    "Magnesium": [r"\bmagnesium\b", r"\bmg\+\+?\b"],
    "Uric Acid": [r"\buric\s+acid\b"],
    "Albumin": [r"\balbumin\b"],
    "Globulin": [r"\bglobulin\b"],
    "Total Protein": [r"total\s+protein", r"\bproteins?\b"],
    "ALP": [r"\balp\b", r"alkaline\s+phosphatase"],
    "GGT": [r"\bggt\b", r"gamma\s+glutamyl\s+transferase"],
    "LDL": [r"\bldl\b", r"ldl\s+cholesterol", r"low\s+density\s+lipoprotein"],
    "HDL": [r"\bhdl\b", r"hdl\s+cholesterol", r"high\s+density\s+lipoprotein"],
    "Triglycerides": [r"\btriglycerides?\b", r"\btg\b"],
    "VLDL": [r"\bvldl\b", r"very\s+low\s+density\s+lipoprotein"],
    "T3": [r"\bt3\b", r"\btri[-\s]?iodothyronine\b"],
    "T4": [r"\bt4\b", r"\bthyroxine\b"],
    "Free T3": [r"free\s+t3", r"\bft3\b"],
    "Free T4": [r"free\s+t4", r"\bft4\b"],
    "Ferritin": [r"\bferritin\b"],
    "Vitamin B12": [r"vitamin\s*b12", r"\bb12\b", r"cobalamin"],
    "Folate": [r"\bfolate\b", r"folic\s+acid"],
    "CRP": [r"\bcrp\b", r"c[-\s]?reactive\s+protein"],
    "ESR": [r"\besr\b", r"erythrocyte\s+sedimentation\s+rate"],
    "Total Count": [r"\btotal\s+count\b"],
    "DLC": [r"\bdlc\b", r"differential\s+leucocyte\s+count", r"differential\s+leukocyte\s+count"],
    "PCV": [r"\bpcv\b", r"packed\s+cell\s+volume"],
    "Total Bilirubin": [r"\btotal\s+bilirubin\b"],
    "Direct Bilirubin": [r"\bdirect\s+bilirubin\b"],
    "Indirect Bilirubin": [r"\bindirect\s+bilirubin\b"],
    "Total Cholesterol": [r"\btotal\s+cholesterol\b"],
}

PLAUSIBLE_RANGES: dict[str, tuple[float, float]] = {
    "Hemoglobin": (2.0, 25.0),
    "Hematocrit": (5.0, 80.0),
    "WBC": (0.5, 500000.0),
    "RBC": (0.5, 12.0),
    "Platelets": (5.0, 2000000.0),
    "MCV": (30.0, 150.0),
    "MCH": (10.0, 60.0),
    "MCHC": (10.0, 45.0),
    "RDW": (5.0, 40.0),
    "MPV": (3.0, 25.0),
    "Neutrophils": (0.0, 100.0),
    "Absolute Neutrophils": (0.0, 100000.0),
    "Lymphocytes": (0.0, 100.0),
    "Absolute Lymphocytes": (0.0, 100000.0),
    "Monocytes": (0.0, 100.0),
    "Absolute Monocytes": (0.0, 100000.0),
    "Eosinophils": (0.0, 100.0),
    "Absolute Eosinophils": (0.0, 100000.0),
    "Basophils": (0.0, 100.0),
    "Absolute Basophils": (0.0, 100000.0),
    "Glucose": (10.0, 1000.0),
    "Cholesterol": (20.0, 1000.0),
    "HbA1c": (2.0, 20.0),
    "TSH": (0.001, 200.0),
    "Creatinine": (0.1, 25.0),
    "Urea": (1.0, 500.0),
    "BUN": (1.0, 300.0),
    "Bilirubin": (0.01, 100.0),
    "ALT": (1.0, 5000.0),
    "AST": (1.0, 5000.0),
    "Vitamin D": (1.0, 500.0),
    "Iron": (1.0, 1000.0),
    "Sodium": (90.0, 200.0),
    "Potassium": (1.0, 10.0),
    "Chloride": (50.0, 200.0),
    "Calcium": (1.0, 20.0),
    "Phosphorus": (0.1, 20.0),
    "Magnesium": (0.1, 10.0),
    "Uric Acid": (0.1, 30.0),
    "Albumin": (0.1, 10.0),
    "Globulin": (0.1, 10.0),
    "Total Protein": (0.1, 20.0),
    "ALP": (1.0, 5000.0),
    "GGT": (1.0, 5000.0),
    "LDL": (1.0, 1000.0),
    "HDL": (1.0, 200.0),
    "Triglycerides": (1.0, 5000.0),
    "VLDL": (1.0, 300.0),
    "T3": (0.01, 1000.0),
    "T4": (0.01, 100.0),
    "Free T3": (0.01, 100.0),
    "Free T4": (0.01, 100.0),
    "Ferritin": (0.1, 10000.0),
    "Vitamin B12": (1.0, 10000.0),
    "Folate": (0.1, 100.0),
    "CRP": (0.0, 1000.0),
    "ESR": (0.0, 200.0),
    "Total Count": (0.0, 1000000.0),
    "DLC": (0.0, 100.0),
    "PCV": (5.0, 80.0),
    "Total Bilirubin": (0.01, 100.0),
    "Direct Bilirubin": (0.01, 100.0),
    "Indirect Bilirubin": (0.01, 100.0),
    "Total Cholesterol": (20.0, 1000.0),
}

IMPORTANT_MEASURE_HINTS = {
    "hemoglobin",
    "haemoglobin",
    "hb",
    "hct",
    "pcv",
    "wbc",
    "rbc",
    "platelet",
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
    "sugar",
    "hba1c",
    "creatinine",
    "urea",
    "bun",
    "bilirubin",
    "alt",
    "ast",
    "alp",
    "ggt",
    "tsh",
    "t3",
    "t4",
    "ft3",
    "ft4",
    "cholesterol",
    "ldl",
    "hdl",
    "triglyceride",
    "vldl",
    "sodium",
    "potassium",
    "chloride",
    "calcium",
    "phosph",
    "magnesium",
    "ferritin",
    "iron",
    "vitamin",
    "crp",
    "esr",
}


def _normalize_text(raw_text: str | None) -> tuple[str, list[str]]:
    text = str(raw_text or "")
    text = text.replace("Hernoglobin", "Hemoglobin")
    text = re.sub(r"[|]", " ", text)
    text = re.sub(r"[??]", "-", text)
    text = re.sub(r"\s+", " ", text)
    lines = [line.strip() for line in str(raw_text or "").replace("\r", "\n").split("\n")]
    lines = [re.sub(r"\s+", " ", line.replace("Hernoglobin", "Hemoglobin")).strip() for line in lines if line.strip()]
    return text.strip(), lines


def _extract_with_alias(text: str, alias: str, marker: str | None = None) -> float | None:
    pattern = rf"{alias}\s*(?:[:=\-]|\bis\b)?\s*{VALUE_CAPTURE}\b"
    match = re.search(pattern, text, flags=re.IGNORECASE)
    if not match:
        return None
    try:
        value = float(match.group(1))
        if marker:
            context_start = max(0, match.start() - 20)
            context_end = min(len(text), match.end() + 40)
            value = _normalize_marker_value(marker, text[context_start:context_end], value)
            if not _is_plausible_value(marker, value):
                return None
        return value
    except ValueError:
        return None


def _normalize_marker_value(marker: str, line: str, value: float) -> float:
    normalized = line.lower()
    marker_text = marker.lower()

    if marker_text == "platelets":
        if re.search(r"\b(lakh|lakhs|lac|lacs)\b", normalized):
            return value * 100000
        if re.search(r"\b(million|millions)\b", normalized):
            return value * 1000000

    return value


def _looks_like_reference_value(value: float, line: str) -> bool:
    normalized = line.lower()
    if "normal range" not in normalized and "reference range" not in normalized and "ref range" not in normalized:
        return False
    return normalized.rfind(str(value)) > normalized.find("range")


def _is_plausible_value(marker: str | None, value: float) -> bool:
    if marker is None or value is None:
        return True
    lower, upper = PLAUSIBLE_RANGES.get(marker, (float("-inf"), float("inf")))
    return lower <= value <= upper


def _score_candidate(marker: str | None, value: float, raw_value: str, position: int, alias_end: int, line: str) -> float:
    score = 0.0
    distance = max(0, position - alias_end)
    score -= min(distance, 120) / 20.0

    normalized_line = line.lower()
    has_decimal = "." in raw_value

    if position >= alias_end:
        score += 2.5
    if value == 0:
        score -= 8.0

    if marker == "RBC":
        if 2.0 <= value <= 8.5:
            score += 8.0
        if has_decimal:
            score += 2.0
        if value >= 100:
            score -= 10.0
    elif marker == "WBC":
        if 1000 <= value <= 20000:
            score += 10.0
        elif 1 <= value <= 20 and has_decimal:
            score += 4.0
        if has_decimal:
            score += 1.0
    elif marker == "Platelets":
        if 100000 <= value <= 700000:
            score += 10.0
        elif 100 <= value <= 700:
            score += 6.0
        if re.search(r"\b(lakh|lakhs|lac|lacs|million|millions|x10\^3|x10\^5)\b", normalized_line):
            score += 2.0
    elif marker == "Hemoglobin":
        if 6.0 <= value <= 20.0:
            score += 6.0
        if has_decimal:
            score += 1.0
    elif marker == "Hematocrit":
        if 15.0 <= value <= 70.0:
            score += 5.0
    elif marker in {"MCV", "MCH", "MCHC", "RDW", "MPV"}:
        score += 4.0

    if re.search(r"\b(range|reference|normal)\b", normalized_line[position:]):
        score -= 2.0

    return score


def _value_from_line(line: str, alias: str, marker: str | None = None) -> float | None:
    match = re.search(alias, line, flags=re.IGNORECASE)
    if not match:
        return None

    alias_end = match.end()
    range_spans = [(item.start(), item.end()) for item in RANGE_RE.finditer(line)]
    candidates: list[tuple[int, float, str]] = []

    for item in NUMBER_RE.finditer(line):
        start = item.start()
        if any(range_start <= start < range_end for range_start, range_end in range_spans):
            continue
        try:
            value = float(item.group(0))
        except ValueError:
            continue
        if _looks_like_reference_value(value, line):
            continue
        if marker:
            value = _normalize_marker_value(marker, line, value)
            if not _is_plausible_value(marker, value):
                continue
        candidates.append((start, value, item.group(0)))

    if not candidates:
        return None

    ranked = sorted(
        candidates,
        key=lambda item: _score_candidate(marker, item[1], item[2], item[0], alias_end, line),
        reverse=True,
    )
    return ranked[0][1]


def _extract_from_table_row(line: str, aliases: list[str], marker: str) -> float | None:
    for alias in aliases:
        value = _value_from_line(line, alias, marker=marker)
        if value is not None:
            return value
    return None


def _clean_generic_label(label: str) -> str:
    cleaned = re.sub(r"[_]+", " ", str(label or "")).strip(" :-,._")
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    if not cleaned:
        return ""
    cleaned = re.sub(r"\b(test|value|level|count)\b$", "", cleaned, flags=re.IGNORECASE).strip(" :-,._")
    return cleaned.title()


def _is_generic_label_valid(label: str) -> bool:
    normalized = str(label or "").strip().lower()
    if not normalized or normalized in GENERIC_LABEL_BLACKLIST:
        return False
    if len(normalized) < 2 or len(normalized) > 60:
        return False
    if re.search(r"\b(reference|normal)\b", normalized):
        return False
    if re.search(r"\b(dr|doctor|patient|profile|name|referring|hospital|lab|collected|sample|gender|male|female)\b", normalized):
        return False
    if re.search(r"\b[a-z]\b$", normalized):
        return False
    return bool(re.search(r"[a-z]", normalized))


def _looks_clinically_important(label: str) -> bool:
    normalized = str(label or "").strip().lower()
    return any(hint in normalized for hint in IMPORTANT_MEASURE_HINTS)


def _canonicalize_generic_label(label: str, known_keys: set[str]) -> str:
    cleaned = _clean_generic_label(label)
    if not cleaned:
        return ""

    normalized_cleaned = cleaned.lower()
    for key in known_keys:
        if normalized_cleaned == key.lower():
            return key

    alias_lookup = {
        "total leucocyte count": "WBC",
        "total leukocyte count": "WBC",
        "white blood cell count": "WBC",
        "rbc count": "RBC",
        "total rbc count": "RBC",
        "platelet count": "Platelets",
        "platelet": "Platelets",
        "serum sodium": "Sodium",
        "serum potassium": "Potassium",
        "serum chloride": "Chloride",
        "serum calcium": "Calcium",
        "serum uric acid": "Uric Acid",
        "serum creatinine": "Creatinine",
        "blood urea nitrogen": "BUN",
        "blood urea": "Urea",
        "total bilirubin": "Bilirubin",
        "sgpt": "ALT",
        "sgot": "AST",
        "alkaline phosphatase": "ALP",
        "ldl cholesterol": "LDL",
        "hdl cholesterol": "HDL",
        "mean platelet volume": "MPV",
        "red cell distribution width": "RDW",
    }
    return alias_lookup.get(normalized_cleaned, cleaned)


def _extract_table_like_measure(line: str) -> tuple[str, str | float] | None:
    compact = re.sub(r"\s+", " ", str(line or "")).strip()
    if not compact:
        return None

    match = re.match(
        r"^(?P<label>[A-Za-z][A-Za-z0-9/%() .,+_-]{1,60}?)\s+(?P<value>-?\d+(?:\.\d+)?)\s*(?P<unit>[A-Za-z/%^0-9._/-]{0,25})?(?:\s+(?P<rest>.*))?$",
        compact,
        flags=re.IGNORECASE,
    )
    if not match:
        return None

    label = _clean_generic_label(match.group("label"))
    if not _is_generic_label_valid(label):
        return None

    value_text = match.group("value")
    unit_text = (match.group("unit") or "").strip()
    rest = safe_rest = (match.group("rest") or "").strip()
    if rest and not RANGE_RE.search(rest) and len(rest.split()) > 3:
        return None

    if unit_text:
        return label, f"{value_text} {unit_text}".strip()
    try:
        return label, float(value_text)
    except ValueError:
        return label, value_text


def _extract_generic_measures(raw_text: str | None, known_keys: set[str]) -> dict[str, str | float]:
    _, lines = _normalize_text(raw_text)
    extracted: dict[str, str | float] = {}
    known_keys_normalized = {key.lower() for key in known_keys}

    for line in lines:
        lowered = line.lower()
        if "reference range" in lowered or "normal range" in lowered:
            continue

        table_like = _extract_table_like_measure(line)
        if table_like:
            raw_label, raw_value = table_like
            label = _canonicalize_generic_label(raw_label, known_keys)
            normalized_label = label.lower()
            if (
                _is_generic_label_valid(label)
                and _looks_clinically_important(label)
                and normalized_label not in known_keys_normalized
                and normalized_label not in {key.lower() for key in extracted}
            ):
                extracted[label] = raw_value

        for match in GENERIC_MEASURE_RE.finditer(line):
            label = _canonicalize_generic_label(match.group("label"), known_keys)
            normalized_label = label.lower()
            if not _is_generic_label_valid(label):
                continue
            if normalized_label in known_keys_normalized:
                continue
            if normalized_label in {key.lower() for key in extracted}:
                continue
            if not _looks_clinically_important(label):
                continue
            if any(normalized_label.endswith(existing.lower()) or existing.lower().endswith(normalized_label) for existing in known_keys):
                continue

            value_text = match.group("value")
            unit_text = (match.group("unit") or "").strip()
            if not value_text:
                continue

            if unit_text:
                extracted[label] = f"{value_text} {unit_text}".strip()
            else:
                try:
                    extracted[label] = float(value_text)
                except ValueError:
                    extracted[label] = value_text

    return extracted


def extract_lab_values(raw_text: str | None) -> dict[str, float | str | None]:
    cleaned, lines = _normalize_text(raw_text)
    extracted: dict[str, float | str | None] = {}

    for lab, aliases in LAB_PATTERNS.items():
        value = None
        for line in lines:
            value = _extract_from_table_row(line, aliases, lab)
            if value is not None:
                break

        if value is None:
            for alias in aliases:
                value = _extract_with_alias(cleaned, alias, marker=lab)
                if value is not None:
                    break

        extracted[lab] = value

    extracted.update(_extract_generic_measures(raw_text, set(extracted.keys())))
    return extracted

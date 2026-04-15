from __future__ import annotations

import re
from html import unescape
from urllib.parse import parse_qs, quote_plus, unquote, urlparse

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router = APIRouter()

USER_AGENT = "HealthNova/1.0 (+http://127.0.0.1)"

SPECIALTY_GROUPS: dict[str, tuple[str, ...]] = {
    "hematology": ("hematologist", "haematologist", "hematology"),
    "cardiology": ("cardiologist", "cardiology", "heart specialist"),
    "neurology": ("neurologist", "neurology", "brain specialist"),
    "orthopedics": ("orthopedist", "orthopaedist", "orthopedic", "orthopaedic", "bone specialist"),
    "gynecology": ("gynecologist", "gynaecologist", "gynecology", "gynaecology", "obgyn", "ob-gyn"),
    "dermatology": ("dermatologist", "dermatology", "skin specialist"),
    "nephrology": ("nephrologist", "nephrology", "kidney specialist"),
    "gastroenterology": ("gastroenterologist", "gastroenterology", "gi specialist"),
    "pulmonology": ("pulmonologist", "pulmonology", "lung specialist", "chest specialist"),
    "ent": ("ent", "otolaryngologist", "ear nose throat"),
    "endocrinology": ("endocrinologist", "endocrinology", "hormone specialist"),
    "oncology": ("oncologist", "oncology", "cancer specialist"),
    "urology": ("urologist", "urology"),
    "psychiatry": ("psychiatrist", "psychiatry", "mental health specialist"),
    "general": ("general physician", "general doctor", "physician", "general medicine", "internal medicine"),
}


class NearbyDoctorsRequest(BaseModel):
    latitude: float
    longitude: float
    specialty: str = Field(default="General Physician")
    limit: int = Field(default=4, ge=1, le=4)


def _clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", unescape(value or "")).strip()


def _resolve_result_url(raw_url: str) -> str:
    url = _clean_text(raw_url)
    if not url:
        return ""
    if url.startswith("//"):
        return f"https:{url}"
    if url.startswith("/"):
        parsed = urlparse(url)
        params = parse_qs(parsed.query)
        redirect = params.get("uddg", [""])[0]
        if redirect:
            return unquote(redirect)
        return f"https://duckduckgo.com{url}"
    return url


def _extract_city_name(reverse_data: dict) -> str:
    address = reverse_data.get("address") or {}
    for key in ("city", "town", "suburb", "county", "state_district", "state"):
        value = _clean_text(address.get(key, ""))
        if value:
            return value
    return _clean_text(reverse_data.get("display_name", "")).split(",")[0].strip()


def _get_specialty_keywords(specialty: str) -> tuple[set[str], str | None]:
    normalized = _clean_text(specialty).lower()
    if not normalized:
        return {"doctor", "clinic", "hospital"}, "general"

    for group, keywords in SPECIALTY_GROUPS.items():
        if any(keyword in normalized for keyword in keywords):
            return set(keywords), group

    return {normalized, f"{normalized} doctor"}, None


def _matches_specialty(combined: str, specialty: str) -> bool:
    keywords, matched_group = _get_specialty_keywords(specialty)
    normalized = combined.lower()

    if matched_group == "general":
        return True

    if any(keyword in normalized for keyword in keywords):
        return True

    if matched_group is None:
        return specialty.lower() in normalized

    return False


def _has_conflicting_specialty(combined: str, specialty: str) -> bool:
    _, matched_group = _get_specialty_keywords(specialty)
    if matched_group in {None, "general"}:
        return False

    normalized = combined.lower()
    for group, keywords in SPECIALTY_GROUPS.items():
        if group in {matched_group, "general"}:
            continue
        if any(keyword in normalized for keyword in keywords):
            return True
    return False


def _parse_duckduckgo_results(html: str, specialty: str, city: str, limit: int) -> list[dict[str, str]]:
    cards: list[dict[str, str]] = []
    seen: set[str] = set()

    pattern = re.compile(
        r'<a[^>]+class="[^"]*result__a[^"]*"[^>]+href="(?P<href>[^"]+)"[^>]*>(?P<title>.*?)</a>(?P<rest>.*?)(?=<a[^>]+class="[^"]*result__a|$)',
        re.I | re.S,
    )

    for match in pattern.finditer(html):
        url = _resolve_result_url(match.group("href"))
        title = _clean_text(re.sub(r"<.*?>", " ", match.group("title")))
        rest = match.group("rest")

        snippet_match = re.search(r'class="[^"]*(?:result__snippet|result__extras__url)[^"]*"[^>]*>(.*?)</', rest, re.I | re.S)
        snippet = _clean_text(re.sub(r"<.*?>", " ", snippet_match.group(1))) if snippet_match else ""
        combined = f"{title} {snippet}".lower()

        if not url or not title:
            continue
        if url in seen:
            continue
        if not re.search(r"doctor|clinic|hospital|practo|justdial|lybrate|care|apollo|medicover", combined):
            continue
        if not _matches_specialty(combined, specialty):
            continue
        if _has_conflicting_specialty(combined, specialty):
            continue

        seen.add(url)
        source = urlparse(url).netloc.replace("www.", "")
        maps_query = quote_plus(f"{title} {specialty} {city}")

        cards.append(
            {
                "name": title[:140],
                "specialty": specialty,
                "area": city,
                "snippet": snippet[:220] or f"Live result for {specialty} near {city}.",
                "source": source,
                "url": url,
                "maps_url": f"https://www.google.com/maps/search/?api=1&query={maps_query}",
            }
        )

        if len(cards) >= limit:
            break

    return cards


@router.post("/doctors/nearby")
async def nearby_doctors(body: NearbyDoctorsRequest) -> dict:
    headers = {"User-Agent": USER_AGENT, "Accept-Language": "en-IN,en;q=0.9"}

    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=20) as client:
            reverse = await client.get(
                "https://nominatim.openstreetmap.org/reverse",
                params={
                    "lat": body.latitude,
                    "lon": body.longitude,
                    "format": "jsonv2",
                    "zoom": 13,
                    "addressdetails": 1,
                },
                headers=headers,
            )
            reverse.raise_for_status()
            reverse_data = reverse.json()
            city = _extract_city_name(reverse_data) or "your area"

            query = f"{body.specialty} doctor in {city}"
            search = await client.get(
                "https://html.duckduckgo.com/html/",
                params={"q": query},
                headers=headers,
            )
            search.raise_for_status()
    except httpx.HTTPError as error:
        raise HTTPException(status_code=502, detail=f"Doctor search failed: {error}") from error

    doctors = _parse_duckduckgo_results(search.text, body.specialty, city, body.limit)
    maps_query = quote_plus(f"{body.specialty} near {city}")

    return {
        "specialty": body.specialty,
        "area": city,
        "doctors": doctors,
        "fallback_links": [
            {
                "label": "Open in Google Maps",
                "url": f"https://www.google.com/maps/search/?api=1&query={maps_query}",
            },
            {
                "label": "Open Google Search",
                "url": f"https://www.google.com/search?q={maps_query}",
            },
        ],
    }

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Header, HTTPException

from app.modules.auth_store import MEMORY_STORE
from app.routes.auth import load_store, save_store

router = APIRouter(tags=["workspace"])

HISTORY_WINDOW = timedelta(hours=24)


def _now_utc() -> datetime:
    return datetime.now(UTC)


def _parse_timestamp(value: str | None) -> datetime | None:
    raw = str(value or "").strip()
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw)
    except ValueError:
        return None


def _is_recent(value: str | None) -> bool:
    timestamp = _parse_timestamp(value)
    return bool(timestamp and _now_utc() - timestamp <= HISTORY_WINDOW)


def _normalize_reports(items: list | None) -> list[dict]:
    reports = []
    for item in items or []:
        if not isinstance(item, dict):
            continue
        created_at = str(item.get("createdAt") or item.get("created_at") or "").strip() or _now_utc().isoformat()
        if not _is_recent(created_at):
            continue
        normalized = {**item, "createdAt": created_at}
        reports.append(normalized)
    reports.sort(key=lambda entry: entry.get("createdAt", ""), reverse=True)
    return reports[:20]


def _normalize_chat_history(items: list | None) -> list[dict]:
    history = []
    for item in items or []:
        if not isinstance(item, dict):
            continue
        role = str(item.get("role") or "").strip()
        content = str(item.get("content") or "").strip()
        created_at = str(item.get("createdAt") or "").strip() or _now_utc().isoformat()
        if role not in {"user", "assistant"} or not content or not _is_recent(created_at):
            continue
        history.append(
            {
                "id": str(item.get("id") or "").strip() or f"{role}-{created_at}",
                "role": role,
                "content": content,
                "createdAt": created_at,
            }
        )
    history.sort(key=lambda entry: entry.get("createdAt", ""))
    return history[-60:]


def _normalize_chat_tabs(items: list | None) -> list[dict]:
    tabs = []
    for index, item in enumerate(items or []):
        if not isinstance(item, dict):
            continue
        messages = _normalize_chat_history(item.get("messages") if isinstance(item.get("messages"), list) else [])
        updated_at = str(item.get("updatedAt") or item.get("createdAt") or "").strip() or (
            messages[-1]["createdAt"] if messages else _now_utc().isoformat()
        )
        if not messages and not _is_recent(updated_at):
            continue
        if messages and not _is_recent(updated_at):
            updated_at = messages[-1]["createdAt"]
        tabs.append(
            {
                "id": str(item.get("id") or "").strip() or f"tab-{index + 1}",
                "label": str(item.get("label") or "").strip() or f"Chat {index + 1}",
                "createdAt": str(item.get("createdAt") or updated_at).strip() or updated_at,
                "updatedAt": updated_at,
                "messages": messages,
            }
        )
    tabs.sort(key=lambda entry: entry.get("updatedAt", ""), reverse=True)
    return tabs[:8]


def _flatten_chat_tabs(tabs: list[dict]) -> list[dict]:
    flattened = []
    for tab in tabs:
        flattened.extend(tab.get("messages", []))
    flattened.sort(key=lambda entry: entry.get("createdAt", ""))
    unique: list[dict] = []
    seen: set[tuple[str, str, str]] = set()
    for item in flattened:
        key = (item.get("role", ""), item.get("content", ""), item.get("createdAt", ""))
        if key in seen:
            continue
        seen.add(key)
        unique.append(item)
    return unique[-60:]


def _resolve_session_email(x_session_token: str | None) -> str:
    load_store()
    token = str(x_session_token or "").strip()
    if not token:
        raise HTTPException(status_code=401, detail="Session token is required.")

    session = MEMORY_STORE.setdefault("sessions", {}).get(token)
    if not isinstance(session, dict):
        raise HTTPException(status_code=401, detail="Session expired. Please log in again.")

    expires_at = _parse_timestamp(session.get("expires_at"))
    if not expires_at or expires_at <= _now_utc():
        MEMORY_STORE["sessions"].pop(token, None)
        save_store()
        raise HTTPException(status_code=401, detail="Session expired. Please log in again.")

    email = str(session.get("email") or "").strip().lower()
    if not email:
        raise HTTPException(status_code=401, detail="Session is invalid.")
    return email


@router.get("/workspace")
def load_workspace(x_session_token: str | None = Header(None)) -> dict:
    email = _resolve_session_email(x_session_token)
    workspace = MEMORY_STORE.setdefault("workspaces", {}).setdefault(
        email,
        {"reports": [], "chatHistory": [], "chatTabs": [], "updated_at": _now_utc().isoformat()},
    )
    reports = _normalize_reports(workspace.get("reports"))
    chat_tabs = _normalize_chat_tabs(workspace.get("chatTabs"))
    chat_history = _normalize_chat_history(workspace.get("chatHistory")) if not chat_tabs else _flatten_chat_tabs(chat_tabs)
    workspace.update(
        {
            "reports": reports,
            "chatHistory": chat_history,
            "chatTabs": chat_tabs,
            "updated_at": _now_utc().isoformat(),
        }
    )
    save_store()
    return {"reports": reports, "chatHistory": chat_history, "chatTabs": chat_tabs}


@router.put("/workspace")
def save_workspace(payload: dict, x_session_token: str | None = Header(None)) -> dict:
    email = _resolve_session_email(x_session_token)
    reports = _normalize_reports(payload.get("reports") if isinstance(payload, dict) else [])
    chat_tabs = _normalize_chat_tabs(payload.get("chatTabs") if isinstance(payload, dict) else [])
    chat_history = (
        _flatten_chat_tabs(chat_tabs)
        if chat_tabs
        else _normalize_chat_history(payload.get("chatHistory") if isinstance(payload, dict) else [])
    )
    MEMORY_STORE.setdefault("workspaces", {})[email] = {
        "reports": reports,
        "chatHistory": chat_history,
        "chatTabs": chat_tabs,
        "updated_at": _now_utc().isoformat(),
    }
    save_store()
    return {"success": True, "reports": reports, "chatHistory": chat_history, "chatTabs": chat_tabs}

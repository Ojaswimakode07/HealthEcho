import json
import hashlib
import smtplib
from datetime import UTC, datetime
from datetime import timedelta
from email.message import EmailMessage
from pathlib import Path
import secrets

from fastapi import APIRouter, Header, HTTPException

from app.core.config import settings
from app.modules.firebase_admin_client import update_firebase_user_password
from app.modules.auth_store import MEMORY_STORE

router = APIRouter(prefix="/auth", tags=["auth"])
STORE_PATH = Path(__file__).resolve().parents[2] / ".tmp" / "auth_store.json"


def send_otp_email(recipient_email: str, code: str, recipient_name: str = "") -> None:
    smtp_host = str(getattr(settings, "smtp_host", "") or "").strip()
    smtp_port = int(getattr(settings, "smtp_port", 587) or 587)
    smtp_username = str(getattr(settings, "smtp_username", "") or "").strip()
    smtp_password = str(getattr(settings, "smtp_password", "") or "").strip()
    smtp_use_tls = bool(getattr(settings, "smtp_use_tls", True))
    from_email = str(getattr(settings, "otp_from_email", "") or "").strip() or smtp_username
    from_name = str(getattr(settings, "otp_from_name", "HealthNova") or "HealthNova").strip() or "HealthNova"

    if not smtp_host or not from_email or not smtp_username or not smtp_password:
        raise RuntimeError("SMTP is not configured.")

    subject = "Your HealthNova verification code"
    greeting_name = recipient_name.strip() or recipient_email.split("@")[0]
    html_body = f"""
    <html>
      <body style="font-family:Arial,sans-serif;background:#f4f8fb;padding:24px;color:#173047;">
        <div style="max-width:520px;margin:0 auto;background:#ffffff;border:1px solid #d8e5ef;border-radius:16px;padding:28px;">
          <h2 style="margin:0 0 12px;">HealthNova verification</h2>
          <p style="margin:0 0 16px;">Hello {greeting_name},</p>
          <p style="margin:0 0 18px;">Use the verification code below to continue signing in to HealthNova.</p>
          <div style="font-size:32px;font-weight:700;letter-spacing:6px;padding:16px 18px;background:#eef6fb;border-radius:12px;display:inline-block;">
            {code}
          </div>
          <p style="margin:18px 0 0;">This code expires in 10 minutes.</p>
          <p style="margin:12px 0 0;color:#5c768c;">If you did not request this code, you can ignore this email.</p>
        </div>
      </body>
    </html>
    """.strip()

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = f"{from_name} <{from_email}>"
    message["To"] = recipient_email
    message.set_content(
        f"Hello {greeting_name},\n\n"
        f"Your HealthNova verification code is: {code}\n\n"
        "This code expires in 10 minutes.\n\n"
        "If you did not request this code, you can ignore this email."
    )
    message.add_alternative(html_body, subtype="html")

    with smtplib.SMTP(smtp_host, smtp_port, timeout=30) as server:
        if smtp_use_tls:
            server.starttls()
        server.login(smtp_username, smtp_password)
        server.send_message(message)


def load_store() -> None:
    for key in ("users", "pending_otps", "sessions", "workspaces", "reset_tokens"):
        MEMORY_STORE.setdefault(key, {})
    if not STORE_PATH.exists():
        return
    try:
        with STORE_PATH.open("r", encoding="utf-8") as file:
            raw_content = file.read().strip()
        if not raw_content:
            return
        disk_store = json.loads(raw_content)
    except Exception:
        return
    for key in ("users", "pending_otps", "sessions", "workspaces", "reset_tokens"):
        MEMORY_STORE[key].update(disk_store.get(key, {}))


def save_store() -> None:
    STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with STORE_PATH.open("w", encoding="utf-8") as file:
        json.dump(MEMORY_STORE, file, indent=2)


@router.post("/sync-user")
def sync_user(payload: dict) -> dict:
    load_store()
    email = str(payload.get("email", "")).strip().lower()
    if not email:
        return {"success": False, "error": "Email is required."}

    name = str(payload.get("name", "")).strip() or email.split("@")[0]
    now = datetime.now(UTC).isoformat()
    existing = MEMORY_STORE.setdefault("users", {}).get(email, {})

    MEMORY_STORE["users"][email] = {
        "uid": existing.get("uid") or str(payload.get("uid", "")).strip() or secrets.token_hex(12),
        "email": email,
        "name": name,
        "created_at": existing.get("created_at") or now,
        "updated_at": now,
    }
    MEMORY_STORE.setdefault("workspaces", {}).setdefault(
        email,
        {"reports": [], "chatHistory": [], "chatTabs": [], "updated_at": now},
    )
    save_store()
    return {"success": True, "user": MEMORY_STORE["users"][email]}


@router.post("/check-account")
def check_account(payload: dict) -> dict:
    email = str(payload.get("email", "")).strip().lower()
    exists = bool(email and email in MEMORY_STORE.get("users", {}))
    return {"exists": exists}


def _otp_hash(code: str) -> str:
    return hashlib.sha256(code.encode("utf-8")).hexdigest()


@router.post("/request-otp")
def request_otp(req: dict):
    load_store()
    email = str(req.get("email", "")).strip().lower()
    name = str(req.get("name", "")).strip()
    purpose = str(req.get("purpose", "")).strip().lower()
    if not email:
        return {"message": "Email is required.", "expires_in_minutes": 10, "dev_code": None}

    now = datetime.now(UTC)
    code = f"{secrets.randbelow(900000) + 100000}"
    MEMORY_STORE.setdefault("pending_otps", {})[email] = {
        "code_hash": _otp_hash(code),
        "expires_at": (now + timedelta(minutes=10)).isoformat(),
        "name": name,
        "purpose": purpose,
        "dev_code": code,
    }
    save_store()
    try:
        send_otp_email(email, code, name)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to send OTP email: {exc}") from exc
    return {
        "message": f"Verification code sent to {email}.",
        "expires_in_minutes": 10,
        "dev_code": code,
    }


@router.post("/verify-otp")
def verify_otp(req: dict):
    load_store()
    email = str(req.get("email", "")).strip().lower()
    code = str(req.get("code") or req.get("otp") or "").strip()
    name = str(req.get("name", "")).strip()
    requested_purpose = str(req.get("purpose", "")).strip().lower()

    pending = MEMORY_STORE.setdefault("pending_otps", {}).get(email)
    if not email or not code or not pending:
        raise HTTPException(status_code=400, detail="Invalid or expired OTP.")

    expires_at_raw = str(pending.get("expires_at") or "").strip()
    try:
        expires_at = datetime.fromisoformat(expires_at_raw)
    except ValueError:
        expires_at = datetime.now(UTC) - timedelta(seconds=1)

    if expires_at <= datetime.now(UTC):
        MEMORY_STORE["pending_otps"].pop(email, None)
        save_store()
        raise HTTPException(status_code=400, detail="OTP expired. Request a new code.")

    if pending.get("code_hash") != _otp_hash(code):
        raise HTTPException(status_code=400, detail="Invalid OTP code.")

    purpose = str(pending.get("purpose", "") or "").strip().lower() or requested_purpose
    if purpose == "password_reset":
        reset_token = secrets.token_urlsafe(32)
        MEMORY_STORE.setdefault("reset_tokens", {})[reset_token] = {
            "email": email,
            "expires_at": (datetime.now(UTC) + timedelta(minutes=15)).isoformat(),
        }
        MEMORY_STORE["pending_otps"].pop(email, None)
        save_store()
        return {
            "message": "OTP verified successfully.",
            "email": email,
            "reset_token": reset_token,
        }

    existing = MEMORY_STORE.setdefault("users", {}).get(email, {})
    resolved_name = name or str(pending.get("name") or "").strip() or existing.get("name") or email.split("@")[0]
    now = datetime.now(UTC).isoformat()
    user = {
        "uid": existing.get("uid") or secrets.token_hex(12),
        "email": email,
        "name": resolved_name,
        "created_at": existing.get("created_at") or now,
        "updated_at": now,
    }
    MEMORY_STORE["users"][email] = user
    MEMORY_STORE.setdefault("workspaces", {}).setdefault(email, {"reports": [], "chatHistory": [], "chatTabs": [], "updated_at": now})
    token = secrets.token_urlsafe(32)
    MEMORY_STORE.setdefault("sessions", {})[token] = {
        "email": email,
        "expires_at": (datetime.now(UTC) + timedelta(hours=336)).isoformat(),
    }
    MEMORY_STORE["pending_otps"].pop(email, None)
    save_store()
    return {"token": token, "user": user}


@router.post("/reset-password")
def reset_password(req: dict):
    load_store()
    email = str(req.get("email", "")).strip().lower()
    reset_token = str(req.get("reset_token", "")).strip()
    new_password = str(req.get("new_password", "") or "").strip()

    if not email or not reset_token or not new_password:
        raise HTTPException(status_code=400, detail="Email, reset token, and new password are required.")

    if len(new_password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters long.")

    token_record = MEMORY_STORE.setdefault("reset_tokens", {}).get(reset_token)
    if not token_record:
        raise HTTPException(status_code=400, detail="Password reset session expired. Please verify OTP again.")

    if str(token_record.get("email", "")).strip().lower() != email:
        raise HTTPException(status_code=400, detail="Reset token does not match this email.")

    expires_at_raw = str(token_record.get("expires_at") or "").strip()
    try:
        expires_at = datetime.fromisoformat(expires_at_raw)
    except ValueError:
        expires_at = datetime.now(UTC) - timedelta(seconds=1)

    if expires_at <= datetime.now(UTC):
        MEMORY_STORE["reset_tokens"].pop(reset_token, None)
        save_store()
        raise HTTPException(status_code=400, detail="Password reset session expired. Please request a new OTP.")

    try:
        update_firebase_user_password(email, new_password)
    except Exception as exc:
        message = str(exc)
        if "No user record found" in message:
            raise HTTPException(status_code=404, detail="No account exists for this email.") from exc
        raise HTTPException(status_code=500, detail=f"Failed to update password: {message}") from exc

    now = datetime.now(UTC).isoformat()
    user = MEMORY_STORE.setdefault("users", {}).get(email, {})
    MEMORY_STORE["users"][email] = {
        "uid": user.get("uid") or secrets.token_hex(12),
        "email": email,
        "name": user.get("name") or email.split("@")[0],
        "created_at": user.get("created_at") or now,
        "updated_at": now,
    }
    MEMORY_STORE["reset_tokens"].pop(reset_token, None)
    save_store()
    return {"success": True, "message": "Password updated successfully."}


@router.post("/logout")
def logout(x_session_token: str | None = Header(None)):
    load_store()
    if x_session_token:
        MEMORY_STORE.setdefault("sessions", {}).pop(x_session_token, None)
        save_store()
    return {"success": True}

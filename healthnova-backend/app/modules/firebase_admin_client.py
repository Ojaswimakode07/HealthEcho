import json
import os
from pathlib import Path

import firebase_admin
from firebase_admin import auth as firebase_auth
from firebase_admin import credentials


DEFAULT_ADMIN_CREDENTIALS_PATH = Path(
    r"C:\Users\ojasw\Downloads\healthnova-14319-firebase-adminsdk-fbsvc-c15a7fb6b6.json"
)
ENV_FILE_PATH = Path(__file__).resolve().parents[2] / ".env"


def _read_env_file_value(name: str) -> str:
    if not ENV_FILE_PATH.exists():
        return ""
    try:
        for line in ENV_FILE_PATH.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or "=" not in stripped:
                continue
            key, value = stripped.split("=", 1)
            if key.strip() == name:
                return value.strip().strip('"').strip("'")
    except Exception:
        return ""
    return ""


def get_admin_credentials_path() -> Path:
    raw_path = (
        str(os.getenv("FIREBASE_ADMIN_CREDENTIALS_PATH", "")).strip()
        or _read_env_file_value("FIREBASE_ADMIN_CREDENTIALS_PATH")
    )
    if raw_path:
        return Path(raw_path)
    return DEFAULT_ADMIN_CREDENTIALS_PATH


def get_firebase_admin_app():
    existing_app = firebase_admin._apps.get("[DEFAULT]")
    if existing_app:
        return existing_app

    credentials_path = get_admin_credentials_path()
    if not credentials_path.exists():
        raise RuntimeError(f"Firebase Admin credentials file not found at {credentials_path}")

    with credentials_path.open("r", encoding="utf-8") as file:
        service_account = json.load(file)

    cred = credentials.Certificate(service_account)
    return firebase_admin.initialize_app(cred)


def update_firebase_user_password(email: str, new_password: str):
    get_firebase_admin_app()
    user = firebase_auth.get_user_by_email(email)
    return firebase_auth.update_user(user.uid, password=new_password)

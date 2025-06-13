import os
import json
from typing import Any

import firebase_admin
from firebase_admin import credentials, storage
from dotenv import load_dotenv

load_dotenv()

# 1) explicit env var wins
# 2) fallback to common default path used in docker-compose (/code/firebase-creds.json)
# 3) fallback to any json file matching *firebase*cred*.json in CWD

_explicit_path = os.getenv("FIREBASE_CREDENTIALS")

if _explicit_path and os.path.isfile(_explicit_path):
    CREDS_PATH = _explicit_path
else:
    # Default docker path
    default_path = "/code/firebase-creds.json"
    if os.path.isfile(default_path):
        CREDS_PATH = default_path
    else:
        # legacy filename in project root
        legacy_path = "onaitabu-firebase-adminsdk-fbsvc-6f0734b19c.json"
        if os.path.isfile(legacy_path):
            CREDS_PATH = legacy_path
        else:
            # try to auto-discover
            import glob

            matches = glob.glob("*firebase*cred*.json")
            CREDS_PATH = matches[0] if matches else ""

# Alternatively, credential JSON can be provided inline via env var
CREDS_INLINE = os.getenv("FIREBASE_CREDENTIALS_JSON")
BUCKET_NAME = "onaitabu.firebasestorage.app"


def _ensure_app() -> Any:
    """Initialize the Firebase app (idempotent)."""
    if firebase_admin._apps:
        return firebase_admin.get_app()

    # Choose credential source
    if CREDS_INLINE:
        try:
            info = json.loads(CREDS_INLINE)
            cred = credentials.Certificate(info)
        except json.JSONDecodeError as e:
            raise RuntimeError(
                "Environment variable FIREBASE_CREDENTIALS_JSON is not valid JSON"
            ) from e
    else:
        if not os.path.isfile(CREDS_PATH):
            raise FileNotFoundError(
                f"Firebase credentials file not found at '{CREDS_PATH}'. "
                "Set FIREBASE_CREDENTIALS or FIREBASE_CREDENTIALS_JSON env variable."
            )
        cred = credentials.Certificate(CREDS_PATH)

    firebase_admin.initialize_app(cred, {"storageBucket": BUCKET_NAME})
    return firebase_admin.get_app()


def upload_image_to_firebase(image_bytes: bytes, file_name: str) -> str:
    """Uploads image bytes to Firebase Storage and returns a publicly accessible URL.

    Args:
        image_bytes: Raw PNG/JPEG bytes.
        file_name: Desired filename inside bucket (without folder path).

    Returns:
        Public URL string.
    """

    _ensure_app()
    bucket = storage.bucket()
    # Store under a dedicated folder to keep bucket organised
    blob = bucket.blob(f"waitlist/{file_name}")
    blob.upload_from_string(image_bytes, content_type="image/png")

    # Make publicly accessible
    blob.make_public()
    return blob.public_url 
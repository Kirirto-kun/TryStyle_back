from __future__ import annotations

"""Utility helpers for interacting with Firebase Cloud Storage.

The main entry-point is :pyfunc:`upload_image_to_firebase` which uploads raw
bytes to a bucket and returns a publicly accessible URL to the object.

The module is intentionally written with *lazy* initialisation – the Firebase
Admin SDK is only initialised the first time it is needed which avoids slowing
application start-up if you never call the upload function.

Environment variables expected:

FIREBASE_STORAGE_BUCKET – name of the storage bucket, e.g. ``my-project.appspot.com``.

At least one of the following variables must be provided so that the Admin SDK
can authenticate:

* ``FIREBASE_CREDENTIALS_FILE`` – path to a service-account JSON key file.
* ``FIREBASE_CREDENTIALS_JSON`` – **contents** of a service-account JSON key
  (useful when you cannot mount a file, e.g. in serverless).
* ``GOOGLE_APPLICATION_CREDENTIALS`` – standard Google credential file env
  (handled automatically by the Admin SDK).

If none are supplied the helper will raise a ``RuntimeError`` on first use.
"""

from typing import Optional
import os
import json
import tempfile

import firebase_admin
from firebase_admin import credentials, storage
import dotenv

dotenv.load_dotenv()

# Holds the singleton Firebase app instance once initialised.
_firebase_app: Optional[firebase_admin.App] = None


def _initialise_firebase() -> firebase_admin.App:
    """Initialise Firebase Admin SDK lazily.

    The function attempts to obtain credentials from one of the supported
    environment variables described in the module docstring. It also requires
    ``FIREBASE_STORAGE_BUCKET`` to be set so that the default bucket can be
    configured.
    """

    global _firebase_app  # noqa: PLW0603 – module-level singleton is OK here.

    if _firebase_app is not None:
        return _firebase_app

    bucket_name = os.getenv("FIREBASE_STORAGE_BUCKET")
    if not bucket_name:
        raise RuntimeError(
            "Missing FIREBASE_STORAGE_BUCKET environment variable – cannot "
            "initialise Firebase storage."
        )

    cred: credentials.Base = _load_credentials()

    _firebase_app = firebase_admin.initialize_app(cred, {"storageBucket": bucket_name})
    return _firebase_app


def _load_credentials() -> credentials.Base:
    """Load Firebase credentials using env vars as described in the docs."""

    # Preferred: explicit JSON *content* passed via env – avoids temp files in Docker
    json_content = os.getenv("FIREBASE_CREDENTIALS_JSON")
    if json_content:
        try:
            data = json.loads(json_content)
        except json.JSONDecodeError as exc:
            raise RuntimeError("FIREBASE_CREDENTIALS_JSON is not valid JSON") from exc

        # Write to a NamedTemporaryFile because firebase_admin expects a file path.
        tmp = tempfile.NamedTemporaryFile(mode="w+", delete=False, suffix=".json", encoding="utf-8")
        with tmp as fp:
            json.dump(data, fp)
        return credentials.Certificate(tmp.name)

    # Fallback: path to the credentials file.
    file_path = os.getenv("FIREBASE_CREDENTIALS_FILE")
    if file_path and os.path.exists(file_path):
        return credentials.Certificate(file_path)

    # Last resort: rely on default application credentials (GAE / GCE, etc.)
    # This will look at GOOGLE_APPLICATION_CREDENTIALS automatically.
    try:
        return credentials.ApplicationDefault()
    except Exception as exc:  # pylint: disable=broad-except
        raise RuntimeError("Unable to load Firebase credentials; set the env vars as described in src/utils/firebase_storage.py docstring.") from exc


def upload_image_to_firebase(image_bytes: bytes, file_name: str, *, content_type: str = "image/png") -> str:
    """Upload raw *image_bytes* to Firebase Storage and return the public URL.

    Parameters
    ----------
    image_bytes:
        The binary payload of the image.
    file_name:
        Desired object name inside the bucket, e.g. ``"abc123.png"``.
    content_type:
        MIME type of the image. Defaults to ``"image/png"``. Set
        accordingly if you are uploading JPEGs or other formats.

    Returns
    -------
    str
        Public URL of the uploaded object.

    Raises
    ------
    RuntimeError
        If Firebase SDK could not be initialised due to missing configuration.
    Exception
        Propagates any errors raised by the underlying Firebase SDK when
        uploading/making the object public.
    """

    app = _initialise_firebase()

    bucket = storage.bucket(app=app)
    blob = bucket.blob(file_name)

    # Perform the upload.
    blob.upload_from_string(image_bytes, content_type=content_type)

    # Make the file publicly readable so that we can return a URL to the user.
    blob.make_public()

    return blob.public_url


__all__ = ["upload_image_to_firebase"]

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import List
import os
import base64
import uuid

from src.database import get_db
from src.models.user import User
from src.models.waitlist import WaitListItem
from src.schemas.waitlist import (
    WaitListItemCreate,
    WaitListItemResponse,
    WaitListScreenshotUpload,
)
from src.utils.auth import get_current_user
from src.utils.firebase_storage import upload_image_to_firebase

router = APIRouter(prefix="/waitlist", tags=["waitlist"])


@router.post("/items", response_model=WaitListItemResponse)
async def add_waitlist_item(
    item: WaitListItemCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Add a new wait-list item by providing a direct image URL."""
    db_item = WaitListItem(
        **item.model_dump(exclude_unset=True), user_id=current_user.id
    )
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item


@router.post("/upload-screenshot", response_model=WaitListItemResponse)
async def upload_screenshot(
    payload: WaitListScreenshotUpload,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Receive a base64 encoded screenshot from the browser extension, store it locally and record the path in the wait-list."""

    # Decode and persist the screenshot
    try:
        img_bytes = base64.b64decode(payload.image_base64.split(",")[-1])
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid base64 image data",
        )

    # Upload to Firebase Storage
    file_name = f"{uuid.uuid4()}.png"
    try:
        image_url = upload_image_to_firebase(img_bytes, file_name)
    except Exception as e:
        # Firebase failed. Fallback to local storage so user flow does not break.
        fallback_dir = os.environ.get("SCREENSHOTS_DIR", "data/test/screenshots")
        os.makedirs(fallback_dir, exist_ok=True)
        local_path = os.path.join(fallback_dir, file_name)

        try:
            with open(local_path, "wb") as f:
                f.write(img_bytes)
            image_url = f"/static/screenshots/{file_name}"
            # Log the issue for debugging but continue.
            print(
                "[Waitlist] Firebase upload failed; stored screenshot locally at",
                local_path,
                "error:",
                e,
            )
        except Exception as file_err:
            # If even local storage fails, report error.
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to save screenshot locally after Firebase error: {file_err}",
            )

    db_item = WaitListItem(image_url=image_url, user_id=current_user.id)
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item


@router.get("/items", response_model=List[WaitListItemResponse])
async def get_my_waitlist(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    """Retrieve all wait-list items for the authenticated user."""
    items = (
        db.query(WaitListItem)
        .filter(WaitListItem.user_id == current_user.id)
        .order_by(WaitListItem.created_at.desc())
        .all()
    )
    return items


@router.get("/download-extension")
async def download_extension():
    """Package the browser extension folder into a ZIP archive and stream it to the user.

    This avoids keeping a duplicate copy of the packaged extension in the repo and
    ensures the archive is always up-to-date with the files in the `extension/` folder.
    """

    from tempfile import NamedTemporaryFile
    from zipfile import ZipFile, ZIP_DEFLATED

    base_dir = os.path.join(os.getcwd(), "extension")
    if not os.path.isdir(base_dir):
        raise HTTPException(status_code=500, detail="Extension directory not found on server")

    tmp = NamedTemporaryFile(delete=False, suffix=".zip")
    with ZipFile(tmp.name, "w", ZIP_DEFLATED) as zipf:
        for root, _, files in os.walk(base_dir):
            for file in files:
                abs_path = os.path.join(root, file)
                # store relative path inside zip
                rel_path = os.path.relpath(abs_path, base_dir)
                zipf.write(abs_path, arcname=rel_path)

    return FileResponse(
        tmp.name,
        media_type="application/zip",
        filename="closetmind_extension.zip",
    ) 
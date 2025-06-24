from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import List
import os
import base64
import uuid
import replicate
import asyncio
import requests

from src.database import get_db
from src.models.user import User
from src.models.waitlist import WaitListItem
from src.schemas.waitlist import (
    WaitListItemCreate,
    WaitListItemResponse,
    WaitListScreenshotUpload,
    TryOnRequest,
)
from src.utils.auth import get_current_user
from src.utils.firebase_storage import upload_image_to_firebase_async, delete_image_from_firebase_async
from src.utils.tryon_analyzer import analyze_image_for_tryon

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
        image_url = await upload_image_to_firebase_async(img_bytes, file_name)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save screenshot to Firebase: {e}",
        )

    db_item = WaitListItem(image_url=image_url, user_id=current_user.id)
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item


@router.post("/try-on/{item_id}", response_model=WaitListItemResponse)
async def try_on_item(
    item_id: int,
    payload: TryOnRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Try on a waitlist item with user's photo."""
    # Get the waitlist item
    db_item = db.query(WaitListItem).filter(
        WaitListItem.id == item_id,
        WaitListItem.user_id == current_user.id
    ).first()
    
    if not db_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Waitlist item not found or does not belong to current user"
        )

    try:
        # Decode and upload user's photo
        img_bytes = base64.b64decode(payload.image_base64.split(",")[-1])
        file_name = f"user_photo_{uuid.uuid4()}.png"
        user_photo_url = await upload_image_to_firebase_async(img_bytes, file_name)

        # Analyze the clothing image to get a description and category
        analysis_result = await analyze_image_for_tryon(db_item.image_url)
        garment_description = analysis_result.get("garment_des", "")
        category = analysis_result.get("category", "upper_body") # Default to upper_body

        # Call Replicate API for try-on (asynchronously in thread)
        def call_replicate_model():
            input_data = {
                "garm_img": db_item.image_url,
                "human_img": user_photo_url,
                "garment_des": garment_description,
                "category": category,
                "steps": 40
            }
            output = replicate.run(
                "cuuupid/idm-vton:0513734a452173b8173e907e3a59d19a36266e55b48528559432bd21c7d7e985",
                input=input_data
            )
            # Download the result
            response = requests.get(output)
            response.raise_for_status()
            return response.content

        # Run the blocking Replicate call in a separate thread
        loop = asyncio.get_running_loop()
        result_bytes = await loop.run_in_executor(None, call_replicate_model)

        # Save the result to Firebase
        result_file_name = f"tryon_{uuid.uuid4()}.png"
        try_on_url = await upload_image_to_firebase_async(result_bytes, result_file_name)

        # Update the waitlist item with try-on URL
        db_item.try_on_url = try_on_url
        db_item.status = "processed"
        db.commit()
        db.refresh(db_item)

        return db_item

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process try-on request: {str(e)}"
        )


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


@router.delete("/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_waitlist_item(
    item_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Delete a waitlist item.
    """
    item = db.query(WaitListItem).filter(
        WaitListItem.id == item_id,
        WaitListItem.user_id == current_user.id
    ).first()

    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Waitlist item not found"
        )

    # Delete images from Firebase
    if item.image_url:
        await delete_image_from_firebase_async(item.image_url)
    if item.try_on_url:
        await delete_image_from_firebase_async(item.try_on_url)

    # Delete from database
    db.delete(item)
    db.commit()

    return


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
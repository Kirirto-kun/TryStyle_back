from fastapi import APIRouter, Depends, HTTPException, status, File, UploadFile, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List
import uuid
import requests
import logging
from src.database import get_db, SessionLocal
from src.models.tryon import TryOn
from src.models.user import User
from src.schemas.tryon import TryOnResponse
from src.utils.auth import get_current_user
from src.utils.firebase_storage import upload_image_to_firebase_async, delete_image_from_firebase_async
from src.utils.tryon_analyzer import analyze_image_for_tryon
import replicate
import asyncio

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tryon", tags=["tryon"])

async def process_tryon_in_background(
    tryon_id: int, 
    clothing_bytes: bytes, 
    human_bytes: bytes
):
    """
    Background task to process the try-on request without blocking the server.
    This now handles file uploads as well.
    """
    db = SessionLocal()
    tryon = None  # Ensure tryon is defined in the outer scope
    try:
        logger.info(f"Starting background try-on process for tryon_id: {tryon_id}")
        
        # 1. Get the TryOn object
        tryon = db.query(TryOn).filter(TryOn.id == tryon_id).first()
        if not tryon:
            logger.error(f"TryOn object with id {tryon_id} not found.")
            return

        # 2. Upload images asynchronously
        clothing_file_name = f"clothing_{uuid.uuid4()}.png"
        human_file_name = f"human_{uuid.uuid4()}.png"
        
        clothing_url_task = upload_image_to_firebase_async(clothing_bytes, clothing_file_name)
        human_url_task = upload_image_to_firebase_async(human_bytes, human_file_name)
        
        clothing_url, human_url = await asyncio.gather(clothing_url_task, human_url_task)

        # Update DB with image URLs
        tryon.clothing_image_url = clothing_url
        tryon.human_image_url = human_url
        db.commit()

        # Analyze the clothing image to get a description
        logger.info(f"Analyzing clothing image for try-on: {clothing_url}")
        analysis_result = await analyze_image_for_tryon(clothing_url)
        garment_description = analysis_result.get("garment_des", "")
        category = analysis_result.get("category", "upper_body") # Default to upper_body
        logger.info(f"Generated garment description: {garment_description}")
        logger.info(f"Determined category: {category}")

        # 3. Call Replicate try-on model (asynchronously in thread)
        def call_replicate_model():
            input_data = {
                "steps": 40,
                "garm_img": clothing_url,
                "human_img": human_url,
                "garment_des": garment_description,
                "category": category
            }
            output = replicate.run(
                "cuuupid/idm-vton:0513734a452173b8173e907e3a59d19a36266e55b48528559432bd21c7d7e985",
                input=input_data
            )
            response = requests.get(output)
            response.raise_for_status()
            return response.content

        # Run the blocking Replicate call in a separate thread
        loop = asyncio.get_running_loop()
        result_bytes = await loop.run_in_executor(None, call_replicate_model)

        result_file_name = f"tryon_result_{uuid.uuid4()}.png"
        result_url = await upload_image_to_firebase_async(result_bytes, result_file_name)

        # 4. Update the TryOn object with the result
        tryon.result_url = result_url
        tryon.status = "completed"
        db.commit()
        logger.info(f"Successfully processed and saved result for tryon_id: {tryon_id}")
    
    except Exception as e:
        logger.error(f"Error in background task for tryon_id {tryon_id}: {e}")
        if tryon:
            tryon.status = "failed"
            db.commit()

    finally:
        db.close()

@router.post("/", response_model=TryOnResponse)
async def create_tryon(
    background_tasks: BackgroundTasks,
    clothing_image: UploadFile = File(...),
    human_image: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Read image bytes immediately. This is still a quick operation.
    clothing_bytes = await clothing_image.read()
    human_bytes = await human_image.read()

    # Create initial TryOn object in DB with minimal info
    # URLs will be populated by the background task
    tryon = TryOn(
        user_id=current_user.id,
        clothing_image_url="", # Placeholder
        human_image_url="",   # Placeholder
        status="processing"
    )
    db.add(tryon)
    db.commit()
    db.refresh(tryon)

    # Start background task for all processing
    background_tasks.add_task(
        process_tryon_in_background,
        tryon_id=tryon.id,
        clothing_bytes=clothing_bytes,
        human_bytes=human_bytes
    )

    return tryon

@router.get("/{tryon_id}", response_model=TryOnResponse)
async def get_tryon_by_id(
    tryon_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get a specific try-on result by its ID.
    """
    tryon = db.query(TryOn).filter(
        TryOn.id == tryon_id,
        TryOn.user_id == current_user.id
    ).first()
    
    if not tryon:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Try-on not found"
        )
        
    return tryon

@router.get("/", response_model=List[TryOnResponse])
async def get_my_tryons(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    tryons = db.query(TryOn).filter(TryOn.user_id == current_user.id).order_by(TryOn.created_at.desc()).all()
    return tryons

@router.delete("/{tryon_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_tryon(
    tryon_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Delete a try-on result.
    """
    tryon = db.query(TryOn).filter(
        TryOn.id == tryon_id,
        TryOn.user_id == current_user.id
    ).first()

    if not tryon:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Try-on not found"
        )

    # Delete all associated images from Firebase
    if tryon.clothing_image_url:
        await delete_image_from_firebase_async(tryon.clothing_image_url)
    if tryon.human_image_url:
        await delete_image_from_firebase_async(tryon.human_image_url)
    if tryon.result_url:
        await delete_image_from_firebase_async(tryon.result_url)

    # Delete from database
    db.delete(tryon)
    db.commit()

    return 
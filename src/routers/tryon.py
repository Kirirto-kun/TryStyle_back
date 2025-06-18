from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
import base64
import uuid
from src.database import get_db
from src.models.tryon import TryOn
from src.models.user import User
from src.schemas.tryon import TryOnRequest, TryOnResponse
from src.utils.auth import get_current_user
from src.utils.firebase_storage import upload_image_to_firebase
import replicate

router = APIRouter(prefix="/tryon", tags=["tryon"])

@router.post("/", response_model=TryOnResponse)
async def create_tryon(
    payload: TryOnRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # 1. Decode and upload clothing image
    try:
        clothing_bytes = base64.b64decode(payload.clothing_image_base64.split(",")[-1])
        clothing_file_name = f"clothing_{uuid.uuid4()}.png"
        clothing_url = upload_image_to_firebase(clothing_bytes, clothing_file_name)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid clothing image: {e}")

    # 2. Decode and upload human image
    try:
        human_bytes = base64.b64decode(payload.human_image_base64.split(",")[-1])
        human_file_name = f"human_{uuid.uuid4()}.png"
        human_url = upload_image_to_firebase(human_bytes, human_file_name)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid human image: {e}")

    # 3. Call Replicate try-on model
    try:
        input_data = {
            "garm_img": clothing_url,
            "human_img": human_url,
            "garment_des": ""
        }
        output = replicate.run(
            "cuuupid/idm-vton:0513734a452173b8173e907e3a59d19a36266e55b48528559432bd21c7d7e985",
            input=input_data
        )
        result_bytes = output.read()
        result_file_name = f"tryon_result_{uuid.uuid4()}.png"
        result_url = upload_image_to_firebase(result_bytes, result_file_name)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Try-on model error: {e}")

    # 4. Save to DB
    tryon = TryOn(
        user_id=current_user.id,
        clothing_image_url=clothing_url,
        human_image_url=human_url,
        result_url=result_url
    )
    db.add(tryon)
    db.commit()
    db.refresh(tryon)
    return tryon

@router.get("/", response_model=List[TryOnResponse])
async def get_my_tryons(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    tryons = db.query(TryOn).filter(TryOn.user_id == current_user.id).order_by(TryOn.created_at.desc()).all()
    return tryons 
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from src.agent.agents import process_user_request
from src.database import get_db
from src.models.user import User
from src.utils.auth import get_current_user

router = APIRouter()

class UserRequest(BaseModel):
    message: str

@router.post("/chat")
async def chat(
    request: UserRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Process user requests through the agent system.
    Requires authentication.
    
    request_type can be:
    - general: for general questions
    - outfit: for outfit recommendations
    - search: for web search and data extraction
    """
    try:
        # Add user context to the message
        user_context = f"[User ID: {current_user.id}] "
        full_message = user_context + "\n\n" + request.message
        
        response = await process_user_request(full_message)
        return {"response": response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
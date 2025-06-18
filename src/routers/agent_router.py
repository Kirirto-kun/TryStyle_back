from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from src.agent.agents import process_user_request
from src.database import get_db
from src.models.user import User
from src.models.chat import Chat
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
    
    This endpoint creates a temporary chat session for the request.
    For persistent chat history, use the /chats endpoints instead.
    
    request_type can be:
    - general: for general questions
    - outfit: for outfit recommendations
    - search: for web search and data extraction
    """
    try:
        # Create a temporary chat for this request or get existing default chat
        default_chat = db.query(Chat).filter(
            Chat.user_id == current_user.id,
            Chat.title == "Agent Chat"
        ).first()
        
        if not default_chat:
            # Create a default chat for agent interactions
            default_chat = Chat(
                title="Agent Chat",
                user_id=current_user.id
            )
            db.add(default_chat)
            db.commit()
            db.refresh(default_chat)
        
        # Pass all required parameters to the agent
        response = await process_user_request(
            message=request.message, 
            user_id=current_user.id,
            db=db,
            chat_id=default_chat.id
        )
        return {"response": response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime

from src.database import get_db
from src.models.user import User
from src.models.chat import Chat, Message
from src.schemas.chat import (
    ChatCreate,
    ChatResponse,
    ChatWithMessages,
    MessageResponse,
    SendMessageRequest
)
from src.utils.auth import get_current_user
from src.agent.agents import process_user_request
from src.utils.chat_title_generator import generate_chat_title

router = APIRouter(prefix="/chats", tags=["chats"])


@router.post("/", response_model=ChatResponse)
async def create_chat(
    chat: ChatCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new chat."""
    db_chat = Chat(
        title=chat.title,
        user_id=current_user.id
    )
    db.add(db_chat)
    db.commit()
    db.refresh(db_chat)
    return db_chat


@router.get("/", response_model=List[ChatResponse])
async def get_my_chats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all chats for the current user."""
    chats = (
        db.query(Chat)
        .filter(Chat.user_id == current_user.id)
        .order_by(Chat.updated_at.desc())
        .all()
    )
    return chats


@router.get("/{chat_id}", response_model=ChatWithMessages)
async def get_chat_with_messages(
    chat_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a specific chat with all its messages."""
    chat = db.query(Chat).filter(
        Chat.id == chat_id,
        Chat.user_id == current_user.id
    ).first()
    
    if not chat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat not found"
        )
    
    return chat


@router.post("/{chat_id}/messages", response_model=MessageResponse)
async def send_message(
    chat_id: int,
    request: SendMessageRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Send a message to a chat and get AI response."""
    # Check if chat exists and belongs to user
    chat = db.query(Chat).filter(
        Chat.id == chat_id,
        Chat.user_id == current_user.id
    ).first()
    
    if not chat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat not found"
        )
    
    try:
        # Save user message
        user_message = Message(
            content=request.message,
            role="user",
            chat_id=chat_id
        )
        db.add(user_message)
        db.commit()
        db.refresh(user_message)
        
        # Process message through AI agent with chat history
        ai_response = await process_user_request(
            request.message,
            current_user.id,
            db=db,
            chat_id=chat_id
        )
        
        # Save AI response
        ai_message = Message(
            content=ai_response,
            role="assistant",
            chat_id=chat_id
        )
        db.add(ai_message)
        
        # Update chat's updated_at timestamp
        chat.updated_at = datetime.utcnow()
        
        db.commit()
        db.refresh(ai_message)
        
        return ai_message
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process message: {str(e)}"
        )


@router.get("/{chat_id}/messages", response_model=List[MessageResponse])
async def get_chat_messages(
    chat_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all messages from a specific chat."""
    # Check if chat exists and belongs to user
    chat = db.query(Chat).filter(
        Chat.id == chat_id,
        Chat.user_id == current_user.id
    ).first()
    
    if not chat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat not found"
        )
    
    messages = (
        db.query(Message)
        .filter(Message.chat_id == chat_id)
        .order_by(Message.created_at.asc())
        .all()
    )
    
    return messages


@router.delete("/{chat_id}")
async def delete_chat(
    chat_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a chat and all its messages."""
    chat = db.query(Chat).filter(
        Chat.id == chat_id,
        Chat.user_id == current_user.id
    ).first()
    
    if not chat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat not found"
        )
    
    db.delete(chat)
    db.commit()
    
    return {"message": "Chat deleted successfully"}


@router.post("/init", response_model=ChatWithMessages, status_code=status.HTTP_201_CREATED)
async def init_chat_with_first_message(
    request: SendMessageRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new chat, auto-generate its title from the first user message and save that message."""

    # 1. Generate chat title
    title = await generate_chat_title(request.message)

    # 2. Create chat record
    db_chat = Chat(title=title, user_id=current_user.id)
    db.add(db_chat)
    db.commit()
    db.refresh(db_chat)

    # 3. Save user's first message
    first_msg = Message(content=request.message, role="user", chat_id=db_chat.id)
    db.add(first_msg)
    db.commit()
    db.refresh(first_msg)

    # 4. Получаем ответ ЛЛМ и сохраняем его
    try:
        ai_response_text = await process_user_request(
            request.message,
            current_user.id,
            db=db,
            chat_id=db_chat.id
        )

        ai_msg = Message(content=ai_response_text, role="assistant", chat_id=db_chat.id)
        db.add(ai_msg)

        # Обновляем время изменения чата
        db_chat.updated_at = datetime.utcnow()

        db.commit()
    except Exception as e:
        # Если ЛЛМ упал, откатывать сообщения не будем – чат всё равно создан.
        db.rollback()
        print(f"Failed to generate AI response for new chat {db_chat.id}: {e}")

    # 5. Refresh chat to include relationship data (messages)
    db.refresh(db_chat)

    return db_chat 
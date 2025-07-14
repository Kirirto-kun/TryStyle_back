from fastapi import APIRouter, Depends, HTTPException, status, Body
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import timedelta
from src.database import get_db
from src.models.user import User
from src.models.store import Store
from src.schemas.user import UserCreate, UserResponse, Token, CurrentUserResponse
from src.utils.auth import (
    verify_password,
    get_password_hash,
    create_access_token,
    ACCESS_TOKEN_EXPIRE_MINUTES,
    get_current_user
)
from src.utils.email import (
    send_verification_email,
    generate_verification_code,
    store_verification_code,
    get_verification_code,
    delete_verification_code,
)
from pydantic import BaseModel, EmailStr
import os
from google.oauth2 import id_token
from google.auth.transport.requests import Request as GoogleRequest

router = APIRouter(prefix="/auth", tags=["auth"])

class GoogleLoginRequest(BaseModel):
    id_token: str

class EmailSchema(BaseModel):
    email: EmailStr

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")

@router.post("/send-verification-code")
def send_code(payload: EmailSchema, db: Session = Depends(get_db)):
    # Проверяем, существует ли пользователь
    db_user = db.query(User).filter(User.email == payload.email).first()
    if db_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    code = generate_verification_code()
    store_verification_code(payload.email, code)
    if not send_verification_email(payload.email, code):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send verification email"
        )
    return {"message": "Verification code sent"}

@router.post("/register", response_model=UserResponse)
def register(user: UserCreate, db: Session = Depends(get_db)):
    # Проверяем, существует ли пользователь
    db_user = db.query(User).filter(User.email == user.email).first()
    if db_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Проверяем код верификации
    stored_code = get_verification_code(user.email)
    if not stored_code or stored_code != user.verification_code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid verification code"
        )

    # Создаем нового пользователя
    hashed_password = get_password_hash(user.password)
    db_user = User(
        email=user.email,
        username=user.username,
        hashed_password=hashed_password
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    # Удаляем код после успешной регистрации
    delete_verification_code(user.email)

    return db_user

@router.post("/token", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/google-login", response_model=Token)
async def google_login(payload: GoogleLoginRequest = Body(...), db: Session = Depends(get_db)):
    try:
        idinfo = id_token.verify_oauth2_token(
            payload.id_token,
            GoogleRequest(),
            audience=GOOGLE_CLIENT_ID
        )
        email = idinfo["email"]
        username = email.split("@")[0]
        user = db.query(User).filter(User.email == email).first()
        if not user:
            user = User(username=username, email=email, hashed_password="google-oauth")
            db.add(user)
            db.commit()
            db.refresh(user)
        access_token = create_access_token(data={"sub": user.email})
        return {"access_token": access_token, "token_type": "bearer"}
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid Google token") 

@router.get("/me", response_model=CurrentUserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Получить информацию о текущем авторизованном пользователе"""
    
    # Получаем информацию о магазине если пользователь - админ магазина
    managed_store = None
    if current_user.is_store_admin and current_user.store_id:
        store = db.query(Store).filter(Store.id == current_user.store_id).first()
        if store:
            managed_store = {
                "id": store.id,
                "name": store.name,
                "city": store.city,
                "logo_url": store.logo_url,
                "rating": store.rating
            }
    
    return CurrentUserResponse(
        id=current_user.id,
        email=current_user.email,
        username=current_user.username,
        is_active=current_user.is_active,
        created_at=current_user.created_at,
        updated_at=current_user.updated_at,
        role=current_user.role.value.upper() if current_user.role else "USER",
        store_id=current_user.store_id,
        phone=current_user.phone,
        is_store_admin=current_user.is_store_admin,
        is_admin=current_user.is_admin,
        can_manage_stores=current_user.can_manage_stores,
        managed_store=managed_store
    ) 
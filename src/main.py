from dotenv import load_dotenv
load_dotenv()
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from src.database import engine, Base
from src.routers import auth, agent_router, wardrobe, waitlist, chat, tryon, stores, products, reviews, admin
import os

# NOTE: Таблицы теперь создаются через миграции Alembic
# Используйте: alembic upgrade head для применения миграций

# Middleware для контроля размера файла
class LimitUploadSize(BaseHTTPMiddleware):
    def __init__(self, app, max_upload_size: int):
        super().__init__(app)
        self.max_upload_size = max_upload_size

    async def dispatch(self, request: Request, call_next):
        if request.method == "POST":
            if "content-length" in request.headers:
                content_length = int(request.headers["content-length"])
                if content_length > self.max_upload_size:
                    return JSONResponse(
                        status_code=413,
                        content={
                            "detail": f"File too large. Maximum size allowed is {self.max_upload_size/1024/1024:.1f}MB"
                        }
                    )
        return await call_next(request)

app = FastAPI(
    title="ClosetMind API",
    # Увеличиваем лимит размера запроса до 10MB
    max_upload_size=50 * 1024 * 1024  # 10MB в байтах
)

# Настройка CORS
origins = [
    "https://stylence.vercel.app",
    "http://localhost:3000",  # Для локальной разработки
    "http://localhost:5173",  # Для Vite dev server
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"]
)

# Добавляем middleware для контроля размера файла (10MB)
app.add_middleware(LimitUploadSize, max_upload_size=10 * 1024 * 1024)

# Подключаем роутеры
app.include_router(auth.router)
app.include_router(agent_router.router, prefix="/api/v1/agent", tags=["agent"])
app.include_router(wardrobe.router)
app.include_router(waitlist.router)
app.include_router(chat.router, prefix="/api/v1")
app.include_router(tryon.router)

# Новые роутеры для каталога
app.include_router(stores.router, prefix="/api/v1")
app.include_router(products.router, prefix="/api/v1")
app.include_router(reviews.router, prefix="/api/v1")

# Административные роутеры
app.include_router(admin.router, prefix="/api/v1")

@app.get("/")
async def root():
    return {"message": "Welcome to ClosetMind API"}
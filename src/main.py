from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from src.database import engine, Base
from src.routers import auth, agent_router, wardrobe, waitlist
import os

# Создаем таблицы
Base.metadata.create_all(bind=engine)

app = FastAPI(title="ClosetMind API")

# Настройка CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # В продакшене укажите конкретные домены
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Подключаем роутеры
app.include_router(auth.router)
app.include_router(agent_router.router, prefix="/api/v1/agent", tags=["agent"])
app.include_router(wardrobe.router)
app.include_router(waitlist.router)

# Ensure screenshots directory exists so StaticFiles mount won't fail
SCREENSHOTS_DIR = os.getenv("SCREENSHOTS_DIR", "data/test/screenshots")
os.makedirs(SCREENSHOTS_DIR, exist_ok=True)

app.mount(
    "/static/screenshots",
    StaticFiles(directory=SCREENSHOTS_DIR),
    name="screenshots",
)

@app.get("/")
async def root():
    return {"message": "Welcome to ClosetMind API"}
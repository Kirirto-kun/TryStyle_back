from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.database import engine, Base
from src.routers import auth

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

@app.get("/")
async def root():
    return {"message": "Welcome to ClosetMind API"}

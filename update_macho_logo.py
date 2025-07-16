#!/usr/bin/env python3
"""
Скрипт для обновления логотипа магазина Macho
"""

import os
import sys
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Добавляем корневую директорию в путь для импорта модулей
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.models.store import Store

# Загружаем переменные окружения
load_dotenv()

def update_macho_logo():
    """Обновляет логотип магазина Macho"""
    
    # Подключение к базе данных
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("❌ DATABASE_URL не найден в переменных окружения")
        return
    
    # Исправляем URL для SQLAlchemy
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)
    
    engine = create_engine(database_url)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    # Новая ссылка на логотип
    new_logo_url = "https://storage.googleapis.com/onaitabu.firebasestorage.app/d6e80e9f-29de-4299-a51f-f091c32f8183.png"
    
    session = SessionLocal()
    try:
        # Ищем магазин Macho
        store = session.query(Store).filter(Store.name.ilike("macho")).first()
        
        if not store:
            print("❌ Магазин 'Macho' не найден в базе данных")
            print("Доступные магазины:")
            stores = session.query(Store).all()
            for s in stores:
                print(f"  - ID: {s.id}, Название: {s.name}")
            return
        
        print(f"✅ Найден магазин: {store.name}")
        print(f"📍 Город: {store.city}")
        print(f"🔗 Текущий логотип: {store.logo_url}")
        
        # Обновляем логотип
        old_logo = store.logo_url
        store.logo_url = new_logo_url
        
        session.commit()
        
        print(f"\n🎉 Логотип успешно обновлен!")
        print(f"📎 Старая ссылка: {old_logo}")
        print(f"🆕 Новая ссылка: {new_logo_url}")
        
    except Exception as e:
        session.rollback()
        print(f"❌ Ошибка при обновлении: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    update_macho_logo() 
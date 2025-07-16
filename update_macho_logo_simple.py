#!/usr/bin/env python3
"""
Простой скрипт для обновления логотипа магазина Macho через SQL
"""

import os
import psycopg2
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

def update_macho_logo():
    """Обновляет логотип магазина Macho через прямой SQL"""
    
    # Получаем URL базы данных
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("❌ DATABASE_URL не найден в переменных окружения")
        return
    
    # Новая ссылка на логотип
    new_logo_url = "https://storage.googleapis.com/onaitabu.firebasestorage.app/d6e80e9f-29de-4299-a51f-f091c32f8183.png"
    
    try:
        # Подключаемся к базе данных
        conn = psycopg2.connect(database_url)
        cur = conn.cursor()
        
        # Сначала проверим, есть ли магазин Macho
        cur.execute("SELECT id, name, city, logo_url FROM stores WHERE LOWER(name) LIKE LOWER(%s)", ('%macho%',))
        store = cur.fetchone()
        
        if not store:
            print("❌ Магазин 'Macho' не найден в базе данных")
            print("Доступные магазины:")
            cur.execute("SELECT id, name FROM stores ORDER BY name")
            stores = cur.fetchall()
            for store_id, name in stores:
                print(f"  - ID: {store_id}, Название: {name}")
            return
        
        store_id, name, city, current_logo = store
        print(f"✅ Найден магазин: {name}")
        print(f"📍 Город: {city}")
        print(f"🔗 Текущий логотип: {current_logo}")
        
        # Обновляем логотип
        cur.execute("UPDATE stores SET logo_url = %s WHERE id = %s", (new_logo_url, store_id))
        conn.commit()
        
        print(f"\n🎉 Логотип успешно обновлен!")
        print(f"📎 Старая ссылка: {current_logo}")
        print(f"🆕 Новая ссылка: {new_logo_url}")
        
    except Exception as e:
        if 'conn' in locals():
            conn.rollback()
        print(f"❌ Ошибка при обновлении: {e}")
    finally:
        if 'cur' in locals():
            cur.close()
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    update_macho_logo() 
#!/usr/bin/env python3
"""
Скрипт для проверки количества зарегистрированных пользователей в приложении ClosetMind.
Показывает общую статистику и детальную информацию о пользователях.
"""

import sys
import os
from pathlib import Path
from datetime import datetime, timedelta

# Добавляем корневую директорию проекта в Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy.orm import sessionmaker
from sqlalchemy import func, and_, text
from src.database import engine, get_db
from src.models.user import User
from src.models.clothing import ClothingItem
from src.models.chat import Chat, Message
from src.models.waitlist import WaitListItem
from src.models.tryon import TryOn
from src.models.store import Store
from src.models.product import Product
from src.models.review import Review

def get_db_session():
    """Создает сессию для работы с базой данных."""
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return SessionLocal()

def get_user_statistics():
    """Получает детальную статистику пользователей."""
    db = None
    try:
        db = get_db_session()
        
        # Общее количество пользователей
        total_users = db.query(User).count()
        
        # Активные пользователи
        active_users = db.query(User).filter(User.is_active == True).count()
        
        # Неактивные пользователи
        inactive_users = db.query(User).filter(User.is_active == False).count()
        
        # Пользователи за последние 24 часа
        yesterday = datetime.now() - timedelta(days=1)
        users_last_24h = db.query(User).filter(User.created_at >= yesterday).count()
        
        # Пользователи за последнюю неделю
        week_ago = datetime.now() - timedelta(days=7)
        users_last_week = db.query(User).filter(User.created_at >= week_ago).count()
        
        # Пользователи за последний месяц
        month_ago = datetime.now() - timedelta(days=30)
        users_last_month = db.query(User).filter(User.created_at >= month_ago).count()
        
        # Самый первый пользователь
        first_user = db.query(User).order_by(User.created_at.asc()).first()
        
        # Самый последний пользователь
        latest_user = db.query(User).order_by(User.created_at.desc()).first()
        
        # Пользователи с телефонами
        users_with_phone = db.query(User).filter(User.phone.isnot(None)).count()
        
        return {
            'total_users': total_users,
            'active_users': active_users,
            'inactive_users': inactive_users,
            'users_last_24h': users_last_24h,
            'users_last_week': users_last_week,
            'users_last_month': users_last_month,
            'first_user': first_user,
            'latest_user': latest_user,
            'users_with_phone': users_with_phone
        }
        
    except Exception as e:
        print(f"❌ Ошибка при получении статистики: {e}")
        return None
    finally:
        # CRITICAL: Always close the database session
        if db:
            try:
                db.close()
            except Exception as close_error:
                print(f"Error closing database session: {close_error}")

def print_user_statistics():
    """Выводит красиво отформатированную статистику пользователей."""
    print("👥 СТАТИСТИКА ПОЛЬЗОВАТЕЛЕЙ CLOSETMIND")
    print("=" * 50)
    
    stats = get_user_statistics()
    if not stats:
        return
    
    # Основная статистика
    print(f"📊 ОБЩАЯ СТАТИСТИКА:")
    print(f"   Всего пользователей: {stats['total_users']:,}")
    print(f"   Активные: {stats['active_users']:,}")
    print(f"   Неактивные: {stats['inactive_users']:,}")
    print(f"   С телефонами: {stats['users_with_phone']:,}")
    print()
    
    # Статистика по времени
    print(f"📅 РЕГИСТРАЦИИ ПО ВРЕМЕНИ:")
    print(f"   За последние 24 часа: {stats['users_last_24h']:,}")
    print(f"   За последнюю неделю: {stats['users_last_week']:,}")
    print(f"   За последний месяц: {stats['users_last_month']:,}")
    print()
    
    # Информация о первом и последнем пользователе
    if stats['first_user']:
        print(f"👤 ПЕРВЫЙ ПОЛЬЗОВАТЕЛЬ:")
        print(f"   ID: {stats['first_user'].id}")
        print(f"   Username: {stats['first_user'].username}")
        print(f"   Email: {stats['first_user'].email}")
        print(f"   Дата регистрации: {stats['first_user'].created_at.strftime('%d.%m.%Y %H:%M:%S')}")
        print()
    
    if stats['latest_user']:
        print(f"🆕 ПОСЛЕДНИЙ ПОЛЬЗОВАТЕЛЬ:")
        print(f"   ID: {stats['latest_user'].id}")
        print(f"   Username: {stats['latest_user'].username}")
        print(f"   Email: {stats['latest_user'].email}")
        print(f"   Дата регистрации: {stats['latest_user'].created_at.strftime('%d.%m.%Y %H:%M:%S')}")
        print()
    
    # Процентные показатели
    if stats['total_users'] > 0:
        active_percentage = (stats['active_users'] / stats['total_users']) * 100
        phone_percentage = (stats['users_with_phone'] / stats['total_users']) * 100
        
        print(f"📈 ПОКАЗАТЕЛИ:")
        print(f"   Активность пользователей: {active_percentage:.1f}%")
        print(f"   Заполненность телефонов: {phone_percentage:.1f}%")
        print()
    
    print("=" * 50)

def test_database_connection():
    """Тестирует подключение к базе данных."""
    print("🔌 ТЕСТИРОВАНИЕ ПОДКЛЮЧЕНИЯ К БД")
    print("-" * 30)
    
    db = None
    try:
        db = get_db_session()
        
        # Простой тестовый запрос
        result = db.execute(text("SELECT 1")).scalar()
        
        # Проверяем доступность таблицы users
        users_count = db.query(User).count()
        
        print("✅ Подключение к базе данных успешно")
        print(f"✅ Таблица users доступна (найдено записей: {users_count})")
        print("✅ Все проверки пройдены")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка подключения к БД: {e}")
        print("💡 Проверьте:")
        print("   - Настройки DATABASE_URL в .env файле")
        print("   - Запущена ли база данных")
        print("   - Применены ли миграции (alembic upgrade head)")
        return False
    finally:
        # CRITICAL: Always close the database session
        if db:
            try:
                db.close()
            except Exception as close_error:
                print(f"Error closing database session: {close_error}")

def main():
    """Основная функция скрипта."""
    print()
    
    # Тестируем подключение
    if not test_database_connection():
        sys.exit(1)
    
    print()
    
    # Показываем статистику
    print_user_statistics()
    
    # Подсказки для дальнейших действий
    print("💡 ДОПОЛНИТЕЛЬНЫЕ КОМАНДЫ:")
    print("   Для API доступа: GET /api/v1/admin/users/stats")
    print("   Для подробной статистики: GET /api/v1/admin/users/count")
    print()

if __name__ == "__main__":
    main() 
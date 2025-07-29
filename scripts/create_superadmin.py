#!/usr/bin/env python3
"""
Скрипт для создания суперадмина.
Создает пользователя с ролью ADMIN, который имеет полный доступ ко всем функциям системы.
"""

import sys
import os
from pathlib import Path

# Добавляем корневую директорию проекта в Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from src.utils.auth import get_password_hash
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

# Получаем URL базы данных
DATABASE_URL = os.getenv("DATABASE_URL")
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable not set")

# Создаем подключение
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def check_enum_values():
    """Проверяет доступные значения ENUM role"""
    db = SessionLocal()
    try:
        result = db.execute(text("""
            SELECT e.enumlabel 
            FROM pg_type t 
            JOIN pg_enum e ON t.oid = e.enumtypid 
            WHERE t.typname = 'userrole'
            ORDER BY e.enumsortorder;
        """))
        enum_values = [row[0] for row in result.fetchall()]
        print(f"📋 Доступные значения роли: {enum_values}")
        return enum_values
    except Exception as e:
        print(f"❌ Ошибка при получении значений ENUM: {str(e)}")
        return []
    finally:
        db.close()


def create_superadmin(email: str, username: str, password: str):
    """
    Создает суперадмина используя прямые SQL команды
    
    Args:
        email: Email суперадмина
        username: Имя пользователя
        password: Пароль
    """
    db = SessionLocal()
    try:
        # Проверяем, существует ли пользователь с таким email
        result = db.execute(text("SELECT id, username, role FROM users WHERE email = :email"), {"email": email})
        existing_user = result.fetchone()
        
        if existing_user:
            print(f"❌ Пользователь с email '{email}' уже существует!")
            print(f"   ID: {existing_user[0]}")
            print(f"   Username: {existing_user[1]}")
            print(f"   Текущая роль: {existing_user[2]}")
            
            # Если это не админ, предлагаем повысить
            if existing_user[2] != 'ADMIN':
                confirm = input(f"🔄 Повысить пользователя {existing_user[1]} до суперадмина? (y/N): ").strip().lower()
                if confirm == 'y':
                    db.execute(
                        text("UPDATE users SET role = 'ADMIN', store_id = NULL WHERE id = :user_id"),
                        {"user_id": existing_user[0]}
                    )
                    db.commit()
                    print(f"✅ Пользователь {existing_user[1]} повышен до суперадмина!")
                    return True
            else:
                print("✅ Пользователь уже является суперадмином!")
            return False
        
        # Проверяем, существует ли пользователь с таким username
        result = db.execute(text("SELECT id, email, role FROM users WHERE username = :username"), {"username": username})
        existing_username = result.fetchone()
        
        if existing_username:
            print(f"❌ Пользователь с username '{username}' уже существует!")
            print(f"   Email: {existing_username[1]}")
            print(f"   Роль: {existing_username[2]}")
            
            # Если это нужный email, предлагаем повысить
            if existing_username[1] == email and existing_username[2] != 'ADMIN':
                confirm = input(f"🔄 Повысить пользователя {username} до суперадмина? (y/N): ").strip().lower()
                if confirm == 'y':
                    db.execute(
                        text("UPDATE users SET role = 'ADMIN', store_id = NULL WHERE id = :user_id"),
                        {"user_id": existing_username[0]}
                    )
                    db.commit()
                    print(f"✅ Пользователь {username} повышен до суперадмина!")
                    return True
            elif existing_username[1] == email and existing_username[2] == 'ADMIN':
                print("✅ Пользователь уже является суперадмином!")
                return True
            return False
        
        # Создаем суперадмина
        hashed_password = get_password_hash(password)
        
        db.execute(
            text("""
                INSERT INTO users (email, username, hashed_password, role, store_id, is_active, created_at) 
                VALUES (:email, :username, :password, 'ADMIN', NULL, true, NOW())
            """),
            {
                "email": email,
                "username": username,
                "password": hashed_password
            }
        )
        db.commit()
        
        print(f"✅ Суперадмин успешно создан!")
        print(f"   👤 Пользователь: {username} ({email})")
        print(f"   🔑 Пароль: {password}")
        print(f"   🎯 Роль: ADMIN")
        print(f"   🚀 Полномочия: Полный доступ ко всем функциям системы")
        
        return True
        
    except Exception as e:
        db.rollback()
        print(f"❌ Ошибка при создании суперадмина: {str(e)}")
        return False
    finally:
        db.close()


def list_existing_admins():
    """Показывает список существующих админов"""
    db = SessionLocal()
    try:
        # Получаем всех админов
        result = db.execute(text("""
            SELECT username, email, role, store_id, is_active 
            FROM users 
            WHERE role IN ('ADMIN', 'STORE_ADMIN')
            ORDER BY role, username
        """))
        admins = result.fetchall()
        
        print("\n📋 Существующие администраторы:")
        print("-" * 60)
        
        superadmins = [admin for admin in admins if admin[2] == 'ADMIN']
        store_admins = [admin for admin in admins if admin[2] == 'STORE_ADMIN']
        
        if superadmins:
            print("🚀 Суперадмины:")
            for admin in superadmins:
                status = "Активен" if admin[4] else "Неактивен"
                print(f"   • {admin[0]} ({admin[1]}) - {status}")
        else:
            print("🚀 Суперадмины: Нет")
        
        if store_admins:
            print("\n🏪 Админы магазинов:")
            for admin in store_admins:
                store_info = f" [Магазин ID: {admin[3]}]" if admin[3] else " [Без магазина]"
                status = "Активен" if admin[4] else "Неактивен"
                print(f"   • {admin[0]} ({admin[1]}){store_info} - {status}")
        else:
            print("\n🏪 Админы магазинов: Нет")
        
        print("-" * 60)
        
    except Exception as e:
        print(f"❌ Ошибка при получении списка админов: {str(e)}")
        # Попробуем вывести всех пользователей для отладки
        try:
            result = db.execute(text("SELECT username, email, role FROM users LIMIT 5"))
            users = result.fetchall()
            print("🔍 Первые 5 пользователей в базе:")
            for user in users:
                print(f"   • {user[0]} ({user[1]}) - роль: {user[2]}")
        except Exception as debug_e:
            print(f"❌ Ошибка при получении пользователей: {str(debug_e)}")
    finally:
        db.close()


def main():
    """Главная функция скрипта"""
    print("🚀 Создание суперадмина")
    print("=" * 50)
    
    # Проверяем доступные значения ENUM
    check_enum_values()
    
    # Показываем существующих админов
    list_existing_admins()
    
    # Создаем суперадмина с указанными данными
    print("\n🔧 Создание суперадмина с указанными данными...")
    email = "jafar@gmail.com"
    username = "jafar"
    password = "AlmatyJafar2900331!"
    
    success = create_superadmin(email, username, password)
    
    if success:
        print(f"\n🎉 Суперадмин создан успешно!")
        print(f"\n📝 Данные для входа:")
        print(f"   Email: {email}")
        print(f"   Password: {password}")
        print(f"\n🔗 API эндпоинты суперадмина:")
        print(f"   • POST /auth/token - вход в систему")
        print(f"   • GET /api/v1/admin/* - административные функции")
        print(f"   • POST /api/v1/admin/create-store-admin - создание админов магазинов")
        print(f"   • GET /api/v1/admin/store-admins - управление админами")
        print(f"   • Доступ ко всем /api/v1/store-admin/* эндпоинтам")
    else:
        print(f"\n❌ Не удалось создать суперадмина.")


if __name__ == "__main__":
    main() 
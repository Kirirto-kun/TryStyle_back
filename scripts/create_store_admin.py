#!/usr/bin/env python3
"""
Скрипт для создания тестового админа магазина.
Использует существующую базу данных и создает пользователя с ролью STORE_ADMIN.
"""

import sys
import os
from pathlib import Path

# Добавляем корневую директорию проекта в Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.database import get_db_session
from src.models.user import User, UserRole
from src.models.store import Store
from src.utils.auth import get_password_hash


def create_store_admin(
    email: str,
    username: str,
    password: str,
    store_id: int = None,
    store_name: str = None
):
    """
    Создает админа магазина
    
    Args:
        email: Email админа
        username: Имя пользователя
        password: Пароль
        store_id: ID магазина (если None, будет использован первый доступный)
        store_name: Название магазина (для поиска, если store_id не указан)
    """
    db = None
    try:
        db = get_db_session()
        
        # Проверяем, существует ли пользователь
        existing_user = db.query(User).filter(
            (User.email == email) | (User.username == username)
        ).first()
        
        if existing_user:
            print(f"❌ Пользователь с email '{email}' или username '{username}' уже существует!")
            return False
        
        # Определяем магазин
        if store_id:
            store = db.query(Store).filter(Store.id == store_id).first()
            if not store:
                print(f"❌ Магазин с ID {store_id} не найден!")
                return False
        elif store_name:
            store = db.query(Store).filter(Store.name.ilike(f"%{store_name}%")).first()
            if not store:
                print(f"❌ Магазин с названием '{store_name}' не найден!")
                return False
        else:
            # Берем первый доступный магазин
            store = db.query(Store).first()
            if not store:
                print("❌ В базе данных нет магазинов!")
                return False
        
        # Проверяем, нет ли уже админа у этого магазина
        existing_admin = db.query(User).filter(
            User.store_id == store.id,
            User.role == UserRole.STORE_ADMIN
        ).first()
        
        if existing_admin:
            print(f"❌ Магазин '{store.name}' уже имеет админа: {existing_admin.username} ({existing_admin.email})")
            return False
        
        # Создаем админа
        hashed_password = get_password_hash(password)
        new_admin = User(
            email=email,
            username=username,
            hashed_password=hashed_password,
            role=UserRole.STORE_ADMIN,
            store_id=store.id,
            is_active=True
        )
        
        db.add(new_admin)
        db.commit()
        db.refresh(new_admin)
        
        print(f"✅ Админ магазина успешно создан!")
        print(f"   👤 Пользователь: {username} ({email})")
        print(f"   🏪 Магазин: {store.name} (ID: {store.id})")
        print(f"   🔑 Пароль: {password}")
        print(f"   🎯 Роль: {new_admin.role.value}")
        
        return True
        
    except Exception as e:
        if db:
            db.rollback()
        print(f"❌ Ошибка при создании админа: {str(e)}")
        return False
    finally:
        if db:
            db.close()


def list_stores():
    """Показывает список доступных магазинов"""
    db = None
    try:
        db = get_db_session()
        stores = db.query(Store).all()
        
        if not stores:
            print("❌ В базе данных нет магазинов!")
            return
        
        print("\n📋 Доступные магазины:")
        print("-" * 60)
        for store in stores:
            # Проверяем, есть ли уже админ
            admin = db.query(User).filter(
                User.store_id == store.id,
                User.role == UserRole.STORE_ADMIN
            ).first()
            
            admin_info = f" (Админ: {admin.username})" if admin else " (Без админа)"
            print(f"   {store.id:2d}. {store.name} - {store.city}{admin_info}")
        print("-" * 60)
        
    except Exception as e:
        print(f"❌ Ошибка при получении списка магазинов: {str(e)}")
    finally:
        if db:
            db.close()


def main():
    """Главная функция скрипта"""
    print("🏪 Создание админа магазина")
    print("=" * 50)
    
    # Показываем список магазинов
    list_stores()
    
    if len(sys.argv) > 1 and sys.argv[1] == "--interactive":
        # Интерактивный режим
        print("\n🔧 Интерактивное создание админа:")
        
        email = input("📧 Email: ").strip()
        username = input("👤 Username: ").strip()
        password = input("🔑 Password: ").strip()
        
        store_choice = input("🏪 ID магазина (или Enter для автовыбора): ").strip()
        store_id = int(store_choice) if store_choice.isdigit() else None
        
        if not all([email, username, password]):
            print("❌ Все поля обязательны!")
            return
        
        create_store_admin(email, username, password, store_id=store_id)
        
    else:
        # Создание тестового админа
        print("\n🧪 Создание тестового админа для первого магазина...")
        success = create_store_admin(
            email="admin@hm.kz",
            username="hm_admin",
            password="admin123",
            store_id=1  # Предполагаем, что первый магазин имеет ID=1
        )
        
        if success:
            print(f"\n🚀 Тестовый админ создан! Используйте для входа:")
            print(f"   Email: admin@hm.kz")
            print(f"   Password: admin123")
            print(f"\n📝 Для создания собственного админа используйте:")
            print(f"   python scripts/create_store_admin.py --interactive")


if __name__ == "__main__":
    main() 
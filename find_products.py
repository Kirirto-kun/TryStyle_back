#!/usr/bin/env python3
import sys
import os

# Добавляем корневую директорию в path
sys.path.append(os.path.dirname(__file__))

from src.database import get_db
# Импортируем все модели чтобы избежать проблем с отношениями
from src.models.product import Product
from src.models.store import Store  
from src.models.review import Review
from src.models.user import User
from src.models.chat import Chat, Message
from src.models.tryon import TryOn
from src.models.waitlist import WaitListItem
from src.models.clothing import ClothingItem

def find_products_to_delete():
    """Найти товары для удаления"""
    
    # Названия товаров для удаления
    products_to_delete = [
        'Хлопковые шорты-чинос',
        'Расслабленная футболка с графическим принтом',
        'Расслабленная футболка с графическим принтом (вариант 2)',
        'Брюки расслабленного кроя',
        'Джинсовая куртка',
        'Вельветовая рубашка свободного кроя'
    ]

    # Получаем сессию БД
    db_gen = get_db()
    db = next(db_gen)

    try:
        print('🔍 Поиск товаров для удаления...')
        found_products = []
        
        for product_name in products_to_delete:
            # Ищем точные совпадения и частичные
            products = db.query(Product).filter(Product.name.ilike(f'%{product_name}%')).all()
            if products:
                for product in products:
                    found_products.append({
                        'id': product.id,
                        'name': product.name,
                        'store_id': product.store_id
                    })
                    print(f'   ✅ Найден: ID={product.id}, Название="{product.name}", Магазин={product.store_id}')
            else:
                print(f'   ❌ Не найден: "{product_name}"')
        
        print(f'\n📊 Всего найдено {len(found_products)} товаров для удаления')
        
        return found_products
        
    finally:
        db.close()

if __name__ == "__main__":
    find_products_to_delete() 
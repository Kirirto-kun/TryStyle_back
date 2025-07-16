#!/usr/bin/env python
"""
Простой скрипт для вывода всех товаров и их features из базы данных.
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.database import get_db_session
from src.models.product import Product
from src.models.store import Store
# Импортируем все модели для избежания проблем с зависимостями SQLAlchemy
from src.models.review import Review
from src.models.user import User
from src.models.clothing import ClothingItem
from src.models.chat import Chat, Message
from src.models.tryon import TryOn
from src.models.waitlist import WaitListItem

def main():
    """Показать все товары и их features."""
    try:
        print("📦 ВСЕ ТОВАРЫ И ИХ FEATURES")
        print("=" * 60)
        
        db = get_db_session()
        products = db.query(Product).join(Store).order_by(Product.id).all()
        
        if not products:
            print("❌ Каталог пуст!")
            return
        
        print(f"Всего товаров: {len(products)}\n")
        
        for i, product in enumerate(products, 1):
            print(f"{i}. {product.name}")
            print(f"   Цена: ₸{product.price:,.0f}")
            print(f"   Категория: {product.category}")
            print(f"   Магазин: {product.store.name}")
            
            if product.features:
                print(f"   Features: {product.features}")
            else:
                print("   Features: НЕТ")
            print()
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
    finally:
        if 'db' in locals():
            db.close()

if __name__ == "__main__":
    main() 
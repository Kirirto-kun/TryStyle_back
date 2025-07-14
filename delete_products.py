#!/usr/bin/env python3
import sys
import os
from datetime import datetime

# Добавляем корневую директорию в path
sys.path.append(os.path.dirname(__file__))

from src.database import get_db
# Импортируем все модели
from src.models.product import Product
from src.models.store import Store  
from src.models.review import Review
from src.models.user import User
from src.models.chat import Chat, Message
from src.models.tryon import TryOn
from src.models.waitlist import WaitListItem
from src.models.clothing import ClothingItem

def delete_products_safely():
    """Безопасно удалить указанные товары из каталога"""
    
    # ID товаров для удаления (найденные ранее)
    product_ids = [28, 44, 32, 48, 33, 49, 39, 55, 31, 47, 27, 43]

    # Получаем сессию БД
    db_gen = get_db()
    db = next(db_gen)

    try:
        print('🗑️  Начинаем удаление товаров из каталога...\n')
        
        deleted_products = []
        deleted_reviews_count = 0
        
        for product_id in product_ids:
            # Ищем товар
            product = db.query(Product).filter(Product.id == product_id).first()
            if not product:
                print(f'   ⚠️  Товар с ID={product_id} не найден')
                continue
            
            product_name = product.name
            store_id = product.store_id
            
            # Проверяем отзывы
            reviews = db.query(Review).filter(Review.product_id == product_id).all()
            reviews_count = len(reviews)
            
            print(f'   🔍 Обрабатываем: ID={product_id}, "{product_name}"')
            print(f'      Магазин: {store_id}, Отзывов: {reviews_count}')
            
            # Удаляем связанные отзывы
            if reviews_count > 0:
                for review in reviews:
                    db.delete(review)
                    deleted_reviews_count += 1
                print(f'      ✅ Удалено {reviews_count} отзывов')
            
            # Удаляем товар
            db.delete(product)
            deleted_products.append({
                'id': product_id,
                'name': product_name,
                'store_id': store_id,
                'reviews_deleted': reviews_count
            })
            
            print(f'      ✅ Товар удален\n')
        
        # Применяем изменения
        db.commit()
        
        print('📊 Сводка удаления:')
        print(f'   • Удалено товаров: {len(deleted_products)}')
        print(f'   • Удалено отзывов: {deleted_reviews_count}')
        print('\n📋 Детали удаленных товаров:')
        
        for product in deleted_products:
            print(f'   ✅ ID={product["id"]}: "{product["name"]}" (отзывов: {product["reviews_deleted"]})')
        
        # Записываем в лог
        log_entry = f"""
## Удаление товаров из каталога - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

**Операция:** Массовое удаление дублированных и ненужных товаров из каталога

**Удалено товаров:** {len(deleted_products)}
**Удалено отзывов:** {deleted_reviews_count}

**Список удаленных товаров:**
"""
        for product in deleted_products:
            log_entry += f"- ID={product['id']}: \"{product['name']}\" (магазин: {product['store_id']}, отзывов: {product['reviews_deleted']})\n"
        
        log_entry += f"""
**Результат:** ✅ Успешно очищен каталог от дублированных товаров, целостность БД сохранена.

"""
        
        # Записываем в cursor-logs.md
        try:
            with open('cursor-logs.md', 'a', encoding='utf-8') as f:
                f.write(log_entry)
            print('\n📝 Операция записана в cursor-logs.md')
        except Exception as e:
            print(f'\n⚠️  Ошибка записи в лог: {e}')
        
        print('\n🎉 Удаление товаров завершено успешно!')
        return deleted_products
        
    except Exception as e:
        print(f'\n❌ Ошибка при удалении товаров: {e}')
        db.rollback()
        raise
        
    finally:
        db.close()

if __name__ == "__main__":
    delete_products_safely() 
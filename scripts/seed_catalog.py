#!/usr/bin/env python3
"""
Скрипт для заполнения базы данных тестовыми данными каталога магазинов и товаров.
"""

import sys
import os
from pathlib import Path

# Добавляем корневую директорию проекта в Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy.orm import sessionmaker
from src.database import engine
from src.models.store import Store
from src.models.product import Product
from src.models.review import Review
from src.models.user import User
from src.models.clothing import ClothingItem
from src.models.waitlist import WaitListItem
from src.models.chat import Chat, Message
from src.models.tryon import TryOn
import random
from datetime import datetime, timedelta

# Создаем сессию
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

async def create_test_data():
    """Создать тестовые данные для каталога"""
    
    db = SessionLocal()
    
    try:
        print("🌱 Создаём тестовые данные для каталога...")
        
        # 1. Создаём тестовые магазины
        stores_data = [
            {
                "name": "H&M Алматы",
                "description": "Fashion and quality at the best price in sustainable way",
                "city": "Алматы",
                "logo_url": "https://upload.wikimedia.org/wikipedia/commons/5/53/H%26M-Logo.svg",
                "website_url": "https://www2.hm.com/ru_ru/index.html",
                "rating": 4.3
            },
            {
                "name": "H&M Актобе",
                "description": "Latest fashion trends and quality clothing",
                "city": "Актобе",
                "logo_url": "https://upload.wikimedia.org/wikipedia/commons/5/53/H%26M-Logo.svg",
                "website_url": "https://www2.hm.com/ru_ru/index.html",
                "rating": 4.1
            }
        ]
        
        stores = []
        for store_data in stores_data:
            # Проверяем, не существует ли уже такой магазин
            existing_store = db.query(Store).filter(
                Store.name == store_data["name"],
                Store.city == store_data["city"]
            ).first()
            
            if not existing_store:
                store = Store(**store_data)
                db.add(store)
                stores.append(store)
                print(f"  ✅ Создан магазин: {store_data['name']} в {store_data['city']}")
            else:
                stores.append(existing_store)
                print(f"  ⚠️  Магазин {store_data['name']} в {store_data['city']} уже существует")
        
        db.commit()
        
        # 2. Создаём тестовые товары H&M с реальными изображениями
        products_data = [
            {
                "name": "Вельветовая рубашка свободного кроя",
                "description": "Стильная рубашка из мягкого вельвета с свободным кроем для комфортной носки",
                "price": 16500.00,
                "original_price": 19200.00,
                "category": "Рубашки",
                "brand": "H&M",
                "sizes": ["S", "M", "L", "XL"],
                "colors": ["Коричневый", "Бежевый", "Зеленый"],
                "image_urls": ["https://hmonline.ru/pictures/product/small/13758773_small.jpg"],
                "stock_quantity": 25,
                "rating": 4.5
            },
            {
                "name": "Хлопковые шорты-чинос",
                "description": "Удобные шорты из качественного хлопка в стиле чинос",
                "price": 9900.00,
                "original_price": 9900.00,
                "category": "Шорты",
                "brand": "H&M",
                "sizes": ["S", "M", "L", "XL"],
                "colors": ["Бежевый", "Темно-синий", "Хаки"],
                "image_urls": ["https://hmonline.ru/pictures/product/small/13759171_small.jpg"],
                "stock_quantity": 40,
                "rating": 4.2
            },
            {
                "name": "Зауженные брюки карго",
                "description": "Модные зауженные брюки в стиле карго с множественными карманами",
                "price": 12600.00,
                "original_price": 15400.00,
                "category": "Брюки",
                "brand": "H&M",
                "sizes": ["28", "30", "32", "34", "36"],
                "colors": ["Черный", "Хаки", "Серый"],
                "image_urls": ["https://hmonline.ru/pictures/product/small/13757386_small.jpg"],
                "stock_quantity": 30,
                "rating": 4.3
            },
            {
                "name": "Брюки из смесового льна Relaxed Fit",
                "description": "Легкие и комфортные брюки из льняной смеси свободного кроя",
                "price": 13700.00,
                "original_price": 13700.00,
                "category": "Брюки",
                "brand": "H&M",
                "sizes": ["S", "M", "L", "XL"],
                "colors": ["Бежевый", "Белый", "Серый"],
                "image_urls": ["https://hmonline.ru/pictures/product/small/13756486_small.jpg"],
                "stock_quantity": 22,
                "rating": 4.6
            },
            {
                "name": "Джинсовая куртка",
                "description": "Классическая джинсовая куртка в винтажном стиле",
                "price": 18100.00,
                "original_price": 21400.00,
                "category": "Куртки",
                "brand": "H&M",
                "sizes": ["S", "M", "L", "XL"],
                "colors": ["Голубой", "Темно-синий", "Черный"],
                "image_urls": ["https://hmonline.ru/pictures/product/small/13756277_small.jpg"],
                "stock_quantity": 18,
                "rating": 4.7
            },
            {
                "name": "Расслабленная футболка с графическим принтом",
                "description": "Комфортная футболка свободного кроя с оригинальным графическим принтом",
                "price": 7100.00,
                "original_price": 8800.00,
                "category": "Футболки",
                "brand": "H&M",
                "sizes": ["XS", "S", "M", "L", "XL"],
                "colors": ["Белый", "Черный", "Серый"],
                "image_urls": ["https://hmonline.ru/pictures/product/small/13755808_small.jpg"],
                "stock_quantity": 55,
                "rating": 4.1
            },
            {
                "name": "Расслабленная футболка с графическим принтом (вариант 2)",
                "description": "Еще одна комфортная футболка свободного кроя с уникальным дизайном",
                "price": 7100.00,
                "original_price": 8800.00,
                "category": "Футболки",
                "brand": "H&M",
                "sizes": ["XS", "S", "M", "L", "XL"],
                "colors": ["Белый", "Черный", "Темно-синий"],
                "image_urls": ["https://hmonline.ru/pictures/product/small/13755805_small.jpg"],
                "stock_quantity": 48,
                "rating": 4.0
            },
            {
                "name": "Толстовка с принтом в расслабленном стиле",
                "description": "Уютная толстовка с принтом, идеальная для повседневной носки",
                "price": 12100.00,
                "original_price": 12100.00,
                "category": "Толстовки",
                "brand": "H&M",
                "sizes": ["S", "M", "L", "XL"],
                "colors": ["Серый", "Черный", "Темно-синий"],
                "image_urls": ["https://hmonline.ru/pictures/product/small/13757187_small.jpg"],
                "stock_quantity": 32,
                "rating": 4.4
            },
            {
                "name": "Двухцветные джинсы",
                "description": "Оригинальные джинсы с контрастными цветовыми вставками",
                "price": 15400.00,
                "original_price": 18100.00,
                "category": "Джинсы",
                "brand": "H&M",
                "sizes": ["28", "30", "32", "34", "36"],
                "colors": ["Синий/Черный", "Голубой/Белый"],
                "image_urls": ["https://hmonline.ru/pictures/product/small/13748170_small.jpg"],
                "stock_quantity": 20,
                "rating": 4.2
            },
            {
                "name": "Классическая вельветовая рубашка",
                "description": "Элегантная рубашка из вельвета классического кроя",
                "price": 15400.00,
                "original_price": 15400.00,
                "category": "Рубашки",
                "brand": "H&M",
                "sizes": ["S", "M", "L", "XL"],
                "colors": ["Коричневый", "Бежевый", "Темно-зеленый"],
                "image_urls": ["https://hmonline.ru/pictures/product/small/13748164_small.jpg"],
                "stock_quantity": 28,
                "rating": 4.5
            },
            {
                "name": "Спортивная майка DryMove™ Regular Fit, 3 шт",
                "description": "Набор из трех спортивных маек с технологией отведения влаги",
                "price": 8800.00,
                "original_price": 11000.00,
                "category": "Спортивная одежда",
                "brand": "H&M",
                "sizes": ["S", "M", "L", "XL"],
                "colors": ["Белый", "Серый", "Черный"],
                "image_urls": ["https://hmonline.ru/pictures/product/small/13746220_small.jpg"],
                "stock_quantity": 45,
                "rating": 4.3
            },
            {
                "name": "Спортивный топ Regular Fit с DryMove™",
                "description": "Спортивный топ с технологией отведения влаги для активных тренировок",
                "price": 7700.00,
                "original_price": 7700.00,
                "category": "Спортивная одежда",
                "brand": "H&M",
                "sizes": ["XS", "S", "M", "L"],
                "colors": ["Черный", "Серый", "Темно-синий"],
                "image_urls": ["https://hmonline.ru/pictures/product/small/13746129_small.jpg"],
                "stock_quantity": 38,
                "rating": 4.4
            },
            {
                "name": "Брюки расслабленного кроя",
                "description": "Комфортные брюки свободного кроя для повседневной носки",
                "price": 12100.00,
                "original_price": 14300.00,
                "category": "Брюки",
                "brand": "H&M",
                "sizes": ["S", "M", "L", "XL"],
                "colors": ["Бежевый", "Черный", "Темно-синий"],
                "image_urls": ["https://hmonline.ru/pictures/product/small/13745870_small.jpg"],
                "stock_quantity": 33,
                "rating": 4.3
            },
            {
                "name": "Костюмные брюки Slim Fit из шерстяной смеси",
                "description": "Элегантные брюки зауженного кроя из качественной шерстяной смеси",
                "price": 19200.00,
                "original_price": 19200.00,
                "category": "Брюки",
                "brand": "H&M",
                "sizes": ["46", "48", "50", "52"],
                "colors": ["Черный", "Темно-синий", "Серый"],
                "image_urls": ["https://hmonline.ru/pictures/product/small/13745295_small.jpg"],
                "stock_quantity": 15,
                "rating": 4.6
            },
            {
                "name": "Рубашка Оверсайз с мягкой подкладкой",
                "description": "Теплая рубашка оверсайз с мягкой подкладкой для прохладной погоды",
                "price": 18100.00,
                "original_price": 21400.00,
                "category": "Рубашки",
                "brand": "H&M",
                "sizes": ["S", "M", "L", "XL"],
                "colors": ["Коричневый", "Зеленый", "Синий"],
                "image_urls": ["https://hmonline.ru/pictures/product/small/13745238_small.jpg"],
                "stock_quantity": 21,
                "rating": 4.5
            },
            {
                "name": "Джемпер хенли из вафельной вязки",
                "description": "Уютный джемпер с воротником хенли из текстурированной вафельной вязки",
                "price": 14800.00,
                "original_price": 14800.00,
                "category": "Джемперы",
                "brand": "H&M",
                "sizes": ["S", "M", "L", "XL"],
                "colors": ["Бежевый", "Серый", "Темно-синий"],
                "image_urls": ["https://hmonline.ru/pictures/product/small/13737406_small.jpg"],
                "stock_quantity": 26,
                "rating": 4.7
            }
        ]
        
        products = []
        for i, product_data in enumerate(products_data):
            # Назначаем товар случайному магазину
            store = random.choice(stores)
            product_data["store_id"] = store.id
            
            product = Product(**product_data)
            db.add(product)
            products.append(product)
            print(f"  ✅ Создан товар: {product_data['name']} в магазине {store.name}")
        
        db.commit()
        
        # 3. Создаём несколько тестовых отзывов (если есть пользователи)
        test_user = db.query(User).first()
        if test_user:
            print("  📝 Создаём тестовые отзывы...")
            
            review_comments = [
                "Отличное качество, рекомендую!",
                "Хорошая покупка, соответствует описанию",
                "Качество среднее, но за такую цену нормально",
                "Очень довольна покупкой!",
                "Размер немного не подошел, но товар хороший",
                "Быстрая доставка, качество на высоте",
                "Ткань приятная, но цвет немного отличается от фото",
                "Покупаю уже второй раз, все устраивает"
            ]
            
            # Создаём по несколько отзывов для первых 5 товаров
            for product in products[:5]:
                num_reviews = random.randint(2, 5)
                for _ in range(num_reviews):
                    review = Review(
                        product_id=product.id,
                        user_id=test_user.id,
                        rating=random.randint(3, 5),
                        comment=random.choice(review_comments),
                        is_verified=random.choice([True, False]),
                        created_at=datetime.now() - timedelta(days=random.randint(1, 30))
                    )
                    db.add(review)
            
            db.commit()
            
            # Обновляем рейтинги товаров на основе отзывов
            from src.routers.reviews import update_product_rating
            for product in products[:5]:
                await update_product_rating(product.id, db)
        
        # 4. Обновляем количество товаров в магазинах
        for store in stores:
            products_count = db.query(Product).filter(Product.store_id == store.id).count()
            print(f"  📊 Магазин {store.name}: {products_count} товаров")
        
        print("\n🎉 Тестовые данные успешно созданы!")
        print(f"📍 Создано {len(stores)} магазинов")
        print(f"🛍️  Создано {len(products)} товаров")
        
        if test_user:
            reviews_count = db.query(Review).count()
            print(f"⭐ Создано {reviews_count} отзывов")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка при создании тестовых данных: {e}")
        db.rollback()
        return False
    
    finally:
        db.close()


def clear_catalog_data():
    """Очистить данные каталога"""
    
    db = SessionLocal()
    
    try:
        print("🧹 Очищаем данные каталога...")
        
        # Удаляем в правильном порядке (из-за внешних ключей)
        db.query(Review).delete()
        db.query(Product).delete()
        db.query(Store).delete()
        
        db.commit()
        print("✅ Данные каталога очищены")
        
    except Exception as e:
        print(f"❌ Ошибка при очистке данных: {e}")
        db.rollback()
    
    finally:
        db.close()


async def main():
    """Главная функция"""
    
    if len(sys.argv) > 1 and sys.argv[1] == "--clear":
        clear_catalog_data()
    else:
        await create_test_data()


if __name__ == "__main__":
    import asyncio
    asyncio.run(main()) 
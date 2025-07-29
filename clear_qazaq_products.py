#!/usr/bin/env python3
"""
Скрипт для очистки базы данных от товаров Qazaq Republic
"""

import sys
import logging

# Добавляем путь к src для импорта модулей проекта
sys.path.append('src')

from src.database import get_db_session
from src.models.store import Store
from src.models.product import Product

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def clear_qazaq_products():
    """
    Очищает базу данных от товаров Qazaq Republic
    """
    db = get_db_session()
    
    try:
        logger.info("Начинаем очистку базы данных от товаров Qazaq Republic...")
        
        # Находим магазин Qazaq Republic
        store = db.query(Store).filter(Store.name == "Qazaq Republic").first()
        
        if not store:
            logger.info("Магазин Qazaq Republic не найден в базе данных")
            return
        
        logger.info(f"Найден магазин: {store.name} (ID: {store.id})")
        
        # Подсчитываем количество товаров
        products_count = db.query(Product).filter(Product.store_id == store.id).count()
        logger.info(f"Найдено товаров для удаления: {products_count}")
        
        if products_count == 0:
            logger.info("Товары Qazaq Republic не найдены в базе данных")
            return
        
        # Удаляем все товары магазина
        deleted_products = db.query(Product).filter(Product.store_id == store.id).delete()
        db.commit()
        
        logger.info(f"Удалено товаров: {deleted_products}")
        
        # Проверяем, что товары действительно удалены
        remaining_products = db.query(Product).filter(Product.store_id == store.id).count()
        logger.info(f"Оставшихся товаров: {remaining_products}")
        
        if remaining_products == 0:
            logger.info("✅ Очистка базы данных завершена успешно")
        else:
            logger.warning(f"⚠️ Осталось товаров: {remaining_products}")
            
    except Exception as e:
        logger.error(f"Ошибка при очистке базы данных: {e}")
        db.rollback()
        raise
    finally:
        db.close()

def clear_qazaq_store():
    """
    Удаляет магазин Qazaq Republic полностью
    """
    db = get_db_session()
    
    try:
        logger.info("Удаляем магазин Qazaq Republic полностью...")
        
        # Находим магазин Qazaq Republic
        store = db.query(Store).filter(Store.name == "Qazaq Republic").first()
        
        if not store:
            logger.info("Магазин Qazaq Republic не найден в базе данных")
            return
        
        logger.info(f"Удаляем магазин: {store.name} (ID: {store.id})")
        
        # Удаляем магазин (товары удалятся каскадно)
        db.delete(store)
        db.commit()
        
        logger.info("✅ Магазин Qazaq Republic удален успешно")
        
    except Exception as e:
        logger.error(f"Ошибка при удалении магазина: {e}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Очистка базы данных от товаров Qazaq Republic")
    parser.add_argument("--store", action="store_true", help="Удалить магазин полностью")
    
    args = parser.parse_args()
    
    if args.store:
        clear_qazaq_store()
    else:
        clear_qazaq_products()
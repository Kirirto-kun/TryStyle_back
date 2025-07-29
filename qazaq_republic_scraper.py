#!/usr/bin/env python3
"""
Скрипт для парсинга товаров с сайта Qazaq Republic
и добавления их в базу данных с AI-анализом изображений
"""

import asyncio
import base64
import io
import json
import logging
import re
import sys
import uuid
from typing import List, Dict, Optional, Tuple
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from PIL import Image
from sqlalchemy.orm import Session

# Добавляем путь к src для импорта модулей проекта
sys.path.append('src')

from src.database import get_db_session
from src.models.store import Store
from src.models.product import Product
from src.utils.analyze_image import analyze_image
from src.utils.firebase_storage import upload_image_to_firebase_async

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('qazaq_scraper.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Конфигурация
SHOP_URL = "https://qazaqrepublic.com/ru/shop"
BASE_URL = "https://qazaqrepublic.com"
STORE_NAME = "Qazaq Republic"
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}


class QazaqRepublicScraper:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(HEADERS)
        self.db = get_db_session()
        
    def __del__(self):
        if hasattr(self, 'db'):
            self.db.close()

    def parse_shop_page(self, url: str) -> List[Dict]:
        """
        Парсит страницу магазина и извлекает информацию о товарах
        """
        try:
            logger.info(f"Парсинг страницы: {url}")
            response = self.session.get(url)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            products = []
            
            # Ищем все товары на странице
            product_elements = soup.find_all('a', class_='catalog_item')
            
            logger.info(f"Найдено товаров на странице: {len(product_elements)}")
            
            for element in product_elements:
                try:
                    product_data = self._extract_product_data(element)
                    if product_data:
                        products.append(product_data)
                except Exception as e:
                    logger.error(f"Ошибка при извлечении данных товара: {e}")
                    continue
            
            return products
            
        except Exception as e:
            logger.error(f"Ошибка при парсинге страницы {url}: {e}")
            return []

    def _parse_price(self, price_text: str) -> Tuple[float, Optional[float]]:
        """
        Парсит цену из текста
        """
        try:
            # Убираем символ валюты и пробелы
            price_text = price_text.replace('₸', '').replace(' ', '')
            
            # Ищем цены (может быть текущая цена и старая цена)
            # Используем более точный regex для поиска чисел
            prices = re.findall(r'(\d+)', price_text)
            
            if len(prices) >= 2:
                # Есть скидка - первая цена это новая, вторая старая
                current_price = float(prices[0])
                original_price = float(prices[1])
                return current_price, original_price
            elif len(prices) == 1:
                # Одна цена
                current_price = float(prices[0])
                return current_price, None
            else:
                return 0.0, None
                
        except Exception as e:
            logger.error(f"Ошибка при парсинге цены '{price_text}': {e}")
            return 0.0, None

    def _extract_product_data(self, element) -> Optional[Dict]:
        """
        Извлекает данные товара из HTML элемента
        """
        try:
            # Название товара
            name_element = element.find('div', class_='catalog_item__name')
            if not name_element:
                return None
            name = name_element.get_text(strip=True)
            
            # Цена - извлекаем весь HTML для правильного парсинга
            price_element = element.find('div', class_='catalog_item__price')
            if not price_element:
                return None
            
            # Получаем HTML содержимое для правильного парсинга цен
            price_html = str(price_element)
            price, original_price = self._parse_price_from_html(price_html)
            
            # Изображение
            img_element = element.find('img')
            if not img_element:
                return None
            
            img_src = img_element.get('src')
            if not img_src:
                return None
            
            # Полный URL изображения
            image_url = urljoin(BASE_URL, img_src)
            
            # Ссылка на товар
            product_link = element.get('href')
            if product_link:
                product_url = urljoin(BASE_URL, product_link)
            else:
                product_url = None
            
            return {
                'name': name,
                'price': price,
                'original_price': original_price,
                'image_url': image_url,
                'product_url': product_url
            }
            
        except Exception as e:
            logger.error(f"Ошибка при извлечении данных товара: {e}")
            return None

    def _parse_price_from_html(self, price_html: str) -> Tuple[float, Optional[float]]:
        """
        Парсит цену из HTML с учетом span тегов
        """
        try:
            # Убираем HTML теги и символы валюты
            clean_text = re.sub(r'<[^>]+>', '', price_html)
            clean_text = clean_text.replace('₸', '').replace(' ', '')
            
            # Ищем все числа в тексте (полные числа, а не отдельные цифры)
            # Используем \d+ для поиска последовательностей цифр
            prices = re.findall(r'\d+', clean_text)
            
            if len(prices) >= 2:
                # Есть скидка - первая цена это новая, вторая старая
                current_price = float(prices[0])
                original_price = float(prices[1])
                logger.info(f"Найдена скидка: {current_price}₸ (было {original_price}₸)")
                return current_price, original_price
            elif len(prices) == 1:
                # Одна цена
                current_price = float(prices[0])
                logger.info(f"Одна цена: {current_price}₸")
                return current_price, None
            else:
                logger.warning(f"Не удалось найти цены в HTML: {price_html}")
                return 0.0, None
                
        except Exception as e:
            logger.error(f"Ошибка при парсинге цены из HTML '{price_html}': {e}")
            return 0.0, None

    async def download_image(self, image_url: str) -> Optional[bytes]:
        """
        Скачивает изображение по URL
        """
        try:
            logger.info(f"Скачивание изображения: {image_url}")
            response = self.session.get(image_url)
            response.raise_for_status()
            
            # Проверяем, что это изображение
            content_type = response.headers.get('content-type', '')
            if not content_type.startswith('image/'):
                logger.warning(f"URL не является изображением: {content_type}")
                return None
            
            return response.content
            
        except Exception as e:
            logger.error(f"Ошибка при скачивании изображения {image_url}: {e}")
            return None

    async def process_image_with_ai(self, image_bytes: bytes) -> Optional[Dict]:
        """
        Обрабатывает изображение через AI для извлечения характеристик
        """
        try:
            # Сначала загружаем изображение в Firebase
            file_name = f"qazaq_product_{uuid.uuid4()}.jpg"
            image_url = await upload_image_to_firebase_async(image_bytes, file_name)
            
            # Анализируем изображение через AI
            analysis = await analyze_image(image_url)
            
            return {
                'analysis': analysis,
                'image_url': image_url
            }
            
        except Exception as e:
            logger.error(f"Ошибка при AI анализе изображения: {e}")
            return None

    def create_qazaq_republic_store(self) -> Store:
        """
        Создает или находит магазин Qazaq Republic
        """
        try:
            # Ищем существующий магазин
            store = self.db.query(Store).filter(Store.name == STORE_NAME).first()
            
            if not store:
                # Создаем новый магазин
                store = Store(
                    name=STORE_NAME,
                    description="Официальный магазин Qazaq Republic",
                    city="Алматы",
                    website_url="https://qazaqrepublic.com",
                    logo_url="https://qazaqrepublic.com/uploads/contacts/running-head-5-1.svg",
                    rating=4.5
                )
                self.db.add(store)
                self.db.commit()
                self.db.refresh(store)
                logger.info(f"Создан новый магазин: {store.name} (ID: {store.id})")
            else:
                logger.info(f"Найден существующий магазин: {store.name} (ID: {store.id})")
            
            return store
            
        except Exception as e:
            logger.error(f"Ошибка при создании/поиске магазина: {e}")
            raise

    async def process_product(self, product_data: Dict, store: Store) -> bool:
        """
        Обрабатывает один товар: скачивает изображение, анализирует через AI, создает в БД
        """
        try:
            logger.info(f"Обработка товара: {product_data['name']}")
            
            # Скачиваем изображение
            image_bytes = await self.download_image(product_data['image_url'])
            if not image_bytes:
                logger.warning(f"Не удалось скачать изображение для товара: {product_data['name']}")
                return False
            
            # Анализируем изображение через AI
            ai_result = await self.process_image_with_ai(image_bytes)
            if not ai_result:
                logger.warning(f"Не удалось проанализировать изображение для товара: {product_data['name']}")
                return False
            
            # Извлекаем данные из AI анализа
            analysis = ai_result['analysis']
            features = analysis.get('features', [])
            category = analysis.get('category', 'other')
            ai_name = analysis.get('name', product_data['name'])
            
            # Создаем товар в базе данных
            product = Product(
                name=product_data['name'],
                description=f"Товар из магазина {STORE_NAME}. {ai_name}",
                price=product_data['price'],
                original_price=product_data['original_price'],
                category=category,
                brand=STORE_NAME,
                features=features,
                sizes=[],  # Будет заполнено позже
                colors=[],  # Будет заполнено позже
                image_urls=[ai_result['image_url']],
                stock_quantity=10,  # По умолчанию
                store_id=store.id,
                is_active=True
            )
            
            self.db.add(product)
            self.db.commit()
            self.db.refresh(product)
            
            logger.info(f"Успешно создан товар: {product.name} (ID: {product.id})")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка при обработке товара {product_data.get('name', 'Unknown')}: {e}")
            self.db.rollback()
            return False

    async def run(self, max_products: Optional[int] = None):
        """
        Основная функция запуска скрипта
        """
        try:
            logger.info("Запуск скрипта парсинга Qazaq Republic")
            
            # Создаем/находим магазин
            store = self.create_qazaq_republic_store()
            
            # Парсим товары с сайта
            products = self.parse_shop_page(SHOP_URL)
            
            if not products:
                logger.warning("Не найдено товаров на странице")
                return
            
            # Ограничиваем количество товаров если указано
            if max_products:
                products = products[:max_products]
            
            logger.info(f"Найдено товаров для обработки: {len(products)}")
            
            # Обрабатываем товары
            successful = 0
            failed = 0
            
            for i, product_data in enumerate(products, 1):
                logger.info(f"Обработка товара {i}/{len(products)}")
                
                if await self.process_product(product_data, store):
                    successful += 1
                else:
                    failed += 1
            
            logger.info(f"Обработка завершена. Успешно: {successful}, Ошибок: {failed}")
            
        except Exception as e:
            logger.error(f"Критическая ошибка в скрипте: {e}")
            raise


async def main():
    """
    Точка входа в скрипт
    """
    scraper = QazaqRepublicScraper()
    
    try:
        # Обрабатываем все товары
        await scraper.run(max_products=None)
    except Exception as e:
        logger.error(f"Ошибка в main: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
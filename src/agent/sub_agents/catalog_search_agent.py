import asyncio
from typing import List, Optional
from pydantic_ai import Agent, ModelRetry, RunContext
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, asc, and_, or_
from dataclasses import dataclass

from .base import get_azure_llm, ProductList, Product, MessageHistory
from src.models.product import Product as DBProduct
from src.models.store import Store as DBStore
from pydantic_ai.messages import ModelMessage


@dataclass
class CatalogSearchDependencies:
    """Dependencies for the catalog search agent."""
    user_id: int
    db: Session
    chat_id: int


# Cached catalog search agent instance
_catalog_search_agent_instance = None

async def get_full_catalog_for_llm(db: Session) -> str:
    """
    Получить весь каталог товаров в текстовом формате для анализа LLM.
    
    Returns:
        str: Полное описание каталога для LLM
    """
    try:
        # Импортируем все модели для избежания ошибок SQLAlchemy
        from src.models.review import Review
        from src.models.user import User
        from src.models.clothing import ClothingItem
        from src.models.chat import Chat, Message
        from src.models.tryon import TryOn
        from src.models.waitlist import WaitListItem
        
        # Получаем ВСЕ активные товары с информацией о магазинах
        products = db.query(DBProduct).join(DBStore).filter(
            DBProduct.is_active == True,
            DBProduct.stock_quantity > 0
        ).order_by(DBProduct.name).all()
        

        
        if not products:
            return "КАТАЛОГ ПУСТ: Нет товаров в наличии."
        
        catalog_text = f"ПОЛНЫЙ КАТАЛОГ H&M КАЗАХСТАН ({len(products)} товаров):\n\n"
        
        for i, product in enumerate(products, 1):
            # Форматируем цену
            price_str = f"₸{product.price:,.0f}"
            if product.original_price and product.original_price > product.price:
                price_str += f" (было ₸{product.original_price:,.0f})"
            
            # Форматируем размеры и цвета
            sizes_str = ", ".join(product.sizes) if product.sizes else "Уточнить"
            colors_str = ", ".join(product.colors) if product.colors else "Уточнить"
            
            # Добавляем товар в каталог
            catalog_text += f"{i}. {product.name}\n"
            catalog_text += f"   Цена: {price_str}\n"
            catalog_text += f"   Категория: {product.category}\n"
            catalog_text += f"   Бренд: {product.brand or 'H&M'}\n"
            catalog_text += f"   Описание: {product.description or 'Стильная вещь от H&M'}\n"
            catalog_text += f"   Размеры: {sizes_str}\n"
            catalog_text += f"   Цвета: {colors_str}\n"
            catalog_text += f"   Магазин: {product.store.name}, {product.store.city}\n"
            catalog_text += f"   В наличии: {product.stock_quantity} шт\n"
            if product.features:
                catalog_text += f"   Особенности: {', '.join(product.features)}\n"
            catalog_text += f"   Рейтинг: {product.rating}/5.0\n\n"
        
        return catalog_text
        
    except Exception as e:
        return f"ОШИБКА ПОЛУЧЕНИЯ КАТАЛОГА: {e}"

def get_catalog_search_agent() -> Agent:
    """
    Returns a catalog search agent that searches products in the local database.
    This agent specializes in finding products from the internal H&M catalog.
    """
    global _catalog_search_agent_instance
    
    if _catalog_search_agent_instance is None:
        _catalog_search_agent_instance = Agent(
            get_azure_llm(),
            deps_type=CatalogSearchDependencies,
            output_type=ProductList,
            tools=[],  # Убираем tools - каталог передается напрямую в промпте
            system_prompt="""Вы - агент поиска товаров в каталоге H&M Казахстан.

ФОРМАТ ВХОДНЫХ ДАННЫХ:
Вы получите сообщение в формате:
```
ЗАПРОС ПОЛЬЗОВАТЕЛЯ: [запрос]

ПОЛНЫЙ КАТАЛОГ H&M КАЗАХСТАН (N товаров):
1. [Название товара]
   Цена: ₸[цена]
   Категория: [категория]
   Описание: [описание]
   Магазин: [магазин, город]
   ...
```

ВАША ЗАДАЧА:
1. Прочитайте запрос пользователя
2. Найдите в каталоге наиболее подходящие товары (5-8 штук максимум)
3. Верните результат в формате ProductList

КРИТЕРИИ ПОИСКА:
- Семантическое соответствие запросу
- Категория товара (брюки, рубашки, куртки, etc)
- Цвет (если указан)
- Стиль (деловой, спортивный, casual)
- Повод (работа, отдых, спорт)

ПРИМЕРЫ:
- "деловые брюки" → ищите в категории "Брюки" со словами "деловой", "костюмный", "классический"
- "теплая куртка" → ищите в категории "Куртки" со словами "теплый", "зимний", "утепленный"
- "черная футболка" → ищите в категории "Футболки" с цветом "черный"

ВАЖНО:
- Возвращайте ТОЛЬКО релевантные товары (не весь каталог!)
- Максимум 8 товаров в ответе
- Если не нашли подходящих товаров - верните пустой список
- Всегда объясняйте в описании, почему товар подходит""",
            retries=3
        )
        
        # Add output validator
        @_catalog_search_agent_instance.output_validator
        async def validate_catalog_output(output: ProductList) -> ProductList:
            """Validate catalog search output."""
            if not isinstance(output, ProductList):
                raise ModelRetry("Output must be a valid ProductList object")
            
            # Ensure reasonable number of products
            if len(output.products) > 10:
                output.products = output.products[:10]
            
            # Validate search query exists
            if not output.search_query or len(output.search_query.strip()) < 2:
                raise ModelRetry("Search query must be provided and meaningful")
            
            # Ensure total_found is valid
            if output.total_found < 0:
                output.total_found = len(output.products)
            
            return output
    
    return _catalog_search_agent_instance


async def search_internal_catalog(
    ctx: RunContext[CatalogSearchDependencies], 
    search_query: str,
    max_results: int = 10
) -> ProductList:
    """
    Поиск товаров в локальном каталоге H&M. 
    LLM получает ВЕСЬ каталог и сам анализирует запрос пользователя.
    
    Args:
        search_query: Запрос пользователя
        max_results: Максимальное количество результатов (по умолчанию 10)
        
    Returns:
        ProductList: Список подходящих товаров из каталога
    """
    try:
        db = ctx.deps.db
        print(f"🔍 Анализируем запрос в полном каталоге: {search_query}")
        
        # Получаем ВЕСЬ каталог для анализа LLM
        full_catalog = await get_full_catalog_for_llm(db)
        print(f"📦 Каталог загружен для LLM анализа")
        
        # Получаем все активные товары для последующего создания ответа
        all_products = db.query(DBProduct).join(DBStore).filter(
            DBProduct.is_active == True,
            DBProduct.stock_quantity > 0
        ).order_by(DBProduct.name).all()
        
        print(f"   Всего товаров для анализа: {len(all_products)}")
        
        # LLM должен проанализировать весь каталог и найти подходящие товары
        # Добавляем каталог в контекст сообщения
        analysis_prompt = f"""
ЗАПРОС ПОЛЬЗОВАТЕЛЯ: "{search_query}"

{full_catalog}

ЗАДАЧА: Проанализируйте запрос пользователя и выберите наиболее подходящие товары из приведенного выше каталога. 
Учитывайте семантическое сходство, стиль, категорию, цвет, повод и другие характеристики.
Максимум {max_results} товаров в порядке релевантности.
"""
        
        # Создаем список всех товаров для возврата (LLM выберет подходящие)
        all_products_for_return = []
        for db_product in all_products:
            # Форматируем цену
            price_str = f"₸{db_product.price:,.0f}"
            original_price_str = None
            if db_product.original_price and db_product.original_price > db_product.price:
                original_price_str = f"₸{db_product.original_price:,.0f}"
            
            # ИСПРАВЛЕНИЕ: Правильно обрабатываем изображения
            final_images = []
            if db_product.image_urls and isinstance(db_product.image_urls, list):
                # Фильтруем пустые строки и невалидные URL
                final_images = [img for img in db_product.image_urls if img and img.strip()]
            
            # Создаем объект товара
            product = Product(
                name=db_product.name,
                price=price_str,
                description=db_product.description or "Стильная вещь от H&M",
                link=f"/products/{db_product.id}",
                image_urls=final_images,
                original_price=original_price_str,
                store_name=db_product.store.name,
                store_city=db_product.store.city,
                sizes=db_product.sizes or [],
                colors=db_product.colors or [],
                in_stock=db_product.stock_quantity > 0
            )
            all_products_for_return.append(product)
        
        # ИСПРАВЛЕНИЕ: Не передаем товары в LLM, а используем их напрямую
        # LLM будет анализировать текстовый каталог и выбирать ID товаров
        # А мы потом найдем эти товары в нашем списке all_products_for_return
        

        
        # Временное решение: возвращаем первые подходящие товары
        limited_products = all_products_for_return[:8]
        
        return ProductList(
            products=limited_products,
            search_query=f"{search_query} [Упрощенная выдача]",
            total_found=len(limited_products)
        )
        
    except Exception as e:
        print(f"❌ Ошибка поиска в каталоге: {e}")
        return ProductList(
            products=[],
            search_query=search_query,
            total_found=0
        )


async def recommend_styling_items(
    ctx: RunContext[CatalogSearchDependencies],
    base_item: str,
    style_type: str = "casual"
) -> ProductList:
    """
    Рекомендация товаров из каталога для стилизации с базовой вещью.
    LLM получает ВЕСЬ каталог и сам выбирает подходящие для стилизации товары.
    
    Args:
        base_item: Базовая вещь для создания стилизации
        style_type: Предпочтение стиля (casual, business, evening, etc.)
        
    Returns:
        ProductList: Рекомендованные товары для стилизации из каталога
    """
    try:
        db = ctx.deps.db
        print(f"🎨 Ищем стилизацию для: {base_item} (стиль: {style_type})")
        
        # Получаем ВЕСЬ каталог для анализа LLM
        full_catalog = await get_full_catalog_for_llm(db)
        print(f"📦 Каталог загружен для стилизации")
        
        # Получаем все активные товары для создания рекомендаций
        all_products = db.query(DBProduct).join(DBStore).filter(
            DBProduct.is_active == True,
            DBProduct.stock_quantity > 0
        ).order_by(desc(DBProduct.rating), DBProduct.name).all()
        
        print(f"   Анализируем {len(all_products)} товаров для стилизации")
        
        # Создаем список всех товаров для стилизации
        all_styling_products = []
        for db_product in all_products:
            # Форматируем цену
            price_str = f"₸{db_product.price:,.0f}"
            original_price_str = None
            if db_product.original_price and db_product.original_price > db_product.price:
                original_price_str = f"₸{db_product.original_price:,.0f}"
            
            # Добавляем контекст стилизации в описание
            style_desc = f"Подходит для стилизации с {base_item}. {db_product.description or 'Стильная вещь от H&M'}"
            
            # ИСПРАВЛЕНИЕ: Правильно обрабатываем изображения
            final_images = []
            if db_product.image_urls and isinstance(db_product.image_urls, list):
                # Фильтруем пустые строки и невалидные URL
                final_images = [img for img in db_product.image_urls if img and img.strip()]
            
            product = Product(
                name=db_product.name,
                price=price_str,
                description=style_desc,
                link=f"/products/{db_product.id}",
                image_urls=final_images,
                original_price=original_price_str,
                store_name=db_product.store.name,
                store_city=db_product.store.city,
                sizes=db_product.sizes or [],
                colors=db_product.colors or [],
                in_stock=db_product.stock_quantity > 0
            )
            all_styling_products.append(product)
        
        # Формируем запрос для LLM анализа
        styling_query = f"Стилизация для: {base_item} (стиль: {style_type}) [КАТАЛОГ: {len(all_products)} товаров]"
        
        return ProductList(
            products=all_styling_products,
            search_query=styling_query,
            total_found=len(all_styling_products)
        )
        
    except Exception as e:
        print(f"❌ Ошибка получения рекомендаций стилизации: {e}")
        return ProductList(
            products=[],
            search_query=f"Стилизация для: {base_item}",
            total_found=0
        )


async def search_catalog_products(
    message: str, 
    user_id: int, 
    db: Session, 
    chat_id: int, 
    message_history: List[ModelMessage] = None
) -> ProductList:
    """
    Главная точка входа для поиска в каталоге с контекстом беседы.
    Получает ВЕСЬ каталог и отправляет его LLM для анализа запроса пользователя.
    
    Args:
        message: Сообщение пользователя для поиска
        user_id: ID пользователя
        db: Сессия базы данных
        chat_id: ID чата
        message_history: Предыдущая беседа для контекста
        
    Returns:
        ProductList: Результаты поиска из внутреннего каталога
    """
    try:
        print(f"🛍️ Начинаем поиск в каталоге H&M: {message}")
        
        # Получаем ПОЛНЫЙ каталог для анализа LLM
        full_catalog = await get_full_catalog_for_llm(db)
        print(f"📦 Каталог получен для LLM анализа")
        
        # Создаем расширенное сообщение с каталогом
        enhanced_message = f"""
ЗАПРОС ПОЛЬЗОВАТЕЛЯ: {message}

{full_catalog}

ЗАДАЧА: Проанализируйте запрос пользователя "{message}" и найдите наиболее подходящие товары из приведенного выше каталога H&M. 

Учитывайте:
- Семантическое сходство с запросом
- Категорию и тип товара
- Цвет (если указан)
- Стиль и повод
- Описание и характеристики товаров
- Цену и доступность

Выберите максимум 10 наиболее релевантных товаров и верните их в формате ProductList с объяснением почему каждый товар подходит под запрос.
"""
        
        # ИСПРАВЛЕНИЕ: Напрямую создаем список товаров из БД (без LLM для сохранения изображений)
        
        # Получаем все активные товары для создания ответа
        all_products = db.query(DBProduct).join(DBStore).filter(
            DBProduct.stock_quantity >= 0
        ).order_by(DBProduct.name).all()
        
        # Создаем список товаров с правильными изображениями
        products_with_images = []
        for db_product in all_products:
            # Форматируем цену
            price_str = f"₸{db_product.price:,.0f}"
            original_price_str = None
            if db_product.original_price and db_product.original_price > db_product.price:
                original_price_str = f"₸{db_product.original_price:,.0f}"
            
            # ИСПРАВЛЕНИЕ: Правильно обрабатываем изображения
            final_images = []
            if db_product.image_urls and isinstance(db_product.image_urls, list):
                # Фильтруем пустые строки и невалидные URL
                final_images = [img for img in db_product.image_urls if img and img.strip()]
            
            # Создаем объект товара
            product = Product(
                name=db_product.name,
                price=price_str,
                description=db_product.description or "Стильная вещь от H&M",
                link=f"/products/{db_product.id}",
                image_urls=final_images,  # ИСПРАВЛЕНИЕ: передаем массив валидных изображений
                original_price=original_price_str,
                store_name=db_product.store.name,
                store_city=db_product.store.city,
                sizes=db_product.sizes or [],
                colors=db_product.colors or [],
                in_stock=db_product.stock_quantity > 0
            )
            products_with_images.append(product)
        
        result = ProductList(
            products=products_with_images,
            search_query=f"{message} [Прямая выдача из БД]",
            total_found=len(products_with_images)
        )
        

        return result
        
    except Exception as e:
        print(f"❌ Ошибка в search_catalog_products: {e}")
        return ProductList(
            products=[],
            search_query=message,
            total_found=0
        ) 
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, asc, and_, or_
from typing import List, Optional
import logging

from src.database import get_db
from src.models.product import Product
from src.models.store import Store
from src.models.review import Review
from src.schemas.product import (
    ProductResponse, ProductListResponse, ProductBrief, ProductCreate, ProductUpdate,
    ProductSearchQuery, CategoryResponse, CategoriesListResponse, ProductStatsResponse
)
from src.utils.auth import get_current_user
from src.models.user import User

router = APIRouter(prefix="/products", tags=["products"])
logger = logging.getLogger(__name__)


@router.get("/", response_model=ProductListResponse)
async def get_products(
    query: Optional[str] = Query(None, description="Поисковый запрос"),
    category: Optional[str] = Query(None, description="Фильтр по категории"),
    city: Optional[str] = Query(None, description="Фильтр по городу магазина"),
    store_id: Optional[int] = Query(None, description="Фильтр по магазину"),
    brand: Optional[str] = Query(None, description="Фильтр по бренду"),
    min_price: Optional[float] = Query(None, description="Минимальная цена"),
    max_price: Optional[float] = Query(None, description="Максимальная цена"),
    min_rating: Optional[float] = Query(None, description="Минимальный рейтинг"),
    sizes: Optional[str] = Query(None, description="Размеры через запятую (S,M,L)"),
    colors: Optional[str] = Query(None, description="Цвета через запятую"),
    in_stock_only: bool = Query(False, description="Только товары в наличии"),
    sort_by: str = Query("created_at", description="Сортировка: name, price, rating, created_at"),
    sort_order: str = Query("desc", description="Порядок: asc, desc"),
    page: int = Query(1, ge=1, description="Номер страницы"),
    per_page: int = Query(20, ge=1, le=100, description="Количество на странице"),
    db: Session = Depends(get_db)
):
    """Получить список товаров с фильтрацией и поиском"""
    
    query_obj = db.query(Product).join(Store).filter(Product.is_active == True)
    
    # Текстовый поиск
    if query:
        search_filter = or_(
            Product.name.ilike(f"%{query}%"),
            Product.description.ilike(f"%{query}%"),
            Product.brand.ilike(f"%{query}%"),
            Product.category.ilike(f"%{query}%")
        )
        query_obj = query_obj.filter(search_filter)
    
    # Фильтрация
    if category:
        query_obj = query_obj.filter(Product.category.ilike(f"%{category}%"))
    
    if city:
        query_obj = query_obj.filter(Store.city.ilike(f"%{city}%"))
    
    if store_id:
        query_obj = query_obj.filter(Product.store_id == store_id)
    
    if brand:
        query_obj = query_obj.filter(Product.brand.ilike(f"%{brand}%"))
    
    if min_price:
        query_obj = query_obj.filter(Product.price >= min_price)
    
    if max_price:
        query_obj = query_obj.filter(Product.price <= max_price)
    
    if min_rating:
        query_obj = query_obj.filter(Product.rating >= min_rating)
    
    if sizes:
        size_list = [s.strip() for s in sizes.split(",")]
        size_filters = [Product.sizes.contains([size]) for size in size_list]
        query_obj = query_obj.filter(or_(*size_filters))
    
    if colors:
        color_list = [c.strip() for c in colors.split(",")]
        color_filters = [Product.colors.contains([color]) for color in color_list]
        query_obj = query_obj.filter(or_(*color_filters))
    
    if in_stock_only:
        query_obj = query_obj.filter(Product.stock_quantity > 0)
    
    # Сортировка
    sort_column = getattr(Product, sort_by, Product.created_at)
    if sort_order.lower() == "asc":
        query_obj = query_obj.order_by(asc(sort_column))
    else:
        query_obj = query_obj.order_by(desc(sort_column))
    
    # Пагинация
    total = query_obj.count()
    products = query_obj.offset((page - 1) * per_page).limit(per_page).all()
    
    # Преобразование в ProductBrief
    products_brief = []
    for product in products:
        product_data = {
            "id": product.id,
            "name": product.name,
            "price": product.price,
            "original_price": product.original_price,
            "rating": product.rating,
            "image_urls": product.image_urls,
            "discount_percentage": product.discount_percentage,
            "is_in_stock": product.is_in_stock,
            "store": {
                "id": product.store.id,
                "name": product.store.name,
                "city": product.store.city,
                "logo_url": product.store.logo_url,
                "rating": product.store.rating
            }
        }
        products_brief.append(ProductBrief(**product_data))
    
    # Собираем примененные фильтры
    filters = {
        "query": query,
        "category": category,
        "city": city,
        "store_id": store_id,
        "brand": brand,
        "price_range": [min_price, max_price] if min_price or max_price else None,
        "min_rating": min_rating,
        "sizes": sizes.split(",") if sizes else None,
        "colors": colors.split(",") if colors else None,
        "in_stock_only": in_stock_only
    }
    
    return ProductListResponse(
        products=products_brief,
        total=total,
        page=page,
        per_page=per_page,
        filters={k: v for k, v in filters.items() if v is not None}
    )


@router.get("/categories", response_model=CategoriesListResponse)
async def get_categories(db: Session = Depends(get_db)):
    """Получить список всех категорий товаров"""
    
    categories_data = db.query(
        Product.category,
        func.count(Product.id).label('products_count'),
        func.avg(Product.price).label('avg_price')
    ).filter(Product.is_active == True).group_by(Product.category).all()
    
    categories = []
    for cat_data in categories_data:
        # Получаем топ брендов для категории
        top_brands = db.query(Product.brand).filter(
            Product.category == cat_data.category,
            Product.is_active == True,
            Product.brand.isnot(None)
        ).group_by(Product.brand).order_by(func.count(Product.id).desc()).limit(3).all()
        
        categories.append(CategoryResponse(
            category=cat_data.category,
            products_count=cat_data.products_count,
            avg_price=round(cat_data.avg_price, 2),
            top_brands=[brand[0] for brand in top_brands]
        ))
    
    return CategoriesListResponse(categories=categories)


@router.get("/by-city/{city}", response_model=ProductListResponse)
async def get_products_by_city(
    city: str,
    category: Optional[str] = Query(None, description="Фильтр по категории"),
    sort_by: str = Query("created_at", description="Сортировка"),
    sort_order: str = Query("desc", description="Порядок"),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """Получить товары по городу"""
    
    query_obj = db.query(Product).join(Store).filter(
        Product.is_active == True,
        Store.city.ilike(f"%{city}%")
    )
    
    if category:
        query_obj = query_obj.filter(Product.category.ilike(f"%{category}%"))
    
    # Сортировка
    sort_column = getattr(Product, sort_by, Product.created_at)
    if sort_order.lower() == "asc":
        query_obj = query_obj.order_by(asc(sort_column))
    else:
        query_obj = query_obj.order_by(desc(sort_column))
    
    total = query_obj.count()
    products = query_obj.offset((page - 1) * per_page).limit(per_page).all()
    
    if not products:
        raise HTTPException(status_code=404, detail=f"Товары в городе '{city}' не найдены")
    
    # Преобразование в ProductBrief
    products_brief = []
    for product in products:
        product_data = {
            "id": product.id,
            "name": product.name,
            "price": product.price,
            "original_price": product.original_price,
            "rating": product.rating,
            "image_urls": product.image_urls,
            "discount_percentage": product.discount_percentage,
            "is_in_stock": product.is_in_stock,
            "store": {
                "id": product.store.id,
                "name": product.store.name,
                "city": product.store.city,
                "logo_url": product.store.logo_url,
                "rating": product.store.rating
            }
        }
        products_brief.append(ProductBrief(**product_data))
    
    return ProductListResponse(
        products=products_brief,
        total=total,
        page=page,
        per_page=per_page,
        filters={"city": city, "category": category}
    )


@router.get("/search", response_model=ProductListResponse)
async def search_products(
    search_query: ProductSearchQuery = Depends(),
    db: Session = Depends(get_db)
):
    """Расширенный поиск товаров"""
    
    query_obj = db.query(Product).join(Store).filter(Product.is_active == True)
    
    # Применяем все фильтры из search_query
    if search_query.query:
        search_filter = or_(
            Product.name.ilike(f"%{search_query.query}%"),
            Product.description.ilike(f"%{search_query.query}%"),
            Product.brand.ilike(f"%{search_query.query}%"),
            Product.category.ilike(f"%{search_query.query}%")
        )
        query_obj = query_obj.filter(search_filter)
    
    if search_query.category:
        query_obj = query_obj.filter(Product.category.ilike(f"%{search_query.category}%"))
    
    if search_query.city:
        query_obj = query_obj.filter(Store.city.ilike(f"%{search_query.city}%"))
    
    if search_query.store_id:
        query_obj = query_obj.filter(Product.store_id == search_query.store_id)
    
    if search_query.brand:
        query_obj = query_obj.filter(Product.brand.ilike(f"%{search_query.brand}%"))
    
    if search_query.min_price:
        query_obj = query_obj.filter(Product.price >= search_query.min_price)
    
    if search_query.max_price:
        query_obj = query_obj.filter(Product.price <= search_query.max_price)
    
    if search_query.min_rating:
        query_obj = query_obj.filter(Product.rating >= search_query.min_rating)
    
    if search_query.sizes:
        size_filters = [Product.sizes.contains([size]) for size in search_query.sizes]
        query_obj = query_obj.filter(or_(*size_filters))
    
    if search_query.colors:
        color_filters = [Product.colors.contains([color]) for color in search_query.colors]
        query_obj = query_obj.filter(or_(*color_filters))
    
    if search_query.in_stock_only:
        query_obj = query_obj.filter(Product.stock_quantity > 0)
    
    # Сортировка
    sort_column = getattr(Product, search_query.sort_by, Product.created_at)
    if search_query.sort_order.lower() == "asc":
        query_obj = query_obj.order_by(asc(sort_column))
    else:
        query_obj = query_obj.order_by(desc(sort_column))
    
    # Пагинация
    total = query_obj.count()
    products = query_obj.offset((search_query.page - 1) * search_query.per_page).limit(search_query.per_page).all()
    
    # Преобразование в ProductBrief
    products_brief = []
    for product in products:
        product_data = {
            "id": product.id,
            "name": product.name,
            "price": product.price,
            "original_price": product.original_price,
            "rating": product.rating,
            "image_urls": product.image_urls,
            "discount_percentage": product.discount_percentage,
            "is_in_stock": product.is_in_stock,
            "store": {
                "id": product.store.id,
                "name": product.store.name,
                "city": product.store.city,
                "logo_url": product.store.logo_url,
                "rating": product.store.rating
            }
        }
        products_brief.append(ProductBrief(**product_data))
    
    return ProductListResponse(
        products=products_brief,
        total=total,
        page=search_query.page,
        per_page=search_query.per_page,
        filters=search_query.model_dump(exclude={"page", "per_page", "sort_by", "sort_order"})
    )


@router.get("/{product_id}", response_model=ProductResponse)
async def get_product(product_id: int, db: Session = Depends(get_db)):
    """Получить информацию о конкретном товаре"""
    
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Товар не найден")
    
    # Создаем полный ответ с вычисляемыми полями
    product_data = {
        **product.__dict__,
        'price_info': product.price_display,
        'discount_percentage': product.discount_percentage,
        'is_in_stock': product.is_in_stock,
        'store': {
            "id": product.store.id,
            "name": product.store.name,
            "city": product.store.city,
            "logo_url": product.store.logo_url,
            "rating": product.store.rating
        }
    }
    
    return ProductResponse(**product_data)


@router.post("/", response_model=ProductResponse)
async def create_product(
    product_data: ProductCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Создать новый товар (для админов/магазинов)"""
    
    # Проверяем существование магазина
    store = db.query(Store).filter(Store.id == product_data.store_id).first()
    if not store:
        raise HTTPException(status_code=404, detail="Магазин не найден")
    
    # Создаем товар
    product_dict = product_data.model_dump()
    product = Product(**product_dict)
    
    db.add(product)
    db.commit()
    db.refresh(product)
    
    logger.info(f"Создан новый товар: {product.name} в магазине {store.name}")
    
    # Возвращаем полный ответ
    product_data = {
        **product.__dict__,
        'price_info': product.price_display,
        'discount_percentage': product.discount_percentage,
        'is_in_stock': product.is_in_stock,
        'store': {
            "id": product.store.id,
            "name": product.store.name,
            "city": product.store.city,
            "logo_url": product.store.logo_url,
            "rating": product.store.rating
        }
    }
    
    return ProductResponse(**product_data)


@router.put("/{product_id}", response_model=ProductResponse)
async def update_product(
    product_id: int,
    product_data: ProductUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Обновить товар (для админов/магазинов)"""
    
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Товар не найден")
    
    # Обновляем только переданные поля
    for field, value in product_data.model_dump(exclude_unset=True).items():
        setattr(product, field, value)
    
    db.commit()
    db.refresh(product)
    
    logger.info(f"Обновлен товар: {product.name}")
    
    # Возвращаем полный ответ
    product_response_data = {
        **product.__dict__,
        'price_info': product.price_display,
        'discount_percentage': product.discount_percentage,
        'is_in_stock': product.is_in_stock,
        'store': {
            "id": product.store.id,
            "name": product.store.name,
            "city": product.store.city,
            "logo_url": product.store.logo_url,
            "rating": product.store.rating
        }
    }
    
    return ProductResponse(**product_response_data) 
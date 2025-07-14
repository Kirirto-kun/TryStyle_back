from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, asc
from typing import List, Optional
import logging

from src.database import get_db
from src.models.store import Store
from src.models.product import Product
from src.schemas.store import (
    StoreResponse, StoreListResponse, StoreBrief, StoreCreate, StoreUpdate,
    CityStatsResponse, CitiesListResponse, StoreStatsResponse
)
from src.schemas.product import ProductBrief, ProductListResponse
from src.utils.auth import get_current_user
from src.utils.roles import require_admin
from src.models.user import User

router = APIRouter(prefix="/stores", tags=["stores"])
logger = logging.getLogger(__name__)


@router.get("/", response_model=StoreListResponse)
async def get_stores(
    city: Optional[str] = Query(None, description="Фильтр по городу"),
    rating_min: Optional[float] = Query(None, description="Минимальный рейтинг"),
    sort_by: str = Query("created_at", description="Сортировка: name, rating, city, created_at"),
    sort_order: str = Query("desc", description="Порядок: asc, desc"),
    page: int = Query(1, ge=1, description="Номер страницы"),
    per_page: int = Query(20, ge=1, le=100, description="Количество на странице"),
    db: Session = Depends(get_db)
):
    """Получить список всех магазинов с фильтрацией"""
    
    query = db.query(Store)
    
    # Фильтрация
    if city:
        query = query.filter(Store.city.ilike(f"%{city}%"))
    
    if rating_min:
        query = query.filter(Store.rating >= rating_min)
    
    # Сортировка
    sort_column = getattr(Store, sort_by, Store.created_at)
    if sort_order.lower() == "asc":
        query = query.order_by(asc(sort_column))
    else:
        query = query.order_by(desc(sort_column))
    
    # Пагинация
    total = query.count()
    stores = query.offset((page - 1) * per_page).limit(per_page).all()
    
    return StoreListResponse(
        stores=stores,
        total=total,
        page=page,
        per_page=per_page
    )


@router.get("/cities", response_model=CitiesListResponse)
async def get_cities(db: Session = Depends(get_db)):
    """Получить список всех городов с магазинами"""
    
    # Получаем статистику по городам
    cities_data = db.query(
        Store.city,
        func.count(Store.id).label('stores_count'),
        func.coalesce(func.sum(
            db.query(func.count(Product.id))
            .filter(Product.store_id == Store.id)
            .scalar_subquery()
        ), 0).label('products_count')
    ).group_by(Store.city).all()
    
    cities = [
        CityStatsResponse(
            city=city_data.city,
            stores_count=city_data.stores_count,
            products_count=city_data.products_count or 0
        )
        for city_data in cities_data
    ]
    
    return CitiesListResponse(cities=cities)


@router.get("/by-city/{city}", response_model=StoreListResponse)
async def get_stores_by_city(
    city: str,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """Получить магазины по городу"""
    
    query = db.query(Store).filter(Store.city.ilike(f"%{city}%"))
    
    total = query.count()
    stores = query.offset((page - 1) * per_page).limit(per_page).all()
    
    if not stores:
        raise HTTPException(status_code=404, detail=f"Магазины в городе '{city}' не найдены")
    
    return StoreListResponse(
        stores=stores,
        total=total,
        page=page,
        per_page=per_page
    )


@router.get("/{store_id}", response_model=StoreResponse)
async def get_store(store_id: int, db: Session = Depends(get_db)):
    """Получить информацию о конкретном магазине"""
    
    store = db.query(Store).filter(Store.id == store_id).first()
    if not store:
        raise HTTPException(status_code=404, detail="Магазин не найден")
    
    return store


@router.get("/{store_id}/products", response_model=ProductListResponse)
async def get_store_products(
    store_id: int,
    category: Optional[str] = Query(None, description="Фильтр по категории"),
    in_stock_only: bool = Query(False, description="Только товары в наличии"),
    sort_by: str = Query("created_at", description="Сортировка: name, price, rating, created_at"),
    sort_order: str = Query("desc", description="Порядок: asc, desc"),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """Получить товары конкретного магазина"""
    
    # Проверяем существование магазина
    store = db.query(Store).filter(Store.id == store_id).first()
    if not store:
        raise HTTPException(status_code=404, detail="Магазин не найден")
    
    query = db.query(Product).filter(Product.store_id == store_id, Product.is_active == True)
    
    # Фильтрация
    if category:
        query = query.filter(Product.category.ilike(f"%{category}%"))
    
    if in_stock_only:
        query = query.filter(Product.stock_quantity > 0)
    
    # Сортировка
    sort_column = getattr(Product, sort_by, Product.created_at)
    if sort_order.lower() == "asc":
        query = query.order_by(asc(sort_column))
    else:
        query = query.order_by(desc(sort_column))
    
    # Пагинация
    total = query.count()
    products = query.offset((page - 1) * per_page).limit(per_page).all()
    
    # Преобразование в ProductBrief с вычисляемыми полями
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
        per_page=per_page
    )


@router.get("/{store_id}/stats", response_model=StoreStatsResponse)
async def get_store_stats(store_id: int, db: Session = Depends(get_db)):
    """Получить статистику магазина"""
    
    store = db.query(Store).filter(Store.id == store_id).first()
    if not store:
        raise HTTPException(status_code=404, detail="Магазин не найден")
    
    # Статистика товаров
    total_products = db.query(Product).filter(Product.store_id == store_id).count()
    active_products = db.query(Product).filter(
        Product.store_id == store_id, 
        Product.is_active == True
    ).count()
    
    # Средний рейтинг товаров
    avg_rating = db.query(func.avg(Product.rating)).filter(
        Product.store_id == store_id,
        Product.is_active == True
    ).scalar() or 0.0
    
    # Количество отзывов
    total_reviews = db.query(func.sum(Product.reviews_count)).filter(
        Product.store_id == store_id
    ).scalar() or 0
    
    # Количество категорий
    categories_count = db.query(func.count(func.distinct(Product.category))).filter(
        Product.store_id == store_id,
        Product.is_active == True
    ).scalar() or 0
    
    # Топ категории
    top_categories = db.query(
        Product.category,
        func.count(Product.id).label('count')
    ).filter(
        Product.store_id == store_id,
        Product.is_active == True
    ).group_by(Product.category).order_by(desc('count')).limit(5).all()
    
    return StoreStatsResponse(
        id=store.id,
        name=store.name,
        city=store.city,
        total_products=total_products,
        active_products=active_products,
        average_rating=round(avg_rating, 2),
        total_reviews=total_reviews,
        categories_count=categories_count,
        top_categories=[cat.category for cat in top_categories]
    )


@router.post("/", response_model=StoreResponse)
async def create_store(
    store_data: StoreCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin())
):
    """Создать новый магазин (только для суперадминов)"""
    
    # Проверяем, не существует ли уже магазин с таким названием в этом городе
    existing_store = db.query(Store).filter(
        Store.name == store_data.name,
        Store.city == store_data.city
    ).first()
    
    if existing_store:
        raise HTTPException(
            status_code=400, 
            detail=f"Магазин '{store_data.name}' уже существует в городе '{store_data.city}'"
        )
    
    store = Store(**store_data.model_dump())
    db.add(store)
    db.commit()
    db.refresh(store)
    
    logger.info(f"Создан новый магазин: {store.name} в {store.city}")
    
    return store


@router.put("/{store_id}", response_model=StoreResponse)
async def update_store(
    store_id: int,
    store_data: StoreUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin())
):
    """Обновить информацию о магазине (только для суперадминов)"""
    
    store = db.query(Store).filter(Store.id == store_id).first()
    if not store:
        raise HTTPException(status_code=404, detail="Магазин не найден")
    
    # Обновляем только переданные поля
    for field, value in store_data.model_dump(exclude_unset=True).items():
        setattr(store, field, value)
    
    db.commit()
    db.refresh(store)
    
    logger.info(f"Обновлен магазин: {store.name}")
    
    return store 
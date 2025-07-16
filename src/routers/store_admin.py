from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, asc, and_
from typing import List, Optional
import logging
import base64
import uuid
import asyncio
from datetime import datetime, timedelta

from src.database import get_db
from src.models.user import User
from src.models.store import Store
from src.models.product import Product
from src.models.review import Review
from src.schemas.store_admin import (
    StoreAdminDashboard, StoreProductStats, StoreAdminSettings,
    StoreAnalytics, StoreAdminProductCreate, StoreAdminProductUpdate,
    LowStockAlert, PhotoProductUpload
)
from src.schemas.product import ProductResponse, ProductListResponse, ProductBrief
from src.utils.auth import get_current_user
from src.utils.roles import check_store_access, UserRole
from src.utils.firebase_storage import upload_image_to_firebase_async
from src.utils.analyze_image import analyze_image

router = APIRouter(prefix="/store-admin", tags=["store-admin"])
logger = logging.getLogger(__name__)


def get_store_admin_user(current_user: User = Depends(get_current_user)) -> User:
    """Проверяет, что пользователь - админ магазина или суперадмин"""
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user"
        )
    
    user_role = getattr(current_user, 'role', UserRole.USER)
    if user_role not in [UserRole.STORE_ADMIN, UserRole.ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Store admin or admin privileges required."
        )
    
    return current_user


@router.get("/dashboard", response_model=StoreAdminDashboard)
async def get_dashboard(
    current_user: User = Depends(get_store_admin_user),
    db: Session = Depends(get_db)
):
    """Главный дашборд админа магазина"""
    
    # Определяем магазин пользователя
    if current_user.role == UserRole.ADMIN:
        # Суперадмин может выбрать магазин через query параметр
        # Пока возьмем первый доступный магазин
        store = db.query(Store).first()
        if not store:
            raise HTTPException(status_code=404, detail="No stores found")
    else:
        if not current_user.store_id:
            raise HTTPException(status_code=400, detail="Store admin must be assigned to a store")
        store = db.query(Store).filter(Store.id == current_user.store_id).first()
        if not store:
            raise HTTPException(status_code=404, detail="Assigned store not found")
    
    # Статистика товаров
    total_products = db.query(Product).filter(Product.store_id == store.id).count()
    active_products = db.query(Product).filter(
        Product.store_id == store.id,
        Product.is_active == True
    ).count()
    inactive_products = total_products - active_products
    
    # Товары по категориям
    categories_data = db.query(
        Product.category,
        func.count(Product.id).label('count')
    ).filter(
        Product.store_id == store.id,
        Product.is_active == True
    ).group_by(Product.category).all()
    
    products_by_category = {cat.category: cat.count for cat in categories_data}
    
    # Статистика отзывов
    total_reviews = db.query(func.sum(Product.reviews_count)).filter(
        Product.store_id == store.id
    ).scalar() or 0
    
    average_rating = db.query(func.avg(Product.rating)).filter(
        Product.store_id == store.id,
        Product.is_active == True
    ).scalar() or 0.0
    
    # Последние добавленные товары
    recent_products_query = db.query(Product).filter(
        Product.store_id == store.id,
        Product.is_active == True
    ).order_by(desc(Product.created_at)).limit(5).all()
    
    recent_products = []
    for product in recent_products_query:
        recent_products.append(ProductBrief(
            id=product.id,
            name=product.name,
            price=product.price,
            original_price=product.original_price,
            rating=product.rating,
            image_urls=product.image_urls,
            discount_percentage=product.discount_percentage,
            is_in_stock=product.is_in_stock,
            store={
                "id": store.id,
                "name": store.name,
                "city": store.city,
                "logo_url": store.logo_url,
                "rating": store.rating
            }
        ))
    
    # Товары с низким остатком
    low_stock_products_query = db.query(Product).filter(
        Product.store_id == store.id,
        Product.is_active == True,
        Product.stock_quantity <= 5,
        Product.stock_quantity > 0
    ).order_by(asc(Product.stock_quantity)).limit(5).all()
    
    low_stock_products = []
    for product in low_stock_products_query:
        low_stock_products.append(ProductBrief(
            id=product.id,
            name=product.name,
            price=product.price,
            original_price=product.original_price,
            rating=product.rating,
            image_urls=product.image_urls,
            discount_percentage=product.discount_percentage,
            is_in_stock=product.is_in_stock,
            store={
                "id": store.id,
                "name": store.name,
                "city": store.city,
                "logo_url": store.logo_url,
                "rating": store.rating
            }
        ))
    
    # Топ товары по рейтингу
    top_rated_products_query = db.query(Product).filter(
        Product.store_id == store.id,
        Product.is_active == True,
        Product.rating >= 4.0
    ).order_by(desc(Product.rating), desc(Product.reviews_count)).limit(5).all()
    
    top_rated_products = []
    for product in top_rated_products_query:
        top_rated_products.append(ProductBrief(
            id=product.id,
            name=product.name,
            price=product.price,
            original_price=product.original_price,
            rating=product.rating,
            image_urls=product.image_urls,
            discount_percentage=product.discount_percentage,
            is_in_stock=product.is_in_stock,
            store={
                "id": store.id,
                "name": store.name,
                "city": store.city,
                "logo_url": store.logo_url,
                "rating": store.rating
            }
        ))
    
    return StoreAdminDashboard(
        store={
            "id": store.id,
            "name": store.name,
            "city": store.city,
            "logo_url": store.logo_url,
            "rating": store.rating
        },
        total_products=total_products,
        active_products=active_products,
        inactive_products=inactive_products,
        products_by_category=products_by_category,
        total_reviews=total_reviews,
        average_rating=round(average_rating, 2),
        recent_products=recent_products,
        low_stock_products=low_stock_products,
        top_rated_products=top_rated_products
    )


@router.get("/products", response_model=ProductListResponse)
async def get_store_products(
    category: Optional[str] = Query(None, description="Фильтр по категории"),
    in_stock_only: bool = Query(False, description="Только товары в наличии"),
    sort_by: str = Query("created_at", description="Сортировка: name, price, rating, created_at, stock_quantity"),
    sort_order: str = Query("desc", description="Порядок: asc, desc"),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_store_admin_user),
    db: Session = Depends(get_db)
):
    """Получить товары своего магазина для управления"""
    
    # Определяем магазин
    if current_user.role == UserRole.ADMIN:
        # Пока берем первый магазин для суперадмина
        store = db.query(Store).first()
        if not store:
            raise HTTPException(status_code=404, detail="No stores found")
        store_id = store.id
    else:
        if not current_user.store_id:
            raise HTTPException(status_code=400, detail="Store admin must be assigned to a store")
        store_id = current_user.store_id
    
    query = db.query(Product).filter(Product.store_id == store_id)
    
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
    
    # Получаем информацию о магазине
    store = db.query(Store).filter(Store.id == store_id).first()
    
    # Преобразование в ProductBrief
    products_brief = []
    for product in products:
        products_brief.append(ProductBrief(
            id=product.id,
            name=product.name,
            price=product.price,
            original_price=product.original_price,
            rating=product.rating,
            image_urls=product.image_urls,
            discount_percentage=product.discount_percentage,
            is_in_stock=product.is_in_stock,
            store={
                "id": store.id,
                "name": store.name,
                "city": store.city,
                "logo_url": store.logo_url,
                "rating": store.rating
            }
        ))
    
    return ProductListResponse(
        products=products_brief,
        total=total,
        page=page,
        per_page=per_page,
        filters={"category": category, "in_stock_only": in_stock_only}
    )


@router.post("/products", response_model=ProductResponse)
async def create_product(
    product_data: StoreAdminProductCreate,
    current_user: User = Depends(get_store_admin_user),
    db: Session = Depends(get_db)
):
    """Создать новый товар в своем магазине"""
    
    # Определяем магазин
    if current_user.role == UserRole.ADMIN:
        # Пока берем первый магазин для суперадмина
        store = db.query(Store).first()
        if not store:
            raise HTTPException(status_code=404, detail="No stores found")
        store_id = store.id
    else:
        if not current_user.store_id:
            raise HTTPException(status_code=400, detail="Store admin must be assigned to a store")
        store_id = current_user.store_id
    
    # Проверяем существование магазина
    store = db.query(Store).filter(Store.id == store_id).first()
    if not store:
        raise HTTPException(status_code=404, detail="Store not found")
    
    # Создаем товар
    product_dict = product_data.model_dump()
    product_dict['store_id'] = store_id  # Автоматически устанавливаем магазин
    product = Product(**product_dict)
    
    db.add(product)
    db.commit()
    db.refresh(product)
    
    logger.info(f"Store admin {current_user.username} created product: {product.name} in store {store.name}")
    
    # Возвращаем полный ответ
    return ProductResponse(
        **product.__dict__,
        price_info=product.price_display,
        discount_percentage=product.discount_percentage,
        is_in_stock=product.is_in_stock,
        store={
            "id": store.id,
            "name": store.name,
            "city": store.city,
            "logo_url": store.logo_url,
            "rating": store.rating
        }
    )


@router.put("/products/{product_id}", response_model=ProductResponse)
async def update_product(
    product_id: int,
    product_data: StoreAdminProductUpdate,
    current_user: User = Depends(get_store_admin_user),
    db: Session = Depends(get_db)
):
    """Обновить товар в своем магазине"""
    
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Проверяем права доступа к магазину
    if not check_store_access(current_user, product.store_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. You can only manage products in your own store."
        )
    
    # Обновляем только переданные поля
    for field, value in product_data.model_dump(exclude_unset=True).items():
        setattr(product, field, value)
    
    db.commit()
    db.refresh(product)
    
    logger.info(f"Store admin {current_user.username} updated product: {product.name}")
    
    # Возвращаем полный ответ
    return ProductResponse(
        **product.__dict__,
        price_info=product.price_display,
        discount_percentage=product.discount_percentage,
        is_in_stock=product.is_in_stock,
        store={
            "id": product.store.id,
            "name": product.store.name,
            "city": product.store.city,
            "logo_url": product.store.logo_url,
            "rating": product.store.rating
        }
    )


@router.delete("/products/{product_id}")
async def delete_product(
    product_id: int,
    current_user: User = Depends(get_store_admin_user),
    db: Session = Depends(get_db)
):
    """Удалить товар из своего магазина"""
    
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Проверяем права доступа к магазину
    if not check_store_access(current_user, product.store_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. You can only manage products in your own store."
        )
    
    product_name = product.name
    db.delete(product)
    db.commit()
    
    logger.info(f"Store admin {current_user.username} deleted product: {product_name}")
    
    return {"message": f"Product '{product_name}' has been deleted successfully"}


@router.get("/analytics", response_model=StoreAnalytics)
async def get_store_analytics(
    period: str = Query("month", description="Период: week, month, year"),
    current_user: User = Depends(get_store_admin_user),
    db: Session = Depends(get_db)
):
    """Получить аналитику магазина"""
    
    # Определяем магазин
    if current_user.role == UserRole.ADMIN:
        store = db.query(Store).first()
        if not store:
            raise HTTPException(status_code=404, detail="No stores found")
        store_id = store.id
    else:
        if not current_user.store_id:
            raise HTTPException(status_code=400, detail="Store admin must be assigned to a store")
        store_id = current_user.store_id
    
    # Определяем период
    period_days = {
        "week": 7,
        "month": 30,
        "year": 365
    }
    
    if period not in period_days:
        raise HTTPException(status_code=400, detail="Invalid period. Use: week, month, year")
    
    start_date = datetime.now() - timedelta(days=period_days[period])
    
    # Товары, добавленные за период
    products_added = db.query(Product).filter(
        Product.store_id == store_id,
        Product.created_at >= start_date
    ).count()
    
    # Отзывы, полученные за период
    reviews_received = db.query(Review).join(Product).filter(
        Product.store_id == store_id,
        Review.created_at >= start_date
    ).count()
    
    # Изменение среднего рейтинга (упрощенно)
    current_rating = db.query(func.avg(Product.rating)).filter(
        Product.store_id == store_id,
        Product.is_active == True
    ).scalar() or 0.0
    
    # Популярные категории
    popular_categories_data = db.query(
        Product.category,
        func.count(Product.id).label('count'),
        func.avg(Product.rating).label('avg_rating')
    ).filter(
        Product.store_id == store_id,
        Product.is_active == True
    ).group_by(Product.category).order_by(desc('count')).limit(5).all()
    
    popular_categories = [
        {
            "category": cat.category,
            "products_count": cat.count,
            "average_rating": round(cat.avg_rating, 2)
        }
        for cat in popular_categories_data
    ]
    
    # Распределение рейтингов
    rating_distribution = {}
    for rating in range(1, 6):
        count = db.query(Product).filter(
            Product.store_id == store_id,
            Product.is_active == True,
            Product.rating >= rating,
            Product.rating < rating + 1
        ).count()
        rating_distribution[str(rating)] = count
    
    return StoreAnalytics(
        period=period,
        products_added=products_added,
        reviews_received=reviews_received,
        average_rating_change=0.0,  # TODO: Implement proper calculation
        popular_categories=popular_categories,
        rating_distribution=rating_distribution
    )


@router.get("/low-stock-alerts", response_model=List[LowStockAlert])
async def get_low_stock_alerts(
    threshold: int = Query(5, description="Порог для уведомления о низком остатке"),
    current_user: User = Depends(get_store_admin_user),
    db: Session = Depends(get_db)
):
    """Получить уведомления о товарах с низким остатком"""
    
    # Определяем магазин
    if current_user.role == UserRole.ADMIN:
        store = db.query(Store).first()
        if not store:
            raise HTTPException(status_code=404, detail="No stores found")
        store_id = store.id
    else:
        if not current_user.store_id:
            raise HTTPException(status_code=400, detail="Store admin must be assigned to a store")
        store_id = current_user.store_id
    
    # Товары с низким остатком
    low_stock_products = db.query(Product).filter(
        Product.store_id == store_id,
        Product.is_active == True,
        Product.stock_quantity <= threshold
    ).order_by(asc(Product.stock_quantity)).all()
    
    alerts = []
    for product in low_stock_products:
        alerts.append(LowStockAlert(
            product_id=product.id,
            product_name=product.name,
            current_stock=product.stock_quantity,
            threshold=threshold,
            category=product.category
        ))
    
    return alerts


@router.put("/store-settings", response_model=dict)
async def update_store_settings(
    settings: StoreAdminSettings,
    current_user: User = Depends(get_store_admin_user),
    db: Session = Depends(get_db)
):
    """Обновить настройки магазина"""
    
    # Определяем магазин
    if current_user.role == UserRole.ADMIN:
        store = db.query(Store).first()
        if not store:
            raise HTTPException(status_code=404, detail="No stores found")
    else:
        if not current_user.store_id:
            raise HTTPException(status_code=400, detail="Store admin must be assigned to a store")
        store = db.query(Store).filter(Store.id == current_user.store_id).first()
        if not store:
            raise HTTPException(status_code=404, detail="Store not found")
    
    # Обновляем настройки
    for field, value in settings.model_dump().items():
        setattr(store, field, value)
    
    db.commit()
    db.refresh(store)
    
    logger.info(f"Store admin {current_user.username} updated store settings for {store.name}")
    
    return {"message": "Store settings updated successfully"}


@router.post("/products/upload-photos", response_model=ProductResponse)
async def create_product_from_photos(
    upload_data: PhotoProductUpload,
    current_user: User = Depends(get_store_admin_user),
    db: Session = Depends(get_db)
):
    """Создать товар через загрузку фотографий с AI анализом"""
    
    # Определяем магазин админа
    if current_user.role == UserRole.ADMIN:
        # Суперадмин может выбрать магазин (пока берем первый)
        store = db.query(Store).first()
        if not store:
            raise HTTPException(status_code=404, detail="No stores found")
        store_id = store.id
    else:
        if not current_user.store_id:
            raise HTTPException(status_code=400, detail="Store admin must be assigned to a store")
        store_id = current_user.store_id
        store = db.query(Store).filter(Store.id == store_id).first()
        if not store:
            raise HTTPException(status_code=404, detail="Store not found")

    uploaded_image_urls = []
    
    try:
        logger.info(f"Store admin {current_user.username} uploading {len(upload_data.images_base64)} photos for new product")
        
        # 1. Загружаем все изображения в Firebase параллельно
        upload_tasks = []
        for i, image_base64 in enumerate(upload_data.images_base64):
            try:
                # Декодируем base64 изображение
                img_bytes = base64.b64decode(image_base64.split(",")[-1])
                
                # Генерируем уникальное имя файла
                file_name = f"product_{store_id}_{uuid.uuid4()}_{i}.png"
                
                # Создаем задачу загрузки
                upload_task = upload_image_to_firebase_async(img_bytes, file_name)
                upload_tasks.append(upload_task)
                
            except Exception as e:
                logger.error(f"Error processing image {i}: {str(e)}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Failed to process image {i+1}: invalid base64 format"
                )
        
        # Загружаем все изображения параллельно
        uploaded_image_urls = await asyncio.gather(*upload_tasks)
        logger.info(f"Successfully uploaded {len(uploaded_image_urls)} images to Firebase")
        
        # 2. Анализируем ВСЕ изображения параллельно через GPT Azure
        logger.info(f"Analyzing {len(uploaded_image_urls)} images for comprehensive features extraction")
        analysis_tasks = [analyze_image(image_url) for image_url in uploaded_image_urls]
        all_analyses = await asyncio.gather(*analysis_tasks, return_exceptions=True)
        
        # 3. Обрабатываем результаты анализа всех изображений
        all_features = []
        all_names = []
        all_categories = []
        successful_analyses = 0
        
        for i, analysis in enumerate(all_analyses):
            if isinstance(analysis, Exception):
                logger.error(f"Error analyzing image {i+1}: {analysis}")
                continue
                
            successful_analyses += 1
            logger.info(f"Analysis {i+1} completed: {analysis}")
            
            # Собираем названия для выбора лучшего
            if analysis.get("name"):
                all_names.append(analysis["name"])
            
            # Собираем категории
            if analysis.get("category"):
                all_categories.append(analysis["category"])
            
            # Собираем features из всех изображений
            image_features = analysis.get("features", [])
            if image_features:
                all_features.extend([f for f in image_features if f is not None and isinstance(f, str)])
        
        logger.info(f"Successfully analyzed {successful_analyses}/{len(uploaded_image_urls)} images")
        
        # 4. Убираем дубликаты features, сохраняя порядок
        unique_features = []
        seen_features = set()
        for feature in all_features:
            feature_lower = feature.lower()
            if feature_lower not in seen_features:
                unique_features.append(feature)
                seen_features.add(feature_lower)
        
        logger.info(f"Combined {len(all_features)} features into {len(unique_features)} unique features")
        
        # 5. Определяем название товара
        if upload_data.name:
            # Используем название от фронтенда (приоритет)
            product_name = upload_data.name
            logger.info(f"Using name from frontend: {product_name}")
        else:
            # Выбираем самое подробное название из анализов
            if all_names:
                product_name = max(all_names, key=len)  # Самое подробное описание
                logger.info(f"Using most detailed GPT name: {product_name}")
            else:
                product_name = "Новый товар"
                logger.info("Using fallback name: Новый товар")
        
        # 6. Определяем категорию (берем наиболее частую)
        if all_categories:
            from collections import Counter
            category_counts = Counter(all_categories)
            final_category = category_counts.most_common(1)[0][0]
            logger.info(f"Selected category: {final_category} (appeared {category_counts[final_category]} times)")
        else:
            final_category = "other"
            logger.info("Using fallback category: other")
        
        # 7. Финальные features (уже уникальные)
        features = unique_features
        
        # 8. Создаем товар в базе данных
        product_data = {
            "name": product_name,
            "description": f"Товар добавлен через анализ {successful_analyses} фото.",
            "price": upload_data.price,
            "original_price": upload_data.original_price,
            "category": final_category,  # Категория из анализа всех изображений
            "brand": store.name,  # Название магазина как бренд
            "features": features,  # Объединенные характеристики из всех фото
            "sizes": upload_data.sizes,  # От фронтенда
            "colors": upload_data.colors,  # От фронтенда
            "image_urls": uploaded_image_urls,  # URL изображений из Firebase
            "stock_quantity": upload_data.stock_quantity,
            "store_id": store_id,
            "is_active": True
        }
        
        product = Product(**product_data)
        db.add(product)
        db.commit()
        db.refresh(product)
        
        logger.info(f"Successfully created product: {product.name} (ID: {product.id}) in store {store.name}")
        
        # 9. Возвращаем полный ответ
        return ProductResponse(
            **product.__dict__,
            price_info=product.price_display,
            discount_percentage=product.discount_percentage,
            is_in_stock=product.is_in_stock,
            store={
                "id": store.id,
                "name": store.name,
                "city": store.city,
                "logo_url": store.logo_url,
                "rating": store.rating
            }
        )
        
    except HTTPException:
        # Переподнимаем HTTP исключения
        raise
    except Exception as e:
        logger.error(f"Error creating product from photos: {str(e)}")
        
        # В случае ошибки пытаемся удалить загруженные изображения
        if uploaded_image_urls:
            try:
                from src.utils.firebase_storage import delete_image_from_firebase_async
                delete_tasks = [delete_image_from_firebase_async(url) for url in uploaded_image_urls]
                await asyncio.gather(*delete_tasks, return_exceptions=True)
                logger.info("Cleaned up uploaded images after error")
            except Exception as cleanup_error:
                logger.error(f"Failed to cleanup images: {cleanup_error}")
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create product: {str(e)}"
        ) 
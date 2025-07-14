from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, text
from datetime import datetime, timedelta
import os
from typing import List

from src.database import get_db, get_connection_pool_status
from src.models.user import User, UserRole
from src.models.store import Store
from src.schemas.admin import (
    UserStats, 
    SimpleUserCount, 
    DetailedUserStats, 
    DatabaseStatus, 
    AdminResponse,
    UserBrief,
    RegistrationTrend,
    PoolStatus,
    PoolMetrics,
    PoolAnalysis
)
from src.schemas.store_admin import (
    StoreAdminUserCreate, StoreAdminUserResponse, StoreAdminListResponse
)
from src.utils.auth import get_current_user, get_password_hash
from src.utils.roles import require_admin

router = APIRouter(prefix="/admin", tags=["admin"])

def is_admin_user(current_user: User = Depends(get_current_user)) -> User:
    """
    Проверяет, является ли текущий пользователь администратором.
    Простая проверка: админ - это первый зарегистрированный пользователь.
    В продакшене стоит добавить специальное поле is_admin в модель User.
    """
    # TODO: В будущем добавить поле is_admin в модель User
    # Пока проверяем, что пользователь существует и активен
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Admin privileges required."
        )
    return current_user

# === НОВЫЕ ЭНДПОИНТЫ ДЛЯ УПРАВЛЕНИЯ АДМИНАМИ МАГАЗИНОВ ===

@router.post("/create-store-admin", response_model=StoreAdminUserResponse)
async def create_store_admin(
    admin_data: StoreAdminUserCreate,
    current_user: User = Depends(require_admin()),
    db: Session = Depends(get_db)
):
    """Создать админа магазина (только для суперадминов)"""
    
    # Проверяем, существует ли пользователь с таким email
    existing_user = db.query(User).filter(User.email == admin_data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this email already exists"
        )
    
    # Проверяем, существует ли пользователь с таким username
    existing_username = db.query(User).filter(User.username == admin_data.username).first()
    if existing_username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this username already exists"
        )
    
    # Проверяем, существует ли магазин
    store = db.query(Store).filter(Store.id == admin_data.store_id).first()
    if not store:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Store not found"
        )
    
    # Проверяем, нет ли уже админа у этого магазина
    existing_admin = db.query(User).filter(
        User.store_id == admin_data.store_id,
        User.role == UserRole.STORE_ADMIN
    ).first()
    if existing_admin:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Store '{store.name}' already has an admin: {existing_admin.username}"
        )
    
    # Создаем нового админа магазина
    hashed_password = get_password_hash(admin_data.password)
    new_admin = User(
        email=admin_data.email,
        username=admin_data.username,
        hashed_password=hashed_password,
        role=UserRole.STORE_ADMIN,
        store_id=admin_data.store_id,
        is_active=True
    )
    
    db.add(new_admin)
    db.commit()
    db.refresh(new_admin)
    
    # Получаем информацию о магазине для ответа
    store = db.query(Store).filter(Store.id == new_admin.store_id).first()
    
    return StoreAdminUserResponse(
        id=new_admin.id,
        email=new_admin.email,
        username=new_admin.username,
        is_active=new_admin.is_active,
        created_at=new_admin.created_at,
        updated_at=new_admin.updated_at,
        role=new_admin.role.value,
        store_id=new_admin.store_id,
        managed_store={
            "id": store.id,
            "name": store.name,
            "city": store.city,
            "logo_url": store.logo_url,
            "rating": store.rating
        } if store else None
    )


@router.get("/store-admins", response_model=StoreAdminListResponse)
async def get_store_admins(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    current_user: User = Depends(require_admin()),
    db: Session = Depends(get_db)
):
    """Получить список всех админов магазинов"""
    
    query = db.query(User).filter(User.role == UserRole.STORE_ADMIN)
    
    total = query.count()
    store_admins = query.offset((page - 1) * per_page).limit(per_page).all()
    
    # Преобразуем в ответы с информацией о магазинах
    admin_responses = []
    for admin in store_admins:
        store = None
        if admin.store_id:
            store = db.query(Store).filter(Store.id == admin.store_id).first()
        
        admin_responses.append(StoreAdminUserResponse(
            id=admin.id,
            email=admin.email,
            username=admin.username,
            is_active=admin.is_active,
            created_at=admin.created_at,
            updated_at=admin.updated_at,
            role=admin.role.value,
            store_id=admin.store_id,
            managed_store={
                "id": store.id,
                "name": store.name,
                "city": store.city,
                "logo_url": store.logo_url,
                "rating": store.rating
            } if store else None
        ))
    
    return StoreAdminListResponse(
        store_admins=admin_responses,
        total=total,
        page=page,
        per_page=per_page
    )


@router.put("/store-admins/{user_id}", response_model=StoreAdminUserResponse)
async def update_store_admin(
    user_id: int,
    store_id: int = Query(..., description="New store ID"),
    is_active: bool = Query(True, description="User active status"),
    current_user: User = Depends(require_admin()),
    db: Session = Depends(get_db)
):
    """Обновить права админа магазина"""
    
    # Находим админа
    admin = db.query(User).filter(
        User.id == user_id,
        User.role == UserRole.STORE_ADMIN
    ).first()
    if not admin:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Store admin not found"
        )
    
    # Проверяем новый магазин
    store = db.query(Store).filter(Store.id == store_id).first()
    if not store:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Store not found"
        )
    
    # Проверяем, нет ли уже админа у нового магазина
    if admin.store_id != store_id:
        existing_admin = db.query(User).filter(
            User.store_id == store_id,
            User.role == UserRole.STORE_ADMIN,
            User.id != user_id
        ).first()
        if existing_admin:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Store '{store.name}' already has an admin: {existing_admin.username}"
            )
    
    # Обновляем админа
    admin.store_id = store_id
    admin.is_active = is_active
    
    db.commit()
    db.refresh(admin)
    
    return StoreAdminUserResponse(
        id=admin.id,
        email=admin.email,
        username=admin.username,
        is_active=admin.is_active,
        created_at=admin.created_at,
        updated_at=admin.updated_at,
        role=admin.role.value,
        store_id=admin.store_id,
        managed_store={
            "id": store.id,
            "name": store.name,
            "city": store.city,
            "logo_url": store.logo_url,
            "rating": store.rating
        }
    )


@router.delete("/store-admins/{user_id}")
async def delete_store_admin(
    user_id: int,
    current_user: User = Depends(require_admin()),
    db: Session = Depends(get_db)
):
    """Удалить админа магазина"""
    
    admin = db.query(User).filter(
        User.id == user_id,
        User.role == UserRole.STORE_ADMIN
    ).first()
    if not admin:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Store admin not found"
        )
    
    store_name = None
    if admin.store_id:
        store = db.query(Store).filter(Store.id == admin.store_id).first()
        store_name = store.name if store else "Unknown"
    
    username = admin.username
    db.delete(admin)
    db.commit()
    
    return {
        "message": f"Store admin '{username}' for store '{store_name}' has been deleted successfully"
    }

# === ОСТАЛЬНЫЕ СУЩЕСТВУЮЩИЕ ЭНДПОИНТЫ ===

@router.get("/users/count", response_model=SimpleUserCount)
async def get_users_count(current_user: User = Depends(require_admin()), db: Session = Depends(get_db)):
    """Получить простой счетчик пользователей"""
    total_users = db.query(User).count()
    active_users = db.query(User).filter(User.is_active == True).count()
    return SimpleUserCount(
        total_users=total_users, 
        active_users=active_users
    )

@router.get("/users/stats", response_model=UserStats)
async def get_users_stats(current_user: User = Depends(require_admin()), db: Session = Depends(get_db)):
    """Получить детальную статистику пользователей"""
    total_users = db.query(User).count()
    active_users = db.query(User).filter(User.is_active == True).count()
    inactive_users = total_users - active_users
    
    # Статистика за разные периоды
    now = datetime.utcnow()
    last_24h = now - timedelta(hours=24)
    last_week = now - timedelta(days=7)
    last_month = now - timedelta(days=30)
    
    users_last_24h = db.query(User).filter(User.created_at >= last_24h).count()
    users_last_week = db.query(User).filter(User.created_at >= last_week).count()
    users_last_month = db.query(User).filter(User.created_at >= last_month).count()
    
    # Пользователи с телефоном
    users_with_phone = db.query(User).filter(User.phone.isnot(None), User.phone != '').count()
    
    # Первый пользователь (демо)
    first_user = db.query(User).order_by(User.id).first()
    first_user_data = None
    if first_user:
        first_user_data = UserBrief(
            id=first_user.id,
            username=first_user.username,
            email=first_user.email,
            is_active=first_user.is_active,
            created_at=first_user.created_at
        )
    
    # Последний пользователь
    latest_user = db.query(User).order_by(User.created_at.desc()).first()
    latest_user_data = None
    if latest_user:
        latest_user_data = UserBrief(
            id=latest_user.id,
            username=latest_user.username,
            email=latest_user.email,
            is_active=latest_user.is_active,
            created_at=latest_user.created_at
        )
    
    return UserStats(
        total_users=total_users,
        active_users=active_users,
        inactive_users=inactive_users,
        users_last_24h=users_last_24h,
        users_last_week=users_last_week,
        users_last_month=users_last_month,
        users_with_phone=users_with_phone,
        first_user=first_user_data,
        latest_user=latest_user_data,
        active_percentage=round((active_users / total_users * 100) if total_users > 0 else 0, 1),
        phone_percentage=round((users_with_phone / total_users * 100) if total_users > 0 else 0, 1)
    )

@router.get("/users/detailed", response_model=DetailedUserStats)
async def get_detailed_users_stats(current_user: User = Depends(require_admin()), db: Session = Depends(get_db)):
    """Получить расширенную статистику пользователей с трендами"""
    
    # Получаем базовую статистику
    basic_stats = await get_users_stats(current_user, db)
    
    # Тренд регистраций за последние 7 дней
    registration_trend = []
    for i in range(7):
        date = datetime.utcnow().date() - timedelta(days=i)
        start_of_day = datetime.combine(date, datetime.min.time())
        end_of_day = datetime.combine(date, datetime.max.time())
        
        count = db.query(User).filter(
            User.created_at >= start_of_day,
            User.created_at <= end_of_day
        ).count()
        
        registration_trend.append(RegistrationTrend(
            date=date.strftime("%Y-%m-%d"),
            registrations=count
        ))
    
    registration_trend.reverse()  # Сортируем от старых к новым
    
    # Получаем последних пользователей
    recent_users = db.query(User).order_by(User.created_at.desc()).limit(10).all()
    recent_users_list = [
        UserBrief(
            id=user.id,
            username=user.username,
            email=user.email,
            is_active=user.is_active,
            created_at=user.created_at
        )
        for user in recent_users
    ]
    
    return DetailedUserStats(
        basic_stats=basic_stats,
        registration_trend=registration_trend,
        recent_users=recent_users_list
    )

@router.get("/database/status", response_model=DatabaseStatus)
async def get_database_status(current_user: User = Depends(require_admin()), db: Session = Depends(get_db)):
    """Получить статус подключения к базе данных"""
    try:
        # Проверяем подключение к БД
        db.execute(text("SELECT 1"))
        connected = True
        
        # Проверяем DATABASE_URL
        database_url_set = bool(os.getenv("DATABASE_URL"))
        
        # Проверяем существование таблицы users
        try:
            result = db.execute(text("SELECT COUNT(*) FROM users LIMIT 1"))
            users_table_exists = True
        except:
            users_table_exists = False
        
        # Считаем общее количество таблиц
        try:
            result = db.execute(text("""
                SELECT COUNT(*) 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
            """))
            total_tables = result.scalar() or 0
        except:
            total_tables = 0
        
        return DatabaseStatus(
            connected=connected,
            database_url_set=database_url_set,
            users_table_exists=users_table_exists,
            total_tables=total_tables,
            error_message=None
        )
    except Exception as e:
        return DatabaseStatus(
            connected=False,
            database_url_set=bool(os.getenv("DATABASE_URL")),
            users_table_exists=False,
            total_tables=0,
            error_message=str(e)
        )

@router.get("/database/pool-status", response_model=PoolStatus)
async def get_pool_status(current_user: User = Depends(require_admin())):
    """Получить детальный статус пула соединений"""
    try:
        pool_info = get_connection_pool_status()
        
        # Извлекаем метрики
        pool_size = pool_info.get('pool_size', 20)
        checked_in = pool_info.get('checked_in_connections', 0)
        checked_out = pool_info.get('checked_out_connections', 0)
        overflow = pool_info.get('overflow_connections', 0)
        total_capacity = pool_size + overflow
        
        # Анализируем использование
        usage_percentage = (checked_out / total_capacity * 100) if total_capacity > 0 else 0
        available_connections = total_capacity - checked_out
        
        if usage_percentage < 50:
            health_status = "healthy"
        elif usage_percentage < 80:
            health_status = "moderate"
        else:
            health_status = "high_load"
        
        return PoolStatus(
            pool_metrics=PoolMetrics(
                pool_size=pool_size,
                checked_in_connections=checked_in,
                checked_out_connections=checked_out,
                overflow_connections=overflow,
                total_capacity=total_capacity
            ),
            analysis=PoolAnalysis(
                pool_usage_percentage=round(usage_percentage, 1),
                health_status=health_status,
                available_connections=available_connections
            )
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get pool status: {str(e)}")

@router.get("/users/recent", response_model=List[UserBrief])
async def get_recent_users(
    limit: int = 10,
    current_user: User = Depends(require_admin()),
    db: Session = Depends(get_db)
):
    """Получить последних зарегистрированных пользователей"""
    recent_users = db.query(User).order_by(User.created_at.desc()).limit(limit).all()
    
    return [
        UserBrief(
            id=user.id,
            username=user.username,
            email=user.email,
            is_active=user.is_active,
            created_at=user.created_at
        )
        for user in recent_users
    ]

@router.get("/health")
async def health_check():
    """Проверка работоспособности админ API (без авторизации)"""
    return {
        "message": "Admin API is healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0"
    } 
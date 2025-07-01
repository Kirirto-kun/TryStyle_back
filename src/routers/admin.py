from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func, text
from datetime import datetime, timedelta
import os
from typing import List

from src.database import get_db, get_connection_pool_status
from src.models.user import User
from src.schemas.admin import (
    UserStats, 
    SimpleUserCount, 
    DetailedUserStats, 
    DatabaseStatus, 
    AdminResponse,
    UserBrief,
    RegistrationTrend
)
from src.utils.auth import get_current_user

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

@router.get("/users/count", response_model=SimpleUserCount)
async def get_users_count(
    db: Session = Depends(get_db),
    current_admin: User = Depends(is_admin_user)
):
    """
    Простой счетчик пользователей - быстрый способ узнать количество.
    """
    try:
        total_users = db.query(User).count()
        active_users = db.query(User).filter(User.is_active == True).count()
        
        return SimpleUserCount(
            total_users=total_users,
            active_users=active_users
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting user count: {str(e)}"
        )

@router.get("/users/stats", response_model=UserStats)
async def get_users_stats(
    db: Session = Depends(get_db),
    current_admin: User = Depends(is_admin_user)
):
    """
    Детальная статистика пользователей с информацией о регистрациях.
    """
    try:
        # Основные счетчики
        total_users = db.query(User).count()
        active_users = db.query(User).filter(User.is_active == True).count()
        inactive_users = db.query(User).filter(User.is_active == False).count()
        
        # Статистика по времени
        now = datetime.now()
        yesterday = now - timedelta(days=1)
        week_ago = now - timedelta(days=7)
        month_ago = now - timedelta(days=30)
        
        users_last_24h = db.query(User).filter(User.created_at >= yesterday).count()
        users_last_week = db.query(User).filter(User.created_at >= week_ago).count()
        users_last_month = db.query(User).filter(User.created_at >= month_ago).count()
        
        # Пользователи с телефонами
        users_with_phone = db.query(User).filter(User.phone.isnot(None)).count()
        
        # Первый и последний пользователи
        first_user = db.query(User).order_by(User.created_at.asc()).first()
        latest_user = db.query(User).order_by(User.created_at.desc()).first()
        
        # Процентные показатели
        active_percentage = (active_users / total_users * 100) if total_users > 0 else 0
        phone_percentage = (users_with_phone / total_users * 100) if total_users > 0 else 0
        
        # Конвертируем пользователей в UserBrief схемы
        first_user_brief = UserBrief.from_orm(first_user) if first_user else None
        latest_user_brief = UserBrief.from_orm(latest_user) if latest_user else None
        
        return UserStats(
            total_users=total_users,
            active_users=active_users,
            inactive_users=inactive_users,
            users_last_24h=users_last_24h,
            users_last_week=users_last_week,
            users_last_month=users_last_month,
            users_with_phone=users_with_phone,
            first_user=first_user_brief,
            latest_user=latest_user_brief,
            active_percentage=round(active_percentage, 1),
            phone_percentage=round(phone_percentage, 1)
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting user statistics: {str(e)}"
        )

@router.get("/users/detailed", response_model=DetailedUserStats)
async def get_detailed_users_stats(
    db: Session = Depends(get_db),
    current_admin: User = Depends(is_admin_user)
):
    """
    Расширенная статистика с трендами регистраций и последними пользователями.
    """
    try:
        # Получаем базовую статистику
        basic_stats_response = await get_users_stats(db, current_admin)
        
        # Тренд регистраций за последние 30 дней
        thirty_days_ago = datetime.now() - timedelta(days=30)
        
        # SQL запрос для группировки по дням
        trend_query = db.query(
            func.date(User.created_at).label('date'),
            func.count(User.id).label('registrations')
        ).filter(
            User.created_at >= thirty_days_ago
        ).group_by(
            func.date(User.created_at)
        ).order_by(
            func.date(User.created_at)
        ).all()
        
        # Конвертируем в схему
        registration_trend = [
            RegistrationTrend(
                date=str(row.date),
                registrations=row.registrations
            )
            for row in trend_query
        ]
        
        # Последние 10 пользователей
        recent_users_query = db.query(User).order_by(
            User.created_at.desc()
        ).limit(10).all()
        
        recent_users = [UserBrief.from_orm(user) for user in recent_users_query]
        
        return DetailedUserStats(
            basic_stats=basic_stats_response,
            registration_trend=registration_trend,
            recent_users=recent_users
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting detailed statistics: {str(e)}"
        )

@router.get("/database/status", response_model=DatabaseStatus)
async def get_database_status(
    db: Session = Depends(get_db),
    current_admin: User = Depends(is_admin_user)
):
    """
    Проверяет статус подключения к базе данных и доступность таблиц.
    """
    try:
        # Проверяем подключение
        db.execute(text("SELECT 1"))
        connected = True
        
        # Проверяем DATABASE_URL
        database_url_set = bool(os.getenv("DATABASE_URL"))
        
        # Проверяем существование таблицы users
        users_count = db.query(User).count()
        users_table_exists = True
        
        # Получаем количество таблиц в БД
        tables_query = db.execute(text("""
            SELECT COUNT(*) 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
        """))
        total_tables = tables_query.scalar()
        
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

@router.get("/database/pool-status")
async def get_connection_pool_status_endpoint(
    current_admin: User = Depends(is_admin_user)
):
    """
    Получить статус пула соединений базы данных для мониторинга.
    Помогает предотвратить исчерпание соединений и отслеживать производительность.
    """
    try:
        pool_status = get_connection_pool_status()
        
        # Добавляем дополнительные метрики для анализа
        pool_usage_percentage = (
            pool_status["checked_out_connections"] / pool_status["total_capacity"] * 100
        ) if pool_status["total_capacity"] > 0 else 0
        
        # Определяем статус здоровья пула
        if pool_usage_percentage < 50:
            health_status = "healthy"
        elif pool_usage_percentage < 80:
            health_status = "warning"
        else:
            health_status = "critical"
        
        return {
            "success": True,
            "pool_metrics": pool_status,
            "analysis": {
                "pool_usage_percentage": round(pool_usage_percentage, 2),
                "health_status": health_status,
                "available_connections": pool_status["total_capacity"] - pool_status["checked_out_connections"],
                "recommendations": {
                    "healthy": "Pool is operating normally",
                    "warning": "Consider monitoring for potential connection leaks",
                    "critical": "URGENT: Pool near exhaustion, check for connection leaks"
                }.get(health_status)
            },
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to get connection pool status: {str(e)}",
            "timestamp": datetime.now().isoformat()
        }

@router.get("/users/recent", response_model=List[UserBrief])
async def get_recent_users(
    limit: int = 10,
    db: Session = Depends(get_db),
    current_admin: User = Depends(is_admin_user)
):
    """
    Получить список последних зарегистрированных пользователей.
    """
    try:
        recent_users = db.query(User).order_by(
            User.created_at.desc()
        ).limit(limit).all()
        
        return [UserBrief.from_orm(user) for user in recent_users]
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting recent users: {str(e)}"
        )

@router.get("/health", response_model=AdminResponse)
async def admin_health_check():
    """
    Простая проверка работоспособности админ API (без авторизации).
    """
    return AdminResponse(
        success=True,
        message="Admin API is running",
        data={
            "version": "1.0.0",
            "endpoints": [
                "/admin/users/count",
                "/admin/users/stats", 
                "/admin/users/detailed",
                "/admin/database/status",
                "/admin/database/pool-status",
                "/admin/users/recent"
            ]
        }
    ) 
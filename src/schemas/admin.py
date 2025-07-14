from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class UserBrief(BaseModel):
    """Краткая информация о пользователе."""
    id: int
    username: str
    email: str
    is_active: bool
    created_at: datetime
    phone: Optional[str] = None

    class Config:
        from_attributes = True

class UserStats(BaseModel):
    """Детальная статистика пользователей."""
    total_users: int = Field(..., description="Общее количество пользователей")
    active_users: int = Field(..., description="Количество активных пользователей")
    inactive_users: int = Field(..., description="Количество неактивных пользователей")
    users_last_24h: int = Field(..., description="Регистрации за последние 24 часа")
    users_last_week: int = Field(..., description="Регистрации за последнюю неделю")
    users_last_month: int = Field(..., description="Регистрации за последний месяц")
    users_with_phone: int = Field(..., description="Пользователи с заполненным телефоном")
    first_user: Optional[UserBrief] = Field(None, description="Первый зарегистрированный пользователь")
    latest_user: Optional[UserBrief] = Field(None, description="Последний зарегистрированный пользователь")
    active_percentage: float = Field(..., description="Процент активных пользователей")
    phone_percentage: float = Field(..., description="Процент пользователей с телефонами")

class SimpleUserCount(BaseModel):
    """Простой счетчик пользователей."""
    total_users: int = Field(..., description="Общее количество пользователей")
    active_users: int = Field(..., description="Количество активных пользователей")
    timestamp: datetime = Field(default_factory=datetime.now, description="Время запроса")

class RegistrationTrend(BaseModel):
    """Тренд регистраций по дням."""
    date: str = Field(..., description="Дата в формате YYYY-MM-DD")
    registrations: int = Field(..., description="Количество регистраций в этот день")

class DetailedUserStats(BaseModel):
    """Расширенная статистика с трендами."""
    basic_stats: UserStats
    registration_trend: list[RegistrationTrend] = Field(
        default_factory=list, 
        description="Тренд регистраций за последние 30 дней"
    )
    recent_users: list[UserBrief] = Field(
        default_factory=list, 
        description="Последние 10 зарегистрированных пользователей"
    )

class DatabaseStatus(BaseModel):
    """Статус подключения к базе данных."""
    connected: bool = Field(..., description="Статус подключения")
    database_url_set: bool = Field(..., description="Установлена ли DATABASE_URL")
    users_table_exists: bool = Field(..., description="Существует ли таблица users")
    total_tables: int = Field(..., description="Общее количество таблиц в БД")
    error_message: Optional[str] = Field(None, description="Сообщение об ошибке, если есть")

class PoolMetrics(BaseModel):
    """Метрики пула соединений."""
    pool_size: int = Field(..., description="Размер пула соединений")
    checked_in_connections: int = Field(..., description="Количество возвращенных соединений")
    checked_out_connections: int = Field(..., description="Количество активных соединений")
    overflow_connections: int = Field(..., description="Количество overflow соединений")
    total_capacity: int = Field(..., description="Общая вместимость пула")

class PoolAnalysis(BaseModel):
    """Анализ использования пула."""
    pool_usage_percentage: float = Field(..., description="Процент использования пула")
    health_status: str = Field(..., description="Статус здоровья пула")
    available_connections: int = Field(..., description="Доступные соединения")

class PoolStatus(BaseModel):
    """Полный статус пула соединений."""
    pool_metrics: PoolMetrics = Field(..., description="Метрики пула")
    analysis: PoolAnalysis = Field(..., description="Анализ пула")

class AdminResponse(BaseModel):
    """Общий формат ответа админ API."""
    success: bool = Field(..., description="Успешность операции")
    message: str = Field(..., description="Сообщение о результате")
    data: Optional[dict] = Field(None, description="Данные ответа")
    timestamp: datetime = Field(default_factory=datetime.now, description="Время ответа") 
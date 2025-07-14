from fastapi import HTTPException, status, Depends
from sqlalchemy.orm import Session
from typing import Optional
from src.models.user import User, UserRole
from src.utils.auth import get_current_user


def require_role(required_role: UserRole):
    """
    Декоратор для проверки роли пользователя
    
    Args:
        required_role: Требуемая роль для доступа
    """
    def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if not current_user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Inactive user"
            )
        
        # Проверяем роль пользователя
        user_role = getattr(current_user, 'role', UserRole.USER)
        
        # Суперадмин имеет доступ ко всему
        if user_role == UserRole.ADMIN:
            return current_user
            
        # Проверяем соответствие требуемой роли
        if user_role != required_role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required role: {required_role.value}"
            )
        
        return current_user
    
    return role_checker


def require_store_admin():
    """Проверка прав админа магазина"""
    return require_role(UserRole.STORE_ADMIN)


def require_admin():
    """Проверка прав суперадмина"""
    return require_role(UserRole.ADMIN)


def check_store_access(user: User, store_id: int) -> bool:
    """
    Проверяет, имеет ли пользователь доступ к магазину
    
    Args:
        user: Пользователь
        store_id: ID магазина
        
    Returns:
        bool: True если доступ разрешен
    """
    # Суперадмин имеет доступ ко всем магазинам
    if getattr(user, 'role', UserRole.USER) == UserRole.ADMIN:
        return True
    
    # Админ магазина имеет доступ только к своему магазину
    if getattr(user, 'role', UserRole.USER) == UserRole.STORE_ADMIN:
        return getattr(user, 'store_id', None) == store_id
    
    # Обычные пользователи не имеют административного доступа
    return False


def get_user_accessible_stores(user: User) -> Optional[list]:
    """
    Получает список магазинов, к которым пользователь имеет доступ
    
    Args:
        user: Пользователь
        
    Returns:
        list: Список ID магазинов или None для полного доступа
    """
    user_role = getattr(user, 'role', UserRole.USER)
    
    # Суперадмин имеет доступ ко всем магазинам
    if user_role == UserRole.ADMIN:
        return None  # None означает доступ ко всем
    
    # Админ магазина имеет доступ только к своему магазину
    if user_role == UserRole.STORE_ADMIN:
        store_id = getattr(user, 'store_id', None)
        return [store_id] if store_id else []
    
    # Обычные пользователи не имеют административного доступа
    return [] 
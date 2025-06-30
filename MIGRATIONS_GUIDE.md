# Руководство по работе с миграциями базы данных

## Что такое миграции?

Миграции — это безопасный способ изменения структуры базы данных. Они позволяют:
- ✅ Версионировать изменения схемы БД
- ✅ Откатывать изменения при необходимости  
- ✅ Синхронизировать БД между разработчиками
- ✅ Автоматизировать развертывание на продакшене

## Настройка

В проекте используется [Alembic](https://alembic.sqlalchemy.org/) для управления миграциями. Конфигурация уже настроена:

```
alembic/                    # Папка с миграциями
├── env.py                  # Конфигурация Alembic
├── script.py.mako         # Шаблон для новых миграций  
└── versions/              # Файлы миграций
alembic.ini                # Основная конфигурация
```

## Команды для работы с миграциями

### Способ 1: Использование готовых скриптов (рекомендуется)

#### Python скрипт (работает на всех ОС):
```bash
# Применить все миграции
python scripts/migrate.py upgrade

# Создать новую миграцию
python scripts/migrate.py revision "Добавить таблицу продуктов"

# Откатить последнюю миграцию
python scripts/migrate.py downgrade

# Показать текущую версию БД
python scripts/migrate.py current

# Показать историю миграций
python scripts/migrate.py history
```

#### Bash скрипт (Linux/macOS):
```bash
# Применить все миграции
./scripts/migrate.sh upgrade

# Создать новую миграцию
./scripts/migrate.sh revision "Добавить таблицу продуктов"

# Откатить последнюю миграцию
./scripts/migrate.sh downgrade

# Показать текущую версию БД
./scripts/migrate.sh current

# Показать историю миграций
./scripts/migrate.sh history
```

### Способ 2: Прямые команды Alembic

Если виртуальное окружение активировано:

```bash
# Применить все миграции
alembic upgrade head

# Создать новую миграцию с автогенерацией
alembic revision --autogenerate -m "Описание изменений"

# Откатить на одну миграцию назад
alembic downgrade -1

# Показать текущую версию
alembic current

# Показать историю
alembic history
```

## Рабочий процесс

### 1. При изменении моделей

1. **Изменяете модель** в `src/models/`:
   ```python
   # Например, добавляете новое поле в модель User
   class User(Base):
       # ... существующие поля
       phone = Column(String, nullable=True)  # Новое поле
   ```

2. **Создаете миграцию**:
   ```bash
   python scripts/migrate.py revision "Добавить поле phone в таблицу users"
   ```

3. **Проверяете созданную миграцию** в `alembic/versions/`:
   ```python
   def upgrade() -> None:
       op.add_column('users', sa.Column('phone', sa.String(), nullable=True))
   
   def downgrade() -> None:
       op.drop_column('users', 'phone')
   ```

4. **Применяете миграцию**:
   ```bash
   python scripts/migrate.py upgrade
   ```

### 2. Развертывание на сервере

```bash
# 1. Обновляете код
git pull

# 2. Активируете виртуальное окружение
source venv/bin/activate

# 3. Применяете миграции
python scripts/migrate.py upgrade

# 4. Перезапускаете приложение
# (зависит от вашего способа развертывания)
```

### 3. Откат изменений

Если что-то пошло не так:

```bash
# Откатить последнюю миграцию
python scripts/migrate.py downgrade

# Откатить до конкретной версии
alembic downgrade abc123def456
```

## Важные моменты

### ⚠️ Безопасность данных

- **Всегда делайте бэкап** перед применением миграций на продакшене
- **Тестируйте миграции** на копии продакшн базы
- **Проверяйте автогенерированные миграции** — Alembic может не всё понять правильно

### ⚠️ Команды, требующие осторожности

```python
# Опасные операции (потеря данных):
op.drop_table('table_name')           # Удаление таблицы
op.drop_column('table', 'column')     # Удаление столбца
op.alter_column('table', 'col', nullable=False)  # Может упасть на существующих NULL

# Безопасные операции:
op.add_column('table', Column(...))   # Добавление столбца
op.create_index('idx_name', 'table', ['column'])  # Создание индекса
```

### 📝 Хорошие практики

1. **Описательные названия миграций**:
   ```bash
   ✅ "Добавить таблицу заказов"
   ✅ "Добавить индекс на email пользователей"
   ❌ "Изменения в БД"
   ❌ "Фикс"
   ```

2. **Одна логическая задача = одна миграция**

3. **Проверяйте миграции перед коммитом**:
   ```bash
   # Создали миграцию
   python scripts/migrate.py revision "Добавить поле"
   
   # Применили
   python scripts/migrate.py upgrade
   
   # Проверили, что работает
   python -m pytest tests/
   
   # Откатили для проверки
   python scripts/migrate.py downgrade
   
   # Снова применили
   python scripts/migrate.py upgrade
   ```

## Структура файла миграции

```python
"""Описание миграции

Revision ID: abc123def456
Revises: xyz789uvw012
Create Date: 2025-06-30 12:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'abc123def456'
down_revision: Union[str, None] = 'xyz789uvw012'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    """Применить изменения"""
    # Команды для изменения схемы
    pass

def downgrade() -> None:
    """Откатить изменения"""
    # Команды для отката изменений
    pass
```

## Устранение проблем

### Проблема: "Target database is not up to date"

```bash
# Решение: применить миграции
python scripts/migrate.py upgrade
```

### Проблема: "Can't locate revision identified by 'xyz'"

```bash
# Решение: проверить историю и синхронизировать
python scripts/migrate.py history
alembic stamp head  # Пометить текущее состояние как актуальное
```

### Проблема: Конфликт миграций

```bash
# Решение: создать merge миграцию
alembic merge -m "Объединить ветки миграций" revision1 revision2
```

## Docker

Если используете Docker, добавьте команду в `Dockerfile` или docker-compose:

```dockerfile
# Dockerfile
RUN python scripts/migrate.py upgrade
```

```yaml
# docker-compose.yml
version: '3.8'
services:
  web:
    # ...
    command: >
      sh -c "python scripts/migrate.py upgrade &&
             uvicorn src.main:app --host 0.0.0.0 --port 8000"
```

## Примеры типичных операций

### Добавление новой таблицы

```python
def upgrade() -> None:
    op.create_table('products',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('price', sa.Numeric(10, 2), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_products_name', 'products', ['name'])

def downgrade() -> None:
    op.drop_index('ix_products_name', table_name='products')
    op.drop_table('products')
```

### Добавление внешнего ключа

```python
def upgrade() -> None:
    op.add_column('orders', sa.Column('user_id', sa.Integer(), nullable=False))
    op.create_foreign_key('fk_orders_user_id', 'orders', 'users', ['user_id'], ['id'])

def downgrade() -> None:
    op.drop_constraint('fk_orders_user_id', 'orders', type_='foreignkey')
    op.drop_column('orders', 'user_id')
```

### Изменение типа столбца

```python
def upgrade() -> None:
    # PostgreSQL
    op.alter_column('users', 'phone',
                    existing_type=sa.VARCHAR(),
                    type_=sa.String(20),
                    existing_nullable=True)

def downgrade() -> None:
    op.alter_column('users', 'phone',
                    existing_type=sa.String(20),
                    type_=sa.VARCHAR(),
                    existing_nullable=True)
``` 
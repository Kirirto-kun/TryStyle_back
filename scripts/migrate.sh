
#!/bin/bash

# Скрипт для управления миграциями базы данных
# Использование:
#   ./scripts/migrate.sh upgrade      - применить все миграции
#   ./scripts/migrate.sh revision "Описание"  - создать новую миграцию
#   ./scripts/migrate.sh downgrade    - откатить последнюю миграцию
#   ./scripts/migrate.sh current      - показать текущую версию БД
#   ./scripts/migrate.sh history      - показать историю миграций

set -e  # Выходить при ошибке

# Определяем корневую директорию проекта
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Переходим в корневую директорию
cd "$PROJECT_ROOT"

# Активируем виртуальное окружение если оно существует
if [ -d "venv" ]; then
    echo "🔧 Активируем виртуальное окружение..."
    source venv/bin/activate
fi

# Проверяем наличие переменных окружения
if [ ! -f ".env" ]; then
    echo "⚠️  Файл .env не найден. Убедитесь, что DATABASE_URL настроен."
fi

case "$1" in
    "upgrade")
        echo "🔄 Применяем миграции..."
        alembic upgrade head
        echo "✅ Миграции успешно применены!"
        ;;
    
    "revision")
        if [ -z "$2" ]; then
            echo "❌ Укажите описание для миграции"
            echo "Пример: ./scripts/migrate.sh revision 'Добавить таблицу продуктов'"
            exit 1
        fi
        echo "📝 Создаём новую миграцию: $2"
        alembic revision --autogenerate -m "$2"
        echo "✅ Миграция создана!"
        ;;
    
    "downgrade")
        echo "⬇️ Откатываем последнюю миграцию..."
        alembic downgrade -1
        echo "✅ Миграция откачена!"
        ;;
    
    "current")
        echo "📍 Текущая версия базы данных:"
        alembic current
        ;;
    
    "history")
        echo "📚 История миграций:"
        alembic history
        ;;
    
    *)
        echo "❌ Неизвестная команда: $1"
        echo ""
        echo "Использование:"
        echo "  $0 upgrade      - применить все миграции"
        echo "  $0 revision \"Описание\"  - создать новую миграцию"
        echo "  $0 downgrade    - откатить последнюю миграцию"
        echo "  $0 current      - показать текущую версию БД"
        echo "  $0 history      - показать историю миграций"
        exit 1
        ;;
esac 